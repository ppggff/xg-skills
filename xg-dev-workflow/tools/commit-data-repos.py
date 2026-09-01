#!/usr/bin/env python3
"""Local-commit the two data repos (KB + workflow docs) — never push.

Used two ways:
  1. The skill's gate-driven cadence calls it (or runs git directly) after a doc/KB write.
  2. The optional Stop-hook safety net calls it at session end to sweep anything uncommitted.

Reads the shared config (~/.config/xg-knowledge-wiki/config.yaml):
  root:     -> KB repo        (default ~/knowledge)
  dev_root: -> workflow docs  (default ~/dev-workflow)

For each existing dir: lazily `git init` (+ a minimal .gitignore) if it isn't a repo yet.
`--project NAME` commits only that project's paths (>=1 commit per repo); without it,
dirty paths are grouped by project and committed one group per commit (message suffixed
` [<group>]`), so one call never mixes two projects' files into the same commit
(same-project parallel sessions need `--card` — project scope can't separate them, 027). **Never pushes, never amends/rebases** (push + history-rewrite stay
human-gated, per global Git & MR Safety).

NOT a byte-identical synced script — it lives only here (xg-dev-workflow/tools/).

Docs-repo commits pass the doc-native diff guard (026 LLD-8): an approved block's
compare-face change without a same-batch 变更/退役 annotation blocks the commit
(`approved-block-touched`); `--allow-approved-edit` overrides and books a log.md
line per card. The (ad) anchor check is the after-the-fact backstop.

Usage:
  commit-data-repos.py [--message MSG] [--reason TEXT] [--only kb|docs]
                       [--project NAME | --card PROJECT/NNN]
`--card PROJECT/NNN` is the gate-commit / single-card park mode (027): docs scope =
the card dir + the project's index.md/roadmap.md (shared-file row-level ride-along is
accepted), KB scope stays project-level; zero/multiple card-dir matches 报错不静默.
`--project NAME` scopes to a whole project (learn/improve 等项目级写入); paths outside
scope stay uncommitted (warned, not lost). Omit both for the sweep safety net.
Exit 0 always (a commit failure on one repo is reported, doesn't abort the other).
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULTS = {"root": "~/knowledge", "dev_root": "~/dev-workflow"}
GITIGNORE = ".DS_Store\n*.swp\n*.swo\n*~\n__pycache__/\n"

# ---- doc-native diff guard (026 LLD-8) ----
PHASE_DOC = re.compile(r"^(?P<card>[^/]+/\d{3}-[^/]+)/(?P<doc>requirement|design|detail)\.md$")
DOC_NATIVE_MODES = ("doc-native-pilot", "doc-native")
# compare face lives in block_parse.face_diffs (029 T2 — the retired
# GUARD_FIELDS constant's single-source successor, shared with the (ad) core)
_BP = None


def _block_parse():
    global _BP
    if _BP is None:
        import importlib.util
        path = Path(__file__).resolve().parent / "block_parse.py"
        spec = importlib.util.spec_from_file_location("block_parse", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _BP = mod
    return _BP


def _card_governance(repo: Path, card_rel: str) -> str:
    """Mode as COMMITTED (HEAD side) — review #4: reading the worktree let a
    same-batch governance downgrade switch the guard off; judged at HEAD, the
    downgrade itself is a guarded phase-doc change. New cards (no HEAD copy)
    fall back to the worktree."""
    head = git(repo, "show", "HEAD:" + card_rel + "/requirement.md")
    text = head.stdout if head.returncode == 0 else ""
    if not text:
        try:
            text = (repo / card_rel / "requirement.md").read_text(encoding="utf-8")
        except OSError:
            return ""
    # quote-tolerant, same value normalization as card_mode (029 T3) — the
    # quoted form used to switch the guard off silently
    m = re.search(r"^governance:\s*['\"]?([\w-]+)", text, re.M)
    return m.group(1) if m else ""


def diff_guard(repo: Path, kind: str, pathspecs: list, allow: bool = False) -> list:
    """Write-time guard (026 LLD-8), docs repo only: an approved doc-native
    block whose compare face (block_parse.face_diffs — five fields + title +
    clauses, 029 T2 — or the state word) differs from HEAD without a
    same-batch 变更/退役 annotation blocks the commit
    (`approved-block-touched`). Proposed blocks, annotation appends and
    legal M2 (fresh 变更/退役 note in the same diff) pass. `allow` (the
    --allow-approved-edit flag) lets findings through and books one log.md
    line per card. Guard errors fail open with a warning — the (ad) anchor
    check is the after-the-fact backstop, and the session-end sweep must never
    lose data to a guard bug."""
    if kind != "docs":
        return []
    try:   # discovery only — a failure here degrades the whole batch, loudly
        status = git(repo, "status", "--porcelain", "-uall", "-z", "--", *pathspecs)
        touched = {}
        for path in parse_porcelain_z(status.stdout):
            m = PHASE_DOC.match(path)
            if m:
                touched.setdefault(m.group("card"), []).append(path)
    except Exception as e:
        print("(diff-guard error: %s — proceeding unguarded)" % e, file=sys.stderr)
        return []
    findings, by_card = [], {}
    for card_rel, paths in sorted(touched.items()):
        for path in paths:
            try:   # review #11: fail-open is PER DOC — one bad file never
                   # strips the guard from the rest of the batch
                if _card_governance(repo, card_rel) not in DOC_NATIVE_MODES:
                    break
                bp = _block_parse()
                head = git(repo, "show", "HEAD:" + path)
                if head.returncode != 0:
                    continue  # new doc — first landing is not a touch
                try:
                    wt = (repo / path).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    wt = ""
                old_blocks, old_pf = bp.parse_doc_blocks(head.stdout)
                new_blocks, new_pf = bp.parse_doc_blocks(wt)
                # parse-class injections (a second `- 陈述:` line, a forged
                # duplicate id, a near-miss header) render but fall out of the
                # compare face — block the NEW ones at write time (029 review #2)
                for pf in new_pf:
                    if pf not in old_pf and pf.startswith(
                            ("duplicate-id", "duplicate-field", "bad-header")):
                        findings.append("parse-injection: %s %s" % (path, pf))
                        by_card.setdefault(card_rel, []).append(pf)
                new_by = {}
                for b in new_blocks:
                    new_by.setdefault("%s-%s" % (b["prefix"], b["num"]), b)
                for ob in old_blocks:
                    # union selection predicate (029 T3, block_parse.is_guarded):
                    # a HEAD-side state rewrite alone must not drop the block
                    if not bp.is_guarded(ob):
                        continue
                    bid = "%s-%s" % (ob["prefix"], ob["num"])
                    nb = new_by.get(bid)
                    if nb is None:
                        findings.append("approved-block-touched: %s %s removed" % (path, bid))
                        by_card.setdefault(card_rel, []).append(bid)
                        continue
                    fresh_note = (
                        len([a for a in nb["annotations"] if a["kind"] in ("变更", "退役")])
                        > len([a for a in ob["annotations"] if a["kind"] in ("变更", "退役")]))
                    if not bp.annots_prefix(ob, nb):
                        # the gate receipt itself (029 review #1): rewriting an
                        # approved note through the normal commit path must not
                        # reach HEAD — appends pass, rewrites never do, and a
                        # fresh 变更 note cannot launder a rewrite (it is
                        # itself an append; only --allow-approved-edit books
                        # one through)
                        findings.append(
                            "approved-block-touched: %s %s (annotations 非前缀)"
                            % (path, bid))
                        by_card.setdefault(card_rel, []).append(bid)
                    diffs = bp.face_diffs(ob, nb)
                    if ob["state"] != nb["state"]:
                        diffs.append("state")
                    if diffs and not fresh_note:
                        findings.append("approved-block-touched: %s %s (%s) — 同批无 变更/退役 注记"
                                        % (path, bid, ", ".join(diffs)))
                        by_card.setdefault(card_rel, []).append(bid)
            except Exception as e:
                print("(diff-guard error on %s: %s — that doc unguarded)" % (path, e),
                      file=sys.stderr)
    if findings and allow:
        # booking sits OUTSIDE any fail-open scope (review #11): the override's
        # log.md line is the accounting invariant — a booking failure must
        # surface as a normal error, never a silently unbooked pass-through
        stamp = datetime.now().strftime("%Y-%m-%d")
        for card_rel, ids in sorted(by_card.items()):
            log = repo / card_rel / "log.md"
            with open(log, "a", encoding="utf-8") as f:
                f.write("\n- `[纠错]` diff 守卫显式放行（--allow-approved-edit，%s）：%s"
                        "——已批块比对面改动随本提交放行（LLD-8 记账）。\n"
                        % (stamp, "、".join(sorted(set(ids)))))
        return []
    if findings:
        print("diff-guard: %d finding(s) — docs commit blocked" % len(findings),
              file=sys.stderr)   # review #11: sweep runs unwatched, stderr keeps it loud
    return findings


def config_path() -> Path:
    return Path.home() / ".config" / "xg-knowledge-wiki" / "config.yaml"


def _load(text: str):
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return None


def parse_key(text: str, key: str, default: str) -> str:
    """Read a top-level scalar key (root:/dev_root:) — PyYAML when present, else a tiny parser."""
    data = _load(text)
    if data is not None:
        return str(data.get(key) or default)
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith(f"{key}:") and not raw.startswith(" "):
            val = s.split(":", 1)[1].split("#", 1)[0].strip().strip("\"'")
            if val:
                return val
    return default


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )


def scoped_pathspecs(kind: str, project: str) -> list:
    """project name -> pathspec prefixes for this repo's layout (R4).

    Pure prefix mapping — dev_root/KB lay out by project as the first path level, so
    this needs no read of the shared config's `projects:` map (that maps product-repo
    paths, not these data-repo subdirs).
    """
    if kind == "kb":
        return [f"raw/{project}", f"wiki/{project}"]
    return [project]


def parse_porcelain_z(raw: str) -> list:
    """`git status --porcelain -z` output -> flat list of touched paths.

    -z avoids core.quotePath mangling non-ASCII paths. A rename/copy entry (XY where
    X or Y is R/C) carries an extra NUL-terminated orig-path field after the path;
    skip it — the new path is what matters for scoping.
    """
    fields = raw.split("\0")
    paths = []
    i = 0
    while i < len(fields) and fields[i]:
        entry = fields[i]
        status, path = entry[:2], entry[3:]
        paths.append(path)
        if status[0] in ("R", "C"):
            i += 1
        i += 1
    return paths


def group_of(path: str, kind: str) -> str:
    """First-level project group for a touched path; '(root)' for unowned files (R6)."""
    parts = path.split("/")
    if kind == "kb":
        if len(parts) >= 3 and parts[0] in ("raw", "wiki"):
            return parts[1]
        return "(root)"
    if len(parts) >= 2:
        return parts[0]
    return "(root)"


def existing_pathspecs(repo: Path, pathspecs: list) -> list:
    """Filter to pathspecs git actually knows about (on disk or tracked) — R1/R4 guard.

    `git add -A -- <ps>...` / `git commit -- <ps>...` abort the WHOLE call if ANY
    pathspec matches nothing at all (fatal, exit 128) — even when other pathspecs in
    the same call would have matched. Filtering first turns an unknown project, or a
    project missing one of the two KB subdirs, into a clean empty/partial scope
    instead of a hard git failure (verified against real git, not assumed).
    """
    kept = []
    for ps in pathspecs:
        if (repo / ps).exists() or git(repo, "ls-files", "--", ps).stdout.strip():
            kept.append(ps)
    return kept


def sweep_groups(repo: Path, kind: str) -> dict:
    """All touched paths in `repo`, grouped by project ('(root)' for unowned) — R2/R6.

    `-uall` expands a brand-new untracked directory into its individual files —
    without it git reports just the directory (e.g. `wiki/`), which would misgroup an
    entirely-new project's files into '(root)'.
    """
    status = git(repo, "status", "--porcelain", "-uall", "-z")
    groups = {}
    for path in parse_porcelain_z(status.stdout):
        groups.setdefault(group_of(path, kind), []).append(path)
    return groups


def is_repo(repo: Path) -> bool:
    # Must be its own work-tree toplevel: merely being inside an ancestor's
    # work tree would send `git add -A` up into that repo.
    res = git(repo, "rev-parse", "--show-toplevel")
    if res.returncode != 0:
        return False
    try:
        return Path(res.stdout.strip()).resolve() == repo.resolve()
    except OSError:
        return False


def _tag_subject(message: str, tag: str) -> str:
    """Insert `tag` at the end of the commit message's subject (first) line, not
    wherever the string happens to end — `git log --oneline` shows only the subject,
    so a suffix appended after a multi-line `--reason` body would never surface there."""
    subject, sep, body = message.partition("\n")
    return f"{subject} {tag}" + sep + body


def _add_commit(repo: Path, pathspecs: list, message: str) -> subprocess.CompletedProcess:
    """Stage and commit exactly `pathspecs` (D4: the same pathspec on both `add` and
    `commit` — scoping only `add` would still let a path a concurrent session staged in
    its own add→commit window get swept into this commit at commit time)."""
    git(repo, "add", "-A", "--", *pathspecs)
    return git(repo, "commit", "-m", message, "--", *pathspecs)


def _commit_scoped(repo: Path, label: str, kind: str, message: str, project: str, inited: bool,
                   allow: bool = False, spec_override: list = None,
                   scope_desc: str = None) -> list:
    """`--project` mode (R1/R3/R4): commit only `project`'s pathspecs, ≤1 commit.
    `--card` mode (027 HLD-6) reuses this with an explicit pathspec list."""
    scope_desc = scope_desc or f"--project {project}"
    pathspecs = existing_pathspecs(repo, spec_override if spec_override is not None
                                   else scoped_pathspecs(kind, project))
    if inited:
        pathspecs = pathspecs + [".gitignore"]  # D3: never lost to scoping
    if not pathspecs:
        return [f"{label}: nothing to commit for {scope_desc}"]
    guard = diff_guard(repo, kind, pathspecs, allow)
    if guard:
        return ([f"{label}: BLOCKED — LLD-8 diff guard (pass --allow-approved-edit to override):"]
                + ["  " + g for g in guard])
    msg = ("init: " + label + " repo\n\n" + message) if inited else message
    res = _add_commit(repo, pathspecs, msg)
    if res.returncode != 0:
        return [f"{label}: nothing committed for {scope_desc} "
                f"({res.stdout.strip() or res.stderr.strip()})"]
    head = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    lines = [f"{label}: committed {head} ({scope_desc}){' (initialized)' if inited else ''}"]
    leftover = parse_porcelain_z(git(repo, "status", "--porcelain", "-uall", "-z").stdout)
    if leftover:
        lines.append(f"{label}: {len(leftover)} path(s) left uncommitted "
                      f"(out of scope for {scope_desc}): " + ", ".join(leftover))
    return lines


def group_pathspecs(group: str, kind: str, paths: list) -> list:
    """Pathspec for one sweep group — a project prefix, or the literal paths for '(root)'
    (unowned files share no common prefix to scope by)."""
    if group == "(root)":
        return paths
    return scoped_pathspecs(kind, group)


def _commit_sweep(repo: Path, label: str, kind: str, message: str, inited: bool,
                  allow: bool = False) -> list:
    """No `--project`: safety-net sweep (R2) — one commit per project group, `(root)`
    catching unowned stragglers (R6). A freshly-`init`-ed `.gitignore` is itself unowned,
    so `sweep_groups()` already places it in `(root)` — D3 falls out for free, no
    special-casing needed."""
    groups = sweep_groups(repo, kind)
    if not groups and not inited:
        return [f"{label}: clean — nothing to commit"]
    lines = []
    for group in sorted(groups, key=lambda g: (g == "(root)", g)):
        pathspecs = existing_pathspecs(repo, group_pathspecs(group, kind, groups[group]))
        if not pathspecs:
            continue
        guard = diff_guard(repo, kind, pathspecs, allow)
        if guard:
            lines.append(f"{label}: group {group} BLOCKED — LLD-8 diff guard "
                         "(pass --allow-approved-edit to override):")
            lines += ["  " + g for g in guard]
            continue
        msg = _tag_subject(message, f"[{group}]")
        res = _add_commit(repo, pathspecs, msg)
        if res.returncode != 0:
            lines.append(f"{label}: nothing committed for group {group} "
                          f"({res.stdout.strip() or res.stderr.strip()})")
            continue
        head = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
        lines.append(f"{label}: committed {head} [{group}]")
    return lines or [f"{label}: clean — nothing to commit"]


def card_pathspecs(docs: Path, card: str):
    """`<project>/<NNN>` -> (project, docs pathspecs) by literal glob
    `<project>/<NNN>-*` (027 HLD-6): no fuzzy match; zero or multiple hits 报错不静默
    (resolve_card's SystemExit would be swallowed by the exit-0 contract — panel F14).
    Scope = the card dir + the project's shared board files."""
    project, _, nnn = card.partition("/")
    if not project or not re.fullmatch(r"\d{3}", nnn or ""):
        return None, [f"--card expects <project>/<NNN> (got {card!r}) — nothing committed"]
    hits = sorted(d.name for d in (docs / project).glob(nnn + "-*") if d.is_dir()) \
        if (docs / project).is_dir() else []
    if len(hits) != 1:
        return None, [f"--card {card}: {len(hits)} card dirs match "
                      f"({', '.join(hits) or 'none'}) — loud fail, nothing committed"]
    return project, [f"{project}/{hits[0]}", f"{project}/index.md", f"{project}/roadmap.md"]


def commit_repo(repo: Path, label: str, kind: str, message: str, project: str = None,
                card: str = None, allow: bool = False) -> list:
    if not repo.exists():
        return [f"{label}: {repo} does not exist — skipped"]
    inited = False
    if not is_repo(repo):
        if git(repo, "init").returncode != 0:
            return [f"{label}: git init failed — skipped"]
        gi = repo / ".gitignore"
        if not gi.exists():
            gi.write_text(GITIGNORE, encoding="utf-8")
        inited = True

    if card is not None:
        if kind == "docs":
            cproj, specs = card_pathspecs(repo, card)
            if cproj is None:
                return [f"{label}: " + ln for ln in specs]
            return _commit_scoped(repo, label, kind, message, cproj, inited, allow,
                                  spec_override=specs, scope_desc=f"--card {card}")
        # the KB repo has no card dirs — --card keeps its KB half at project
        # scope (027 HLD-6/F6)
        return _commit_scoped(repo, label, kind, message, card.partition("/")[0],
                              inited, allow, scope_desc=f"--card {card} (KB project 级)")
    if project is not None:
        return _commit_scoped(repo, label, kind, message, project, inited, allow)
    return _commit_sweep(repo, label, kind, message, inited, allow)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message", "-m", default=None)
    ap.add_argument("--reason", default=None)
    ap.add_argument("--only", choices=["kb", "docs"], default=None)
    ap.add_argument("--project", default=None,
                    help="scoped mode (R3): commit only this project's paths, "
                         "in both repos (R4) — learn/improve 等项目级写入用。")
    ap.add_argument("--card", default=None, metavar="PROJECT/NNN",
                    help="card scope (027 HLD-6): docs = the card dir + the project's "
                         "index.md/roadmap.md; KB stays project-level. Gate commits "
                         "and single-card park close-outs use this.")
    ap.add_argument("--allow-approved-edit", action="store_true",
                    help="override the LLD-8 diff guard: commit approved-block "
                         "compare-face changes and book a log.md line per card.")
    a = ap.parse_args()
    if a.card and a.project:
        print("--card and --project are mutually exclusive — nothing committed")
        sys.exit(0)

    cp = config_path()
    text = cp.read_text(encoding="utf-8") if cp.exists() else ""
    kb = Path(os.path.expanduser(parse_key(text, "root", DEFAULTS["root"])))
    docs = Path(os.path.expanduser(parse_key(text, "dev_root", DEFAULTS["dev_root"])))

    if a.card:   # validate ONCE before touching either repo — the KB half must not
                 # commit ahead of a docs-side resolve failure (027 review #3)
        cproj, err = card_pathspecs(docs, a.card)
        if cproj is None:
            for ln in err:
                print(ln)
            sys.exit(0)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    default_msg = a.message or f"auto: data snapshot {stamp}"
    if a.reason:
        default_msg += f"\n\n{a.reason}"

    targets = []
    if a.only in (None, "kb"):
        targets.append((kb, "knowledge (KB)", "kb"))
    if a.only in (None, "docs"):
        targets.append((docs, "dev-workflow (docs)", "docs"))

    for repo, label, kind in targets:
        for line in commit_repo(repo, label, kind, default_msg, project=a.project,
                                card=a.card, allow=a.allow_approved_edit):
            print(line)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        sys.exit(0)  # even an argparse usage error must not block the session
    except Exception as e:
        # never block the session ("Exit 0 always")
        print(f"(commit-data-repos: skipped — {e})", file=sys.stderr)
        sys.exit(0)
