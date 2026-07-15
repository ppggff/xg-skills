#!/usr/bin/env python3
"""Supersede sweep: grep card docs for retired phrasings (M2 mode-变更 aid, see change.md).

Usage:
  check-superseded-phrases.py <card-dir> --terms "旧词A,旧词B"
  check-superseded-phrases.py <card-dir> --terms-file retired.txt [--exclude notes]

Scans *.md under the card dir. Prints file:line: [term] excerpt. Exit 1 if hits, 0 if clean.
Adjudication is the caller's job: change-log/grill/notes history may legitimately keep old
phrasing (annotate as 历史表述); every other hit is rewritten or its retention justified.
"""
import argparse
import pathlib
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('card', help='requirement/card directory (or any docs dir)')
    ap.add_argument('--terms', default='', help='comma-separated retired phrasings')
    ap.add_argument('--terms-file', help='file with one phrasing per line (# comments ok)')
    ap.add_argument('--exclude', action='append', default=[],
                    help='subdir name to skip (repeatable, e.g. --exclude notes)')
    args = ap.parse_args()

    terms = [t.strip() for t in args.terms.split(',') if t.strip()]
    if args.terms_file:
        for line in pathlib.Path(args.terms_file).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                terms.append(line)
    if not terms:
        sys.exit('no terms given (--terms / --terms-file)')

    root = pathlib.Path(args.card)
    if not root.is_dir():
        sys.exit(f'not a directory: {root}')

    hits = 0
    for md in sorted(root.rglob('*.md')):
        rel = md.relative_to(root)
        if any(part in args.exclude for part in rel.parts[:-1]):
            continue
        for i, line in enumerate(md.read_text(errors='replace').splitlines(), 1):
            for t in terms:
                if t in line:
                    print(f'{rel}:{i}: [{t}] {line.strip()[:110]}')
                    hits += 1
    if hits:
        print(f'-- {hits} hit(s): rewrite / annotate-as-历史表述 / justify each --')
    else:
        print('-- clean --')
    sys.exit(1 if hits else 0)


if __name__ == '__main__':
    main()
