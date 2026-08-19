#!/usr/bin/env python3
"""Supersede sweep: grep card docs for retired phrasings (M2 mode-变更 aid, see change.md).

Usage:
  check-superseded-phrases.py <card-dir> --terms "旧词A,旧词B"
  check-superseded-phrases.py <card-dir> --terms-file retired.txt [--exclude notes]
  check-superseded-phrases.py <card-dir> --from-card    # terms from the card's machine
                                                        # anchors (ADR 被取代表述 list lines
                                                        # + Change-log 被取代表述 sub-lists)

Scans *.md under the card dir. Prints file:line: [term] excerpt. Exit 1 if hits, 0 if clean.
Adjudication is the caller's job: change-log/grill/notes history may legitimately keep old
phrasing (annotate as 历史表述); every other hit is rewritten or its retention justified.
"""
import argparse
import glob
import os
import pathlib
import re
import sys

TERM = re.compile(r'`([^`]+)`')
QUOTE = re.compile(r'[「『]([^」』]+)[」』]')
PHASE_DOCS = ('requirement.md', 'design.md', 'detail.md')


def _term_from_line(s):
    """(term|None, malformed?) for one list line. A CJK-quoted phrase wins (the
    legacy-and-natural way to retire a *phrase*); a backtick span is the fallback
    (the template form). A quote with a backtick inside is ambiguous — flagged,
    never guessed (021 review #1). `<…>` spans are template placeholders."""
    q = QUOTE.search(s)
    if q:
        if '`' in q.group(1):
            return None, True
        term = re.sub(r'\*\*', '', q.group(1)).strip()
        return (term, False) if len(term) >= 2 else (None, True)
    m = TERM.search(s)
    if m:
        if re.fullmatch(r'<[^>]+>', m.group(1)):
            return None, False          # placeholder line, not a term claim
        return (m.group(1), False) if len(m.group(1)) >= 2 else (None, True)
    return None, True


def _section(text, title_pat, level=2):
    """Body of the first level-2 heading matching title_pat, else ''."""
    for m in re.finditer(r'^%s\s+(.+)$' % ('#' * level), text, re.M):
        if re.search(title_pat, m.group(1)):
            start = m.end()
            nxt = re.search(r'^#{2,%d}\s' % level, text[start:], re.M)
            return text[start:start + nxt.start()] if nxt else text[start:]
    return ''


