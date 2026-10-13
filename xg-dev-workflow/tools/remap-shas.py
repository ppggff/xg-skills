#!/usr/bin/env python3
"""Carry commit ids in docs across a history rewrite (rebase, squash, split, reorder).

  remap-shas.py map   --repo R --old BASE..HEAD --new BASE..HEAD [--manual F] -o MAP
  remap-shas.py apply --map MAP [--dry-run] [--exclude GLOB ...] PATH ...

map pairs each old commit with the new one(s) carrying its change:
  patch-id   same change (a plain rebase, a reorder, a reword)
  subject    same subject and author time, the change differs (a conflict resolved)
  squash     a run of old commits whose combined change is one new commit
  split      one old commit whose change is a run of new commits; it maps to the last
  manual     a line "old new" of --manual, for what the above cannot pair
Old commits left unpaired are listed and keep their ids in the docs.

apply replaces every hex token of 7 to 40 characters that is a prefix of exactly
one old commit of the map with the new id cut to the same length.
"""
import argparse
import fnmatch
import os
import re
import subprocess
import sys


class GitError(Exception):
    pass


def git(repo, *args, stdin=None):
    r = subprocess.run(["git", "-C", repo, *args], input=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        raise GitError(f"git {' '.join(args[:3])}: {(r.stderr.strip().splitlines() or ['failed'])[-1]}")
    return r.stdout


def commits(repo, rng):
    out = git(repo, "log", "--reverse", "--no-merges", "--format=%H%x00%at%x00%s", rng)
    return [tuple(l.split("\0")) for l in out.splitlines() if l]


def patch_ids(repo, rng):
    out = git(repo, "log", "--no-merges", "-p", "--format=commit %H", rng)
    ids = git(repo, "patch-id", "--stable", stdin=out)
    return {c: p for p, c in (l.split() for l in ids.splitlines())}


def diff_id(repo, a, b):
    """patch-id of the change from a's parent to b."""
    out = git(repo, "diff", a + "^", b)
    ids = git(repo, "patch-id", "--stable", stdin=out).split()
    return ids[0] if ids else ""


def build(repo, old_rng, new_rng, manual):
    old, new = commits(repo, old_rng), commits(repo, new_rng)
    opid, npid = patch_ids(repo, old_rng), patch_ids(repo, new_rng)
    pairs = {}  # old sha -> (new sha, how)
    used = set()

    by_pid = {}
    for sha, _, _ in new:
        by_pid.setdefault(npid.get(sha), []).append(sha)
    for sha, _, _ in old:
        for n in by_pid.get(opid.get(sha), []):
            if n not in used and opid.get(sha):
                pairs[sha] = (n, "patch-id")
                used.add(n)
                break

    by_subj = {}
    for sha, at, subj in new:
        if sha not in used:
            by_subj.setdefault((at, subj), []).append(sha)
    for sha, at, subj in old:
        if sha in pairs:
            continue
        cand = [n for n in by_subj.get((at, subj), []) if n not in used]
        if len(cand) == 1:
            pairs[sha] = (cand[0], "subject")
            used.add(cand[0])

    def runs(seq, left):
        """contiguous runs of commits in seq that are still unpaired."""
        cur, out = [], []
        for sha, _, _ in seq:
            if sha in left:
                cur.append(sha)
            else:
                if cur:
                    out.append(cur)
                cur = []
        if cur:
            out.append(cur)
        return out

    old_left = {s for s, _, _ in old if s not in pairs}
    new_left = {s for s, _, _ in new if s not in used}
    # squash: a run of old commits whose combined change is one new commit
    for n in [s for s, _, _ in new if s in new_left]:
        for run in runs(old, old_left):
            for i in range(len(run)):
                for j in range(i + 1, len(run)):
                    if diff_id(repo, run[i], run[j]) == npid.get(n):
                        for o in run[i:j + 1]:
                            pairs[o] = (n, "squash")
                            old_left.discard(o)
                        new_left.discard(n)
                        break
                if n not in new_left:
                    break
            if n not in new_left:
                break
    # split: one old commit whose change is a run of new commits
    for o in [s for s, _, _ in old if s in old_left]:
        done = False
        for run in runs(new, new_left):
            for i in range(len(run)):
                for j in range(i + 1, len(run)):
                    if diff_id(repo, run[i], run[j]) == opid.get(o):
                        pairs[o] = (run[j], "split:" + ",".join(x[:9] for x in run[i:j + 1]))
                        old_left.discard(o)
                        for x in run[i:j + 1]:
                            new_left.discard(x)
                        done = True
                        break
                if done:
                    break
            if done:
                break

    if manual:
        with open(manual) as fh:
            lines = fh.readlines()
        for line in lines:
            f = line.split()
            if len(f) >= 2 and not line.startswith("#"):
                o = git(repo, "rev-parse", f[0]).strip()
                n = git(repo, "rev-parse", f[1]).strip()
                pairs[o] = (n, "manual")
                old_left.discard(o)

    subj = {s: t for s, _, t in old}
    return old, pairs, sorted(old_left, key=[s for s, _, _ in old].index), subj


def cmd_map(a):
    old, pairs, left, subj = build(a.repo, a.old, a.new, a.manual)
    with open(a.o, "w") as f:
        f.write(f"# old\tnew\thow\tsubject   ({a.old} -> {a.new})\n")
        for sha, _, _ in old:
            if sha in pairs:
                n, how = pairs[sha]
                f.write(f"{sha}\t{n}\t{how}\t{subj[sha]}\n")
    counts = {}
    for _, how in pairs.values():
        counts[how.split(":")[0]] = counts.get(how.split(":")[0], 0) + 1
    print(f"{len(old)} old commits: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
          + f", {len(left)} unpaired")
    for s in left:
        print(f"  unpaired {s[:9]} {subj[s]}")
    return 0


TOKEN = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])")


def cmd_apply(a):
    pairs = []
    with open(a.map) as fh:
        lines = fh.readlines()
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        o, n = line.split("\t")[:2]
        pairs.append((o, n))

    def swap(m):
        tok = m.group(0)
        hits = [n for o, n in pairs if o.startswith(tok)]
        if len(hits) != 1:
            return tok
        return hits[0][:len(tok)]

    files = []
    for p in a.paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                if "/.git" in root:
                    continue
                files += [os.path.join(root, n) for n in names]
        else:
            files.append(p)
    total = 0
    for path in sorted(files):
        if any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(os.path.basename(path), g) for g in a.exclude):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        n = 0

        def count(m):
            nonlocal n
            new = swap(m)
            n += new != m.group(0)
            return new
        out = TOKEN.sub(count, text)
        if n:
            total += n
            print(f"{n:5d}  {path}")
            if not a.dry_run:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(out)
    print(f"{total} ids {'would be ' if a.dry_run else ''}replaced")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("map")
    m.add_argument("--repo", default=".")
    m.add_argument("--old", required=True, help="BASE..HEAD of the history before the rewrite")
    m.add_argument("--new", required=True, help="BASE..HEAD of the history after it")
    m.add_argument("--manual", help='lines "old new" for pairs the matching cannot find')
    m.add_argument("-o", required=True, help="the map file to write")
    p = sub.add_parser("apply")
    p.add_argument("--map", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--exclude", action="append", default=[], help="glob of files to leave alone")
    p.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    try:
        return cmd_map(a) if a.cmd == "map" else cmd_apply(a)
    except (GitError, OSError) as e:
        print(f"remap-shas: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
