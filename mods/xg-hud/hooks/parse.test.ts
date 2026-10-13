import { describe, expect, test } from 'claude-code/testing'

import { kbPathsIn, parsePointer, parseBacklog, parseConfig, parseDesign, projectOf } from './parse'

const HOME = '/Users/me'
const CONFIG = `root: ~/knowledge
dev_root: ~/dev-workflow
gitweb_repos:
- ~/xxx/hdw-agent
projects:
  cbdb:
    paths:
    - ~/xxx/cbdb
  cbcloud:
    paths:
    - ~/xxx/cbdb/cbcloud
  xg-skills:
    paths:
    - ~/xxx/xg-skills
`

describe('config', () => {
  const config = parseConfig(CONFIG, HOME)
  test('roots expand ~', () => {
    expect(config.root).toBe('/Users/me/knowledge')
    expect(config.devRoot).toBe('/Users/me/dev-workflow')
  })
  test('quoted and commented roots', () => {
    const quoted = parseConfig('root: "~/kb"  # the KB\ndev_root: \'~/dw\'\n', HOME)
    expect(quoted.root).toBe('/Users/me/kb')
    expect(quoted.devRoot).toBe('/Users/me/dw')
  })
  test('gitweb_repos is not a project', () => {
    expect(Object.keys(config.projects)).toEqual(['cbdb', 'cbcloud', 'xg-skills'])
  })
  test('longest path prefix wins', () => {
    expect(projectOf('/Users/me/xxx/cbdb/cbcloud/src', config)).toBe('cbcloud')
    expect(projectOf('/Users/me/xxx/cbdb', config)).toBe('cbdb')
    expect(projectOf('/Users/me/xxx/cbdbx', config)).toBe(null)
  })
})

describe('design.md', () => {
  const card = parseDesign(`---
id: 045
title: viewer-todo-editor-plus
governance: lite
status: done      # draft | executing | closing | done
---
# 045 viewer-todo-editor-plus

## 当前摘要
已完成并收卡。

## 目标与边界
做：下列 Req。

### Req-1 已验证 — 进入编辑
body
### Req-2 待做 — 工具栏与带时间的 todo
`)
  test('frontmatter strips trailing comment', () => {
    expect(card.status).toBe('done')
    expect(card.id).toBe('045')
  })
  test('summary is the section body only', () => {
    expect(card.summary).toBe('已完成并收卡。')
  })
  test('reqs carry state word and title', () => {
    expect(card.reqs).toEqual([
      { n: 1, word: '已验证', title: '进入编辑' },
      { n: 2, word: '待做', title: '工具栏与带时间的 todo' },
    ])
  })
})

describe('backlog, KB and card paths', () => {
  test('backlog rows skip slug lines', () => {
    const rows = parseBacklog('📚 KB compile backlog (xg-knowledge-lite):\n  cbdb: 43 raw / 27 wiki · 7 uncompiled\n      - x\n  devenv: 1 raw / 0 wiki · 0 uncompiled\n')
    expect(rows).toEqual([
      { project: 'cbdb', raw: 43, wiki: 27, uncompiled: 7, slugs: ['x'] },
      { project: 'devenv', raw: 1, wiki: 0, uncompiled: 0, slugs: [] },
    ])
  })
  test('KB paths a call names', () => {
    expect(kbPathsIn('{"file_path":"/Users/me/knowledge/raw/cbdb/x.md"}', '/Users/me/knowledge', HOME)).toEqual(['raw/cbdb/x.md'])
    expect(kbPathsIn('grep -rn foo ~/knowledge/wiki/cbdb/ ~/knowledge', '/Users/me/knowledge', HOME)).toEqual(['wiki/cbdb', ''])
    expect(kbPathsIn('ls /Users/me/xxx', '/Users/me/knowledge', HOME)).toEqual([])
    expect(kbPathsIn('[ -f ~/knowledge/$l.md ]', '/Users/me/knowledge', HOME)).toEqual([''])
    expect(kbPathsIn('cat ~/knowledge/raw/*/x.md', '/Users/me/knowledge', HOME)).toEqual(['raw'])
  })
  test('active-card pointer: one card line or nothing', () => {
    expect(parsePointer('xg-skills/047-session-active-card\n')).toBe('xg-skills/047-session-active-card')
    expect(parsePointer('')).toBe(null)
    expect(parsePointer('xg-skills/notes')).toBe(null)
    expect(parsePointer('../etc/047-x')).toBe(null)
    expect(parsePointer('../047-x')).toBe(null)
    expect(parsePointer('a/047-x\nb/048-y')).toBe(null)
  })
})
