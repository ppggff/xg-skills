#!/usr/bin/env python3
"""gitweb companion for the status viewer (card 003).

Runs a read-only, localhost-only gitweb over multiple repositories (each product
project repo + the dev_root repo + the KB repo) via lighttpd, as a co-launched
companion of viewer.py. The viewer stays pure stdlib; this module only
orchestrates the external lighttpd/gitweb (subprocess), and its dependencies
(lighttpd, Perl, gitweb.cgi) never enter the viewer.

Security posture: localhost bind + a lighttpd Host allowlist (DNS-rebinding guard,
needs mod_access loaded), gitweb snapshot disabled, a controlled symlink forest
(only the chosen repos' git-dirs), read-only.

Sync targets: none (lives only in xg-dev-workflow/tools/).
"""
import argparse
import importlib.util
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
DEFAULT_PORT = 8791
RESERVED = ("dev-workflow", "knowledge")


def _load(fname, mod):
    spec = importlib.util.spec_from_file_location(mod, str(TOOLS / fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_rp = _load("resolve-project.py", "rp")


def runtime_dir():
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(cache) / "xg-dev-workflow" / "gitweb-companion"


def discover():
    """Locate lighttpd + the gitweb share dir (holds gitweb.cgi + static/); None if unavailable."""
    lighttpd = shutil.which("lighttpd")
    if not lighttpd:
        return None
    share = _gitweb_share()
    if not share:
        return None
    return {"lighttpd": lighttpd, "share": str(share)}


def _gitweb_share():
    try:
        exec_path = subprocess.run(["git", "--exec-path"], capture_output=True, text=True).stdout.strip()
    except OSError:
        exec_path = ""
    cands = []
    if exec_path:
        cands.append(Path(exec_path).parent.parent / "share" / "gitweb")
    cands += [Path("/opt/homebrew/share/gitweb"), Path("/usr/local/share/gitweb"), Path("/usr/share/gitweb")]
    for c in cands:
        if (c / "gitweb.cgi").is_file():
            return c
    return None


def collect_repos():
    """[(label, git_dir)] for product projects + dev_root + KB.

    Skips paths that are missing / not a git repo; reserves the dev-workflow and
    knowledge labels; suffixes a colliding label rather than dropping a repo;
    dedups repos that resolve to the same git-dir.
    """
    text = ""
    cp = _rp.config_path()
    if cp.exists():
        text = cp.read_text(encoding="utf-8")
    wanted = []
    for name, paths in _rp.parse_projects(text):
        if name not in RESERVED and paths:
            wanted.append((name, Path(os.path.expanduser(str(paths[0])))))
    wanted.append(("dev-workflow", Path(os.path.expanduser(_rp.parse_dev_root(text)))))
    wanted.append(("knowledge", Path(os.path.expanduser(_rp.parse_kb_root(text)))))

    out, labels, gitdirs = [], set(), set()
    for label, path in wanted:
        gd = _git_dir(path)
        if not gd or gd in gitdirs:
            continue
        gitdirs.add(gd)
        out.append((_uniq(label, labels), gd))
    return out


def _git_dir(path):
    if not path.is_dir():
        return None
    try:
        r = subprocess.run(["git", "-C", str(path), "rev-parse", "--absolute-git-dir"],
                           capture_output=True, text=True)
    except OSError:
        return None
    gd = r.stdout.strip()
    return gd if r.returncode == 0 and gd else None


def _uniq(label, seen):
    base, n, out = label, 2, label
    while out in seen:
        out = "%s-%d" % (base, n)
        n += 1
    seen.add(out)
    return out


def build_forest(runtime, repos):
    """Rebuild <runtime>/projectroot with a symlink <label> -> <git-dir> per repo."""
    root = runtime / "projectroot"
    if root.exists() or root.is_symlink():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for label, gd in repos:
        (root / label).symlink_to(gd)
    return root


def write_configs(runtime, disc, port):
    (runtime / "tmp").mkdir(parents=True, exist_ok=True)
    gwcfg = runtime / "gitweb_config.perl"
    gwcfg.write_text(
        'our $projectroot = "%s";\n'
        'our $projects_list = $projectroot;\n'
        'our $git_temp = "%s";\n'
        "$feature{'snapshot'}{'default'} = [];\n"  # no tarball download (shrinks bulk-exfil surface)
        % (runtime / "projectroot", runtime / "tmp"),
        encoding="utf-8")
    lcfg = runtime / "lighttpd.conf"
    lcfg.write_text(
        'server.document-root = "%s"\n'
        'server.bind = "127.0.0.1"\n'
        "server.port = %d\n"
        'server.modules = ( "mod_access", "mod_cgi", "mod_setenv" )\n'  # mod_access load-bearing for the Host guard
        'server.pid-file = "%s"\n'
        'server.errorlog = "%s"\n'
        'index-file.names = ( "gitweb.cgi" )\n'
        'cgi.assign = ( ".cgi" => "" )\n'
        'setenv.add-environment = ( "GITWEB_CONFIG" => "%s", "PATH" => "%s" )\n'
        '$HTTP["host"] !~ "^(127\\.0\\.0\\.1|localhost)(:[0-9]+)?$" { url.access-deny = ( "" ) }\n'
        % (disc["share"], port, runtime / "lighttpd.pid", runtime / "error.log",
           gwcfg, os.environ.get("PATH", "")),
        encoding="utf-8")
    return lcfg


def _validate(lighttpd, lcfg):
    v = subprocess.run([lighttpd, "-tt", "-f", str(lcfg)], capture_output=True, text=True)
    if v.returncode != 0:
        sys.stderr.write("gitweb-companion: lighttpd config invalid:\n" + v.stderr)
    return v.returncode == 0


def _is_our_lighttpd(pid, runtime):
    try:
        r = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
    except OSError:
        return False
    return "lighttpd" in r.stdout and str(runtime / "lighttpd.conf") in r.stdout


def reap_stale(runtime):
    """Kill a leftover companion lighttpd from a previous run (e.g. viewer was -9'd). Returns
    True if it actually signalled one, so the caller can wait for the port to release."""
    pidf = runtime / "lighttpd.pid"
    if not pidf.exists():
        return False
    try:
        pid = int(pidf.read_text().strip())
    except (ValueError, OSError):
        pid = 0
    reaped = False
    if pid and _is_our_lighttpd(pid, runtime):
        try:
            os.kill(pid, signal.SIGTERM)
            reaped = True
        except OSError:
            pass
    try:
        pidf.unlink()
    except OSError:
        pass
    return reaped


def prepare(port=DEFAULT_PORT):
    """discover + build forest + write configs + validate. Returns a handle dict or None."""
    disc = discover()
    if not disc:
        return None
    runtime = runtime_dir()
    runtime.mkdir(parents=True, exist_ok=True)
    repos = collect_repos()
    build_forest(runtime, repos)
    lcfg = write_configs(runtime, disc, port)
    if not _validate(disc["lighttpd"], lcfg):
        return None
    return {"disc": disc, "runtime": runtime, "lcfg": lcfg, "port": port,
            "repos": [label for label, _ in repos]}


def _port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _serves_gitweb(port):
    """Whether 127.0.0.1:port answers with our gitweb (not just any listener)."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=0.6) as r:
            return "gitweb" in r.read(4096).decode("utf-8", "replace").lower()
    except Exception:
        return False


def _await_up(proc, port, timeout=6.0):
    """Up = the child is alive AND the port serves *our* gitweb. Polls (no fixed-settle guess) until
    either the child exits (bind failure / bad config → not up) or a gitweb response confirms it.
    Two independent signals, so neither a slow startup nor a foreign process holding the port can
    fool it: our child dies if it can't bind, and a foreign listener won't return gitweb HTML."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        if _serves_gitweb(port):
            return True
        time.sleep(0.1)
    return False


def start(port=DEFAULT_PORT):
    """Prepare + launch lighttpd, confirming it comes up. Returns handle, or None on any failure."""
    h = prepare(port)
    if not h:
        return None
    if reap_stale(h["runtime"]):
        time.sleep(0.5)                      # let our just-reaped stale release the port
    proc = subprocess.Popen([h["disc"]["lighttpd"], "-D", "-f", str(h["lcfg"])])
    if not _await_up(proc, port):
        sys.stderr.write("gitweb-companion: lighttpd did not come up on 127.0.0.1:%d "
                         "(port busy or config error)\n" % port)
        if proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        return None
    h["proc"] = proc
    return h


def stop(handle):
    if not handle:
        return
    proc = handle.get("proc")
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser(description="gitweb companion for the status viewer")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--once", action="store_true", help="build + validate + report, do not serve")
    a = ap.parse_args()
    if not discover():
        print("gitweb-companion: lighttpd or gitweb not found — companion disabled", file=sys.stderr)
        sys.exit(2)
    if a.once:
        h = prepare(a.port)
        if not h:
            sys.exit(1)
        print("repos (%d): %s" % (len(h["repos"]), ", ".join(h["repos"])))
        print("config ok; would serve http://127.0.0.1:%d/" % a.port)
        sys.exit(0)
    h = start(a.port)
    if not h:
        sys.exit(1)
    print("gitweb companion on http://127.0.0.1:%d/ (%d repos)" % (a.port, len(h["repos"])))

    def _sig(*_):
        stop(h)
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    h["proc"].wait()


if __name__ == "__main__":
    main()