def terms_from_card(card_dir):
    """(terms, findings, exemptions) from the card's machine anchors (021 G4).
    exemptions = (class, reason) pairs for the silent not-harvested paths — a
    side channel for the resident check's exemption stream (023); this tool's
    own CLI judgment and output ignore it.

    ADR「被取代表述」sections: a list line's first backtick span is the term; a list
    line without one — or a non-list line that carries a backtick span — is an
    `adr-retired-format` finding (a malformed term is flagged, never guessed at);
    bare prose lines are annotation. A superseding ADR (its Supersedes section names
    an ADR) with no 被取代表述 section is `adr-retired-missing`. Phase-doc Change-log
    entries contribute via an indented sub-list under a 被取代表述-titled list line.
    """
    terms, findings, exemptions = [], [], []
    for f in sorted(glob.glob(os.path.join(card_dir, 'adr', '*.md'))):
        base = 'adr/' + os.path.basename(f)
        text = re.sub(r'<!--.*?-->', '', pathlib.Path(f).read_text(errors='replace'),
                      flags=re.S)   # template guidance rides in comments — never terms
        st = re.search(r'^Status:\s*(\w+)', text, re.M)
        if st and st.group(1).lower() in ('superseded', 'deprecated', 'withdrawn'):
            # a dead decision's retired-terms are no longer authoritative
            exemptions.append(('not-yet-due', 'dead ADR, file not harvested'))
            continue
        sect = _section(text, r'被取代表述')
        if not sect.strip():
            if re.search(r'ADR-\d{4}', _section(text, r'Supersedes')):
                findings.append('adr-retired-missing: ' + base)
            else:
                exemptions.append(('carrier-missing',
                                   'ADR without 被取代表述 section or Supersedes id'))
            continue
        for line in sect.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith('-'):
                term, bad = _term_from_line(s)
                if term:
                    terms.append(term)
                elif bad:
                    findings.append('adr-retired-format: %s %r' % (base, s[:40]))
            elif TERM.search(s) or QUOTE.search(s):
                findings.append('adr-retired-format: %s %r' % (base, s[:40]))
    for name in PHASE_DOCS:
        p = os.path.join(card_dir, name)
        if not os.path.exists(p):
            exemptions.append(('carrier-missing',
                               'phase doc missing, anchors not harvested'))
            continue
        clog = _section(pathlib.Path(p).read_text(errors='replace'),
                        r'Change log|Change notes')
        if not clog.strip():
            exemptions.append(('carrier-missing',
                               'no Change-log section / 被取代表述 sub-list'))
            continue
        in_anchor, anchor_indent, saw_anchor = False, 0, False
        for line in clog.splitlines():
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            s = line.strip()
            if s.startswith('-') and '被取代表述' in s:
                in_anchor, anchor_indent, saw_anchor = True, indent, True
                continue
            if in_anchor:
                if s.startswith('-') and indent > anchor_indent:
                    term, bad = _term_from_line(s)
                    if term:
                        terms.append(term)
                    elif bad:
                        findings.append('adr-retired-format: %s %r' % (name, s[:40]))
                else:
                    in_anchor = False
        if not saw_anchor:
            exemptions.append(('carrier-missing',
                               'no Change-log section / 被取代表述 sub-list'))
    return terms, findings, exemptions


def scan(root, terms, exclude=()):
    """[(relpath, lineno, term, stripped line)] for every term occurrence."""
    hits = []
    for md in sorted(pathlib.Path(root).rglob('*.md')):
        rel = md.relative_to(root)
        if any(part in exclude for part in rel.parts[:-1]):
            continue
        for i, line in enumerate(md.read_text(errors='replace').splitlines(), 1):
            for t in terms:
                if t in line:
                    hits.append((str(rel), i, t, line.strip()))
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('card', help='requirement/card directory (or any docs dir)')
    ap.add_argument('--terms', default='', help='comma-separated retired phrasings')
    ap.add_argument('--terms-file', help='file with one phrasing per line (# comments ok)')
    ap.add_argument('--from-card', action='store_true',
                    help='read terms from the card\'s machine anchors (021 G4)')
    ap.add_argument('--exclude', action='append', default=[],
                    help='subdir name to skip (repeatable, e.g. --exclude notes)')
    args = ap.parse_args()

    root = pathlib.Path(args.card)
    if not root.is_dir():
        sys.exit(f'not a directory: {root}')

    terms = [t.strip() for t in args.terms.split(',') if t.strip()]
    if args.terms_file:
        for line in pathlib.Path(args.terms_file).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                terms.append(line)
    anchor_findings = []
    if args.from_card:
        got, anchor_findings, _ = terms_from_card(str(root))   # exemptions: resident-check face only
        terms += got
        # informational: legacy anchor shapes are data debt, not sweep hits — the
        # exit code belongs to term hits alone (021 review #6; change.md runs this
        # on old cards too)
        for f in anchor_findings:
            print('⚠ ' + f)
    if not terms:
        if args.from_card:
            print('-- no machine anchors --')
            sys.exit(0)
        sys.exit('no terms given (--terms / --terms-file / --from-card)')

    hits = scan(root, terms, exclude=args.exclude)
    for rel, i, t, line in hits:
        print(f'{rel}:{i}: [{t}] {line[:110]}')
    if hits:
        print(f'-- {len(hits)} hit(s): rewrite / annotate-as-历史表述 / justify each --')
    else:
        print('-- clean --')
    sys.exit(1 if hits else 0)


if __name__ == '__main__':
    main()
