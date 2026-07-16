#!/usr/bin/env python3
"""Record and report xg-skill usage + self-feedback.

Append one JSON line per skill invocation so xg-dev-workflow / xg-knowledge-lite
accumulate a usage + feedback trail for later improvement (read by the retro loop).

KEEP IN SYNC: identical copies live at xg-dev-workflow/tools/, xg-knowledge-lite/tools/,
and ~/.claude/scripts/ — edit one, copy to the others (cp, byte-identical).

One event = one record: a KB write performed inside an xg-dev-workflow investigate/review
run is covered by that run's single record — don't also log xg-knowledge-lite/write.

Usage:
  log-usage.py log --skill xg-dev-workflow --action design \
      --score 4 --note "design-grill surfaced a missing ADR" [--project cbdb]
  log-usage.py log --skill xg-knowledge-lite --action write \
      --score 4 --note "compile produced a clean concept split" [--project cbdb]
  log-usage.py report [--skill NAME] [--action NAME] [--limit 20]

Log file resolution (first that applies):
  1. --log <path>
  2. $XG_USAGE_LOG
  3. ~/.config/xg-knowledge-wiki/usage.jsonl   (shared by both skills)
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG = Path.home() / ".config" / "xg-knowledge-wiki" / "usage.jsonl"

# Canonical action vocabulary per xg-skill (matches each SKILL.md's verb/action list).
# Off-vocabulary actions are logged anyway, with a stderr warning — fragmented action
# names break the report aggregation the retro loop depends on.
KNOWN_ACTIONS = {
    "xg-dev-workflow": {
        "new", "requirement", "design", "detail", "plan", "test", "investigate",
        "diagnose", "review", "change", "resume", "check", "retro", "status",
    },
    "xg-knowledge-lite": {"write", "compile", "query", "orient", "lint"},
}

# Recurring mis-logged spellings, normalized to the canonical verb — at write time (cmd_log)
# and again at report time (cmd_report), so pre-fix records aggregate cleanly too.
# One-off composites stay unaliased (they just warn).
ACTION_ALIASES = {
    "xg-dev-workflow": {
        # implementation-phase task work logs as plan (both implement spellings)
        "implement": "plan",
        "implement/test": "plan",
        "design-note": "design",
        "change/adr": "change",
    },
}


def canonical_action(skill, action):
    return ACTION_ALIASES.get(skill, {}).get(action, action)


def log_path(args) -> Path:
    if getattr(args, "log", None):
        return Path(os.path.expanduser(args.log))
    env = os.environ.get("XG_USAGE_LOG")
    if env:
        return Path(os.path.expanduser(env))
    return DEFAULT_LOG


def cmd_log(args):
    action = canonical_action(args.skill, args.action)
    if action != args.action:
        print(f"note: action '{args.action}' normalized to canonical '{action}'", file=sys.stderr)
    known = KNOWN_ACTIONS.get(args.skill)
    if known is not None and action not in known:
        print(
            f"warning: '{action}' is not a canonical {args.skill} action "
            f"(expected one of: {', '.join(sorted(known))}); logged anyway — "
            f"prefer the canonical verb (one event = one record)",
            file=sys.stderr,
        )
    p = log_path(args)
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "skill": args.skill,
        "action": action,
        "project": args.project,
        "score": args.score,
        "note": args.note,
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"logged {args.skill}/{action} (score={args.score}) → {p}")


def cmd_report(args):
    p = log_path(args)
    if not p.exists():
        print(f"no usage log at {p}")
        return
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    for r in rows:
        r["action"] = canonical_action(r.get("skill"), r.get("action"))
    if args.skill:
        rows = [r for r in rows if r.get("skill") == args.skill]
    if args.action:
        rows = [r for r in rows if r.get("action") == canonical_action(r.get("skill"), args.action)]
    if not rows:
        print("no matching records")
        return
    agg = defaultdict(lambda: [0, 0.0, 0])  # (skill, action) -> [uses, score_sum, scored]
    for r in rows:
        k = (r.get("skill"), r.get("action"))
        agg[k][0] += 1
        s = r.get("score")
        if isinstance(s, (int, float)):
            agg[k][1] += s
            agg[k][2] += 1
    print(f"# usage report ({len(rows)} records) — {p}")
    print(f"{'skill':<18} {'action':<14} {'uses':>4} {'avg':>5}")
    for (sk, ac), (c, ssum, sc) in sorted(agg.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        avg = f"{ssum / sc:.2f}" if sc else "  -"
        print(f"{(sk or '-'):<18} {(ac or '-'):<14} {c:>4} {avg:>5}")
    n = max(1, args.limit)
    print(f"\n# last {min(n, len(rows))} notes")
    for r in rows[-n:]:
        print(f"- [{r.get('ts', '?')}] {r.get('skill')}/{r.get('action')} "
              f"({r.get('score')}): {r.get('note')}")


def main():
    ap = argparse.ArgumentParser(description="record/report xg-skill usage + feedback")
    ap.add_argument("--log", help="override log file path")
    sub = ap.add_subparsers(dest="cmd", required=True)

    lg = sub.add_parser("log", help="append one usage record")
    lg.add_argument("--skill", required=True)
    lg.add_argument("--action", required=True, help="the verb/feature used")
    lg.add_argument("--score", type=int, choices=range(1, 6), help="1-5, how well it served the task")
    lg.add_argument("--note", default="", help="one-sentence evaluation / friction")
    lg.add_argument("--project", default=None)
    lg.set_defaults(func=cmd_log)

    rp = sub.add_parser("report", help="summarize usage + recent notes")
    rp.add_argument("--skill")
    rp.add_argument("--action")
    rp.add_argument("--limit", type=int, default=20)
    rp.set_defaults(func=cmd_report)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
