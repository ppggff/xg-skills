/** Pure parsers: shared config, card design.md, kb-backlog output, paths named by tool calls. */

import type { HudKbRow, HudReq } from '../types'

export type Config = { root: string; devRoot: string; projects: Record<string, string[]> }

export function expandHome(path: string, home: string): string {
  return path.startsWith('~/') ? home + path.slice(1) : path
}

// A YAML scalar as the config writes it: an optional trailing ` # comment` and optional quotes.
function scalar(raw: string): string {
  return raw.replace(/\s+#.*$/, '').trim().replace(/^(['"])(.*)\1$/, '$2')
}

export function parseConfig(text: string, home: string): Config {
  const config: Config = { root: `${home}/knowledge`, devRoot: `${home}/dev-workflow`, projects: {} }
  let section = ''
  let project = ''
  for (const line of text.split('\n')) {
    const top = line.match(/^(\w[\w-]*):\s*(.*)$/)
    if (top) {
      section = top[1]!
      const value = scalar(top[2] ?? '')
      if (section === 'root' && value) config.root = expandHome(value, home)
      if (section === 'dev_root' && value) config.devRoot = expandHome(value, home)
      continue
    }
    if (section !== 'projects') continue
    const name = line.match(/^ {2}([\w.-]+):\s*$/)
    if (name) {
      project = name[1]!
      config.projects[project] = []
      continue
    }
    const path = line.match(/^\s+-\s+(.+?)\s*$/)
    if (path && project) config.projects[project]!.push(expandHome(path[1]!, home))
  }
  return config
}

export function projectOf(cwd: string, config: Config): string | null {
  let best: string | null = null
  let bestLength = -1
  for (const [name, paths] of Object.entries(config.projects)) {
    for (const path of paths) {
      const isUnder = cwd === path || cwd.startsWith(path + '/')
      if (isUnder && path.length > bestLength) {
        best = name
        bestLength = path.length
      }
    }
  }
  return best
}

export function frontmatter(text: string): Record<string, string> {
  const block = text.match(/^---\n([\s\S]*?)\n---/)
  const fields: Record<string, string> = {}
  if (!block) return fields
  for (const line of block[1]!.split('\n')) {
    const field = line.match(/^(\w+):\s*(.*?)\s*(?:#.*)?$/)
    if (field) fields[field[1]!] = field[2]!
  }
  return fields
}

export function parseDesign(text: string): { id: string; title: string; status: string; summary: string; reqs: HudReq[] } {
  const fields = frontmatter(text)
  const summaryBlock = text.match(/^## 当前摘要\s*\n([\s\S]*?)(?=^## |$(?![\s\S]))/m)
  const reqs = [...text.matchAll(/^### Req-(\d+)\s+(\S+)\s+[—–-]+\s+(.*)$/gm)].map(m => ({
    n: Number(m[1]!),
    word: m[2]!,
    title: m[3]!.trim(),
  }))
  return {
    id: fields.id ?? '',
    title: fields.title ?? '',
    status: fields.status ?? '',
    summary: (summaryBlock?.[1] ?? '').trim(),
    reqs,
  }
}

export function parseBacklog(text: string): HudKbRow[] {
  const rows: HudKbRow[] = []
  for (const line of text.split('\n')) {
    const row = line.match(/^ {2}(\S+): (\d+) raw \/ (\d+) wiki · (\d+) uncompiled/)
    if (row) {
      rows.push({ project: row[1]!, raw: Number(row[2]!), wiki: Number(row[3]!), uncompiled: Number(row[4]!), slugs: [] })
      continue
    }
    const slug = line.match(/^ {6}- (\S+)/)
    if (slug && rows.length) rows[rows.length - 1]!.slugs.push(slug[1]!)
  }
  return rows
}

/** KB paths a tool call names, relative to the KB root ('' for the root itself). */
export function kbPathsIn(text: string, root: string, home: string): string[] {
  const spelled = text.split('~/').join(home + '/')
  const escaped = root.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const found = [...spelled.matchAll(new RegExp(`${escaped}(?:/([\\w./-]*))?`, 'g'))].map(m => (m[1] ?? '').replace(/\/$/, ''))
  return [...new Set(found)]
}

/** The active-card pointer file's one line `<project>/<NNN-slug>`; anything else reads as no card. */
export function parsePointer(text: string): string | null {
  const line = text.trim()
  return /^(?!\.\.?\/)[\w.-]+\/\d{3}-[\w.-]+$/.test(line) ? line : null
}
