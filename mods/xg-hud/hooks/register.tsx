import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, RenderChildren } from 'claude-code'

import type { HudCard, HudCardSlot, HudKb, HudKbStart, HudReq, HudTimes, HudTodo } from '../types'
import { frontmatter, kbPathsIn, parseBacklog, parseConfig, parseDesign, parsePointer, projectOf } from './parse'
import type { Config } from './parse'

const card = atom({ plugin: 'xg-hud', key: 'card' } as const, null)
const kb = atom({ plugin: 'xg-hud', key: 'kb' } as const, null)
const kbStart = atom({ plugin: 'xg-hud', key: 'kbStart' } as const, null)
const isKbOpen = atom({ plugin: 'xg-hud', key: 'isKbOpen' } as const, false)
const isCardOpen = atom({ plugin: 'xg-hud', key: 'isCardOpen' } as const, false)
const kbReads = atom({ plugin: 'xg-hud', key: 'kbReads' } as const, [])
const kbTouched = atom({ plugin: 'xg-hud', key: 'kbTouched' } as const, [])
const isDoneShown = atom({ plugin: 'xg-hud', key: 'isDoneShown' } as const, false)
const cardPage = atom({ plugin: 'xg-hud', key: 'cardPage' } as const, 0)
const kbPage = atom({ plugin: 'xg-hud', key: 'kbPage' } as const, 0)
const todos = atom({ plugin: 'xg-hud', key: 'todos' } as const, [])
const isTodoOpen = atom({ plugin: 'xg-hud', key: 'isTodoOpen' } as const, false)
const todoSessionRefs = atom({ plugin: 'xg-hud', key: 'todoSessionRefs' } as const, [])
const todoAt = atom({ plugin: 'xg-hud', key: 'todoAt' } as const, 0)
const times = atom({ plugin: 'xg-hud', key: 'times' } as const, { message: null, reply: null } as HudTimes)
const isMsgOpen = atom({ plugin: 'xg-hud', key: 'isMsgOpen' } as const, false)
const msgNow = atom({ plugin: 'xg-hud', key: 'msgNow' } as const, 0)

type Ctx = { home: string; cwd: string; config: Config }
type $ = EngineInterface

const DONE_WORDS = new Set(['已验证', '已完成', '完成'])
const DROPPED_WORDS = new Set(['放弃', '搁置', '移出', '不做'])
const NARROW = 80
const SEP = '｜'
const SEP_CELLS = 2

function cells(text: string): number {
  let width = 0
  for (const ch of text) width += /[\u1100-\u115F\u2E80-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE4F\uFF00-\uFF60\uFFE0-\uFFE6]/.test(ch) ? 2 : 1
  return width
}

// Detail lines read left-aligned and are padded to one width, so the ┤/┘ connectors form a column at the right edge.
function branch(lines: string[], isNarrow: boolean, width: number): string[] {
  if (isNarrow) return lines
  return lines.map((line, i) => `${line}${' '.repeat(width - cells(line))} ${i === lines.length - 1 ? '┘' : '┤'}`)
}

function clip(text: string, max: number): string {
  if (cells(text) <= max) return text
  let out = ''
  for (const ch of text) {
    if (cells(out + ch) > max - 1) break
    out += ch
  }
  return out + '…'
}

function progressSvg(done: number, total: number): string {
  const filled = total ? Math.round((done / total) * 40) : 0
  return `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="4" viewBox="0 0 40 4"><rect width="40" height="4" rx="2" fill="currentColor" opacity="0.18"/><rect width="${filled}" height="4" rx="2" fill="currentColor" opacity="0.6"/></svg>`
}

function bar(done: number, total: number, width: number): string {
  const filled = total ? Math.round((done / total) * width) : 0
  return '●'.repeat(filled) + '○'.repeat(width - filled)
}
const WRITE_TOOLS = new Set(['Write', 'Edit', 'NotebookEdit'])

let ctx: Ctx | null = null

async function context($: $): Promise<Ctx | null> {
  if (ctx) return ctx
  const home = await $.env.get('HOME')
  if (!home) return null
  const text = await $.fs.read(`${home}/.config/xg-knowledge-wiki/config.yaml`).catch(() => '')
  ctx = { home, cwd: await $.session.cwd(), config: parseConfig(String(text), home) }
  return ctx
}

async function loadCard($: $, c: Ctx, dir: string): Promise<HudCard | null> {
  const [project, name] = dir.slice(c.config.devRoot.length + 1).split('/') as [string, string]
  const text = await $.fs.read(`${dir}/design.md`).catch(() => null)
  if (text === null) {
    const requirement = await $.fs.read(`${dir}/requirement.md`).catch(() => null)
    if (requirement === null) return null
    const legacy = frontmatter(String(requirement))
    return { project, dir, id: name.slice(0, 3), title: name.slice(4), status: legacy.status || 'legacy', summary: '', reqs: [] }
  }
  return { project, dir, ...parseDesign(String(text)) }
}

// The workflow records the session's card in a pointer file (xg-dev-workflow tools/active-card.py); only read it here.
async function activeCardDir($: $, c: Ctx): Promise<string | null> {
  const session = await $.session.id().catch(() => '')
  if (!session) return null
  const card = parsePointer(String(await $.fs.read(`${c.home}/.config/xg-knowledge-wiki/active-card/${session}`).catch(() => '')))
  return card ? `${c.config.devRoot}/${card}` : null
}

async function refreshCard($: $): Promise<void> {
  const c = await context($)
  if (!c) return
  const dir = await activeCardDir($, c)
  const slot: HudCardSlot = { project: projectOf(c.cwd, c.config), card: dir ? await loadCard($, c, dir) : null }
  await update($, card, () => slot)
}

// KB: backlog via kb-backlog.py; session activity from tool calls plus a file diff against the start snapshot.
async function kbFiles($: $, root: string): Promise<{ name: string; mtimeMs: number }[]> {
  const files: { name: string; mtimeMs: number }[] = []
  for (const layer of ['raw', 'wiki']) {
    const projects = await $.fs.list(`${root}/${layer}`).catch(() => [])
    for (const project of projects) {
      if (project.kind !== 'dir') continue
      const entries = await $.fs.list(`${root}/${layer}/${project.name}`).catch(() => [])
      for (const f of entries) {
        if (f.kind === 'file' && f.name.endsWith('.md')) files.push({ name: `${layer}/${project.name}/${f.name}`, mtimeMs: f.mtimeMs })
      }
    }
  }
  return files
}

async function snapshotKb($: $): Promise<void> {
  const c = await context($)
  if (!c || (await read($, kbStart)) !== null) return
  const start: HudKbStart = { at: await $.clock.now(), names: (await kbFiles($, c.config.root)).map(f => f.name) }
  await update($, kbStart, () => start)
}

// A command can name a KB path it never opens (a shell variable, a glob); count only files that exist.
async function existing($: $, root: string, paths: string[]): Promise<string[]> {
  const found: string[] = []
  for (const path of paths) if (await $.fs.exists(`${root}/${path}`).catch(() => false)) found.push(path)
  return found
}

async function refreshKb($: $): Promise<void> {
  const c = await context($)
  if (!c) return
  const script = `${c.home}/.claude/skills/xg-knowledge-lite/tools/kb-backlog.py`
  const backlog = await $.process.run(['python3', script, '--all'], { timeoutMs: 20000 }).catch(() => null)
  const start = await read($, kbStart)
  const files = await kbFiles($, c.config.root)
  const known = new Set(start?.names ?? files.map(f => f.name))
  const since = start?.at ?? Infinity
  // A changed file counts as this session's write only when one of its tool calls named it or its folder;
  // other sessions writing the KB meanwhile stay out.
  const touched = (await read($, kbTouched)).filter(path => path.split('/').length >= 2)
  const isOurs = (name: string) => touched.some(path => name === path || name.startsWith(path + '/'))
  const view: HudKb = {
    project: projectOf(c.cwd, c.config),
    rows: parseBacklog(backlog?.stdout ?? ''),
    reads: await existing($, c.config.root, (await read($, kbReads)).filter(path => path.endsWith('.md'))),
    added: files.filter(f => !known.has(f.name) && isOurs(f.name)).map(f => f.name),
    updated: files.filter(f => known.has(f.name) && f.mtimeMs > since && isOurs(f.name)).map(f => f.name),
  }
  await update($, kb, () => view)
}

function refreshAll($: $): void {
  void refreshCard($)
  void refreshKb($)
}

// Todo: text queued to send to this session later, kept in the viewer's todo files through the workflow's todo.py.
// The band lists the current project's open todos plus the ones this session added, synced from the files; the
// list and this session's refs live in $.state (hot reloads) and $.store (a resume).
const SYNC_MS = 60_000

async function todoKey($: $): Promise<string> {
  return `todos:${await $.session.id()}`
}

async function sessionRefsKey($: $): Promise<string> {
  return `todo-session:${await $.session.id()}`
}

async function setSessionRefs($: $, fn: (refs: string[]) => string[]): Promise<void> {
  const refs = await update($, todoSessionRefs, fn)
  await $.store.set(await sessionRefsKey($), refs)
}

function isTagged(item: HudTodo, project: string): boolean {
  return new RegExp(`(^|\\s)[@#]${project.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\s|$)`).test(item.key)
}

// Identity is file + created stamp + first-line key, compared whole; the hash only names drawn elements.
function todoRef(item: HudTodo): string {
  return `${item.file}\n${item.created}\n${item.key}`
}

export function todoId(item: HudTodo): string {
  let h = 5381
  for (const ch of todoRef(item)) h = ((h * 33) ^ ch.codePointAt(0)!) >>> 0
  return h.toString(36)
}

function withoutFirst(list: HudTodo[], item: HudTodo): HudTodo[] {
  const at = list.findIndex(one => todoRef(one) === todoRef(item))
  return at < 0 ? list : [...list.slice(0, at), ...list.slice(at + 1)]
}

async function changeTodos($: $, fn: (list: HudTodo[]) => HudTodo[]): Promise<HudTodo[]> {
  const list = await update($, todos, fn)
  const key = await todoKey($)
  if (list.length === 0) await $.store.delete(key)
  else await $.store.set(key, list)
  return list
}

// todo.py prints one JSON value, or exits non-zero with one line on stderr: that line is the error's message.
async function runTodo($: $, args: string[], stdin?: string): Promise<unknown> {
  const c = await context($)
  if (!c) throw new Error('no HOME')
  const script = `${c.home}/.claude/skills/xg-dev-workflow/tools/todo.py`
  const ran = await $.process.run(['python3', script, ...args], { stdin, timeoutMs: 15000 })
  if (ran.isStdoutTruncated) throw new Error('todo.py output was cut off; check the todo file before retrying')
  if (ran.exitCode !== 0) throw new Error((ran.stderr.trim().split('\n').pop() || `todo.py exited ${ran.exitCode}`).replace(/^todo\.py: /, ''))
  return JSON.parse(ran.stdout)
}

function reason(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

async function addTodo($: $, text: string): Promise<number> {
  const c = await context($)
  const project = c ? projectOf(c.cwd, c.config) : null
  const item = (await runTodo($, ['add', ...(project ? ['--project', project] : [])], text)) as HudTodo
  await setSessionRefs($, refs => [...refs, todoRef(item)])
  return (await changeTodos($, list => [...list, item])).length
}

async function stashPrompt($: $): Promise<void> {
  const { text } = await $.prompt.read()
  if (!text.trim()) {
    $.ui.toast('Prompt is empty, nothing to stash')
    return
  }
  try {
    const count = await addTodo($, text)
    await $.prompt.fill({ text: '', mode: 'replace' })
    $.ui.toast(`Stashed as todo (${count})`)
  } catch (err) {
    $.ui.toast(`Todo not saved, prompt kept: ${reason(err)}`)
  }
}

async function addTyped($: $, text: string): Promise<void> {
  try {
    $.ui.toast(`Added todo (${await addTodo($, text)})`)
  } catch (err) {
    $.ui.toast(`Todo not saved (${reason(err)}): ${text}`)
  }
}

// Ticks the item in its file; it leaves the working set unless the script itself failed.
async function finishTodo($: $, item: HudTodo): Promise<boolean> {
  let res: { ok: boolean; reason?: string }
  try {
    res = (await runTodo($, ['done', '--file', item.file, '--created', item.created, '--key', item.key])) as typeof res
  } catch (err) {
    $.ui.toast(`Todo kept, could not mark it done: ${reason(err)}`)
    return false
  }
  if (!res.ok) $.ui.toast(`Todo not found in ${item.file} (edited or ticked there); removed from the list`)
  await changeTodos($, list => withoutFirst(list, item))
  return true
}

// Copies the todo into the prompt only; marking it done is the done button's job.
async function takeTodo($: $, item: HudTodo): Promise<void> {
  const { text: draft } = await $.prompt.read()
  const filled = draft.trim()
    ? await $.prompt.fill({ text: `\n${item.text}`, mode: 'append' })
    : await $.prompt.fill({ text: item.text, mode: 'replace' })
  if (!filled.isFilled) $.ui.toast('Prompt is not writable now')
}

// Replaces the list with what the files hold now. Items added while the list ran are kept, and a failed list changes nothing.
async function syncTodos($: $): Promise<void> {
  const before = new Set((await read($, todos)).map(todoRef))
  let open: HudTodo[]
  try {
    open = (await runTodo($, ['list', '--open'])) as HudTodo[]
  } catch {
    return
  }
  const c = await context($)
  const project = c ? projectOf(c.cwd, c.config) : null
  const own = new Set(await read($, todoSessionRefs))
  const synced = open.filter(item => own.has(todoRef(item)) || (project !== null && isTagged(item, project)))
  const seen = new Set(synced.map(todoRef))
  await changeTodos($, list => [...synced, ...list.filter(one => !before.has(todoRef(one)) && !seen.has(todoRef(one)))])
}

// At session start: a resumed session's working set comes back from the store, and items kept before the todo files
// backed the list ({ id, text }) are written to the inbox once. Those wait under their own key until each is written,
// so neither a failure nor an interruption mid-way drops one.
async function restoreTodos($: $): Promise<void> {
  const unsavedKey = `todos-unsaved:${await $.session.id()}`
  const inState = (await read($, todos)) as unknown[]
  const stored = inState.length ? inState : (await $.store.get(await todoKey($))) ?? []
  const waiting = (await $.store.get(unsavedKey)) ?? []
  const all = [...(Array.isArray(stored) ? stored : []), ...(Array.isArray(waiting) ? waiting : [])]
  const isOld = (one: unknown) => typeof one === 'object' && one !== null && !('file' in one) && typeof (one as { text?: unknown }).text === 'string'
  const left = all.filter(isOld) as { text: string }[]
  const kept = all.filter(one => !isOld(one)) as HudTodo[]
  await update($, todos, () => kept)
  const refs = (await $.store.get(await sessionRefsKey($))) as string[] | undefined
  await update($, todoSessionRefs, () => (Array.isArray(refs) ? refs : kept.map(todoRef)))
  if (left.length === 0) return
  await $.store.set(unsavedKey, left)
  await changeTodos($, list => list)
  while (left.length) {
    try {
      await addTodo($, left[0]!.text)
    } catch {
      $.ui.toast(`${left.length} earlier todos could not be written to the inbox; retried when this session starts again`)
      return
    }
    left.shift()
    if (left.length) await $.store.set(unsavedKey, left)
    else await $.store.delete(unsavedKey)
  }
}

// Todo text is wrapped here rather than by the surface, so each drawn row is known and gets its own connector.
function wrapLine(line: string, width: number): string[] {
  const rows: string[] = []
  let rest = line
  while (cells(rest) > width) {
    let cut = ''
    for (const ch of rest) {
      if (cells(cut + ch) > width) break
      cut += ch
    }
    const space = cut.lastIndexOf(' ')
    if (rest[cut.length] !== ' ' && space > 0) cut = cut.slice(0, space)
    rows.push(cut)
    rest = rest.slice(cut.length).replace(/^ /, '')
  }
  rows.push(rest)
  return rows
}

export function todoLines(text: string, width: number, maxRows = 3): string[] {
  const rows = text.split('\n').flatMap(line => wrapLine(line, width))
  if (rows.length <= maxRows) return rows
  const kept = rows.slice(0, maxRows)
  kept[maxRows - 1] = clip(`${kept[maxRows - 1]} …`, width)
  return kept
}

// Times: the last typed prompt and the last reply, mirrored to $.store so a resumed session keeps them; while the
// segment is open a ticker moves msgNow so its "ago" text stays current.
const TICK_MS = 30_000

export function clockText(ms: number): string {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function agoText(ms: number): string {
  const minutes = Math.floor(ms / 60_000)
  if (minutes < 1) return '<1m ago'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return hours < 24 ? `${hours}h ${minutes % 60}m ago` : `${Math.floor(hours / 24)}d ago`
}

async function timesKey($: $): Promise<string> {
  return `times:${await $.session.id()}`
}

async function markTime($: $, which: keyof HudTimes): Promise<void> {
  const now = await $.clock.now()
  const next = await update($, times, value => ({ ...value, [which]: now }))
  await update($, msgNow, () => now)
  await $.store.set(await timesKey($), next)
}

async function restoreTimes($: $): Promise<void> {
  const saved = (await $.store.get(await timesKey($))) as Partial<HudTimes> | undefined
  if (!saved || (await read($, times)).message !== null) return
  await update($, times, () => ({ message: saved.message ?? null, reply: saved.reply ?? null }))
}

async function tickTimes($: $): Promise<void> {
  if (await read($, isMsgOpen)) {
    const now = await $.clock.now()
    await update($, msgNow, () => now)
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    $.ui.status(undefined)
    await $.command.register({ name: 'todo', description: 'Queue text as a todo for this session; no argument toggles the todo list', argumentHint: '[text]', immediate: true })
    void restoreTodos($).then(() => syncTodos($))
    $.clock.every(SYNC_MS, () => void syncTodos($))
    await restoreTimes($)
    $.clock.every(TICK_MS, () => void tickTimes($))
    void snapshotKb($).then(() => refreshAll($))
    return started
  })

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId === undefined) {
      refreshAll($)
      void syncTodos($)
      await markTime($, 'reply')
    }
    return done
  })

  on('prompt.submit', async ($, e, next) => {
    const submitted = await next(e)
    if (e.origin.kind === 'composer' && !submitted.drop) await markTime($, 'message')
    return submitted
  })

  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    const c = await context($)
    if (!c) return ran

    const blob = JSON.stringify(e)
    const paths = kbPathsIn(blob, c.config.root, c.home)
    if (paths.length) {
      await update($, kbTouched, all => [...new Set([...all, ...paths])])
      if (!WRITE_TOOLS.has(String(e.tool))) await update($, kbReads, all => [...new Set([...all, ...paths])])
      void refreshKb($)
    }

    if (blob.includes('active-card.py')) void refreshCard($)
    return ran
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'todo' }, async ($, e) => {
    const text = e.args.trim()
    if (!text) await update($, isTodoOpen, v => !v)
    else await addTyped($, text)
    return {}
  })

  // One always-on line above the prompt; its KB and card segments each toggle their detail lines.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const view = await read($, kb)
    const slot = await read($, card)
    const queue = await read($, todos)
    const todoOpen = await read($, isTodoOpen)
    const at = todoOpen ? Math.min(await read($, todoAt), Math.max(0, queue.length - 1)) : 0
    const { Box, Button, Text } = $.ui.resolve(e)
    const isDesktop = e.surface === 'desktop'
    const kbOpen = await read($, isKbOpen)
    const cardOpen = await read($, isCardOpen)
    const doneShown = await read($, isDoneShown)
    const page = await read($, cardPage)
    const pageKb = await read($, kbPage)

    const here = view?.rows.find(r => r.project === view.project)
    const total = view?.rows.reduce((sum, r) => sum + r.uncompiled, 0) ?? 0
    const c = slot?.card ?? null
    const verified = c ? c.reqs.filter(r => DONE_WORDS.has(r.word)).length : 0
    const pending = here ? here.uncompiled : total
    const written = view ? view.added.length + view.updated.length : 0

    const room = (e.props.bodyColumns ?? 120) - 2
    const isNarrow = room < NARROW

    type Segment = { key: string; text: string; onPress?: () => unknown; rank: number }
    const all: Segment[] = []
    const todoText = `todo ${queue.length}${todoOpen ? ' ▾' : ''}`
    const stamps = await read($, times)
    const msgOpen = stamps.message !== null && (await read($, isMsgOpen))
    const msgText = stamps.message === null ? null : `${clockText(stamps.message)}${msgOpen ? ' ▾' : ''}`
    const msgCost = msgText ? cells(msgText) + SEP_CELLS : 0
    if (view !== null) {
      const counts = [pending && `${pending}c`, view.reads.length && `${view.reads.length}r`, written && `${written}w`].filter(Boolean)
      const text = `KB ${counts.length ? counts.join(' ') : '✓'}${kbOpen ? ' ▾' : ''}`
      all.push({ key: 'kb', text, onPress: () => update($, isKbOpen, v => !v), rank: 0 })
    }
    if (c !== null) {
      const dropped = c.reqs.filter(r => DROPPED_WORDS.has(r.word)).length
      const isAllDone = verified > 0 && verified + dropped === c.reqs.length
      const progress = c.reqs.length === 0 ? c.status : isAllDone ? '✓' : isNarrow ? `${verified}/${c.reqs.length}` : `${bar(verified, c.reqs.length, 8)} ${verified}/${c.reqs.length}`
      const tail = ` ${progress}${cardOpen ? ' ▾' : ''}`
      const kbCost = all.length ? cells(all[0]!.text) + SEP_CELLS : 0
      const titleRoom = room - kbCost - cells(`${c.id} `) - cells(tail) - cells(todoText) - SEP_CELLS - msgCost
      const title = titleRoom >= 4 ? ` ${clip(c.title, titleRoom - 1)}` : ''
      all.push({ key: 'card', text: `${c.id}${title}${tail}`, onPress: () => update($, isCardOpen, v => !v), rank: 1 })
    }
    const toggleTodo = async () => {
      if (await update($, isTodoOpen, v => !v)) void syncTodos($)
    }
    all.push({ key: 'todo', text: todoText, onPress: toggleTodo, rank: 2 })
    if (msgText) {
      const toggleMsg = async () => {
        const now = await $.clock.now()
        await update($, msgNow, () => now)
        await update($, isMsgOpen, v => !v)
      }
      all.unshift({ key: 'msg', text: msgText, onPress: toggleMsg, rank: 3 })
    }

    // Narrow screens drop whole segments by rank instead of letting the row wrap mid-segment.
    const kept = new Set<string>()
    let width = 0
    for (const seg of [...all].sort((x, y) => x.rank - y.rank)) {
      const cost = cells(seg.text) + (kept.size ? SEP_CELLS : 0)
      if (width + cost > room && kept.size) continue
      kept.add(seg.key)
      width += cost
    }
    const shown = all.filter(seg => kept.has(seg.key))
    if (shown.length === 0) return next(e)

    // A detail line: a short mark (r / + / ● …) and its text; terminals join them with spaces, desktop lays them out in columns.
    type Line = { mark?: string; text: string; onPress?: () => unknown }
    const used = new Map<string, string>()
    if (view !== null && kbOpen) {
      for (const path of view.reads) used.set(path, 'r')
      for (const path of view.added) used.set(path, '+')
      for (const path of view.updated) used.set(path, used.has(path) ? 'rw' : 'w')
    }
    const kbLines: Line[] = [...used].map(([path, mark]) => ({ mark, text: path.replace(/\.md$/, '') }))
    if (kbOpen && view !== null) {
      for (const slug of here?.slugs ?? []) kbLines.push({ mark: 'c', text: `raw/${view.project}/${slug}` })
      const others = view.rows.filter(r => r.uncompiled > 0 && r.project !== view.project)
      const othersTotal = others.reduce((sum, r) => sum + r.uncompiled, 0)
      if (others.length) kbLines.push({ mark: 'c', text: isNarrow ? `others ${othersTotal}` : others.map(r => `${r.project} ${r.uncompiled}`).join(' / ') })
    }

    // Row budget, shared when both are open; a group longer than its share pages instead of being cut off.
    const paginate = (body: Line[], budget: number, at: number, onNext: () => unknown): Line[] => {
      if (body.length <= budget) return body
      const size = Math.max(1, budget - 1)
      const pages = Math.ceil(body.length / size)
      const current = at % pages
      return [...body.slice(current * size, (current + 1) * size), { mark: '…', text: `page ${current + 1}/${pages}, click for next`, onPress: onNext }]
    }
    const allRows = Math.max(0, (e.props.maxRows ?? 20) - (isDesktop ? 3 : 1))
    // Todo rows are reserved first (wrapped items from `at` on, a more row, the new/stash row); KB and card share the rest.
    const othersOpen = (kbOpen && kbLines.length > 0) || (cardOpen && c !== null)
    const todoWidth = Math.min(64, room)
    const todoTextWidth = Math.max(8, todoWidth - 14)
    const todoAvail = (othersOpen ? Math.max(3, Math.ceil(allRows / 2)) : allRows) - 2
    const todoItems: { item: HudTodo; lines: string[] }[] = []
    let todoUsed = 0
    const listed = todoOpen ? queue.slice(at) : []
    for (const item of listed) {
      const lines = todoLines(item.text, todoTextWidth)
      if (todoItems.length > 0 && todoUsed + lines.length > todoAvail) break
      todoItems.push({ item, lines })
      todoUsed += lines.length
    }
    const todoHidden = queue.length - at - todoItems.length
    const todoRows = todoOpen ? todoUsed + (todoHidden > 0 || at > 0 ? 1 : 0) + 1 : 0
    const now = Math.max(await read($, msgNow), stamps.reply ?? 0, stamps.message ?? 0)
    const msgLines: Line[] = !msgOpen || stamps.message === null ? [] : [
      { mark: '›', text: `msg ${clockText(stamps.message)} · ${agoText(now - stamps.message)}` },
      { mark: '‹', text: stamps.reply === null ? 'reply —' : `reply ${clockText(stamps.reply)} · ${agoText(now - stamps.reply)}` },
    ]
    const rows = Math.max(0, allRows - todoRows - msgLines.length)
    const cardWanted = cardOpen && c !== null
    const kbBudget = cardWanted ? Math.max(2, Math.ceil(rows / 2)) : rows
    const kbFitted = paginate(kbLines, Math.min(kbBudget, rows), pageKb, () => update($, kbPage, n => n + 1))
    const cardRows = rows - kbFitted.length

    const cardLines: Line[] = []
    if (cardWanted && c !== null && cardRows > 0) {
      const isDone = (word: string) => DONE_WORDS.has(word) || DROPPED_WORDS.has(word)
      const symbol = (word: string) => DONE_WORDS.has(word) ? '●' : DROPPED_WORDS.has(word) ? '–' : '○'
      const doneCount = c.reqs.filter(r => isDone(r.word)).length
      const listed = doneShown ? c.reqs : c.reqs.filter(r => !isDone(r.word))
      const reqLine = (r: HudReq): Line => isNarrow && !isDesktop
        ? { mark: symbol(r.word), text: `${r.n} ${r.title}` }
        : { mark: symbol(r.word), text: `Req-${r.n} ${r.word}  ${r.title}` }
      const head: Line[] = isNarrow && !isDesktop ? [] : [{ mark: '◇', text: c.status }]
      const toggle: Line[] = doneCount > 0
        ? [{ mark: doneShown ? '▴' : '▸', text: `${doneShown ? 'hide' : 'show'} done (${doneCount})`, onPress: () => update($, isDoneShown, v => !v) }]
        : []
      const body: Line[] = listed.length === 0 ? [{ mark: '✓', text: 'all done' }] : listed.map(reqLine)
      const paged = paginate(body, Math.max(1, cardRows - head.length - toggle.length), page, () => update($, cardPage, n => n + 1))
      cardLines.push(...[...head, ...paged, ...toggle].slice(0, cardRows))
    }

    const pressable = (key: string, label: string, onPress: () => unknown) =>
      <Box key={`${key}-hover`}><Button key={key} plain dimColor hover={{ underline: true }} label={label} onPress={onPress} /></Box>

    // Todo detail: a fixed-width, left-aligned list; each text wraps beside its take/done. The last row, indented to
    // the text column (the number's two cells plus the gap), holds the new field and stash.
    const todoBlock: RenderChildren[] = []
    if (todoOpen) {
      // Connectors as KB and card draw them: ┤ on each entry's first row, │ on its wrapped rows, ┘ closing the block.
      const hasTicks = !isDesktop && !isNarrow
      const tick = (glyphs: string[]) => hasTicks ? <Box flexDirection="column">{glyphs.map(g => <Text dimColor>{g}</Text>)}</Box> : null
      todoItems.forEach(({ item, lines }, i) => {
        const id = `${todoId(item)}-${at + i}`
        todoBlock.push(
          <Box key={`todo-${id}`} flexDirection="row" gap={1} width={todoWidth}>
            <Box width={2}><Text dimColor>{String(at + i + 1)}</Text></Box>
            <Box width={todoTextWidth} flexDirection="column">{lines.map(line => <Text>{line}</Text>)}</Box>
            {pressable(`todo-take-${id}`, 'take', () => takeTodo($, item))}
            {pressable(`todo-done-${id}`, 'done', () => finishTodo($, item))}
            <Box flexGrow={1} />
            {tick(['┤', ...lines.slice(1).map(() => '│')])}
          </Box>,
        )
      })
      if (todoHidden > 0) {
        const nextAt = at + todoItems.length
        todoBlock.push(
          <Box key="todo-more" flexDirection="row" gap={1} width={todoWidth} paddingLeft={3}>
            <Text dimColor>{`… ${todoHidden} more`}</Text>
            {pressable('todo-next', 'next', () => update($, todoAt, () => (nextAt >= queue.length ? 0 : nextAt)))}
            <Box flexGrow={1} />
            {tick(['┤'])}
          </Box>,
        )
      } else if (at > 0) {
        todoBlock.push(
          <Box key="todo-more" flexDirection="row" gap={1} width={todoWidth} paddingLeft={3}>
            {pressable('todo-next', 'first', () => update($, todoAt, () => 0))}
            <Box flexGrow={1} />
            {tick(['┤'])}
          </Box>,
        )
      }
      // A click on a band Button does not hand the band the keyboard, so new is the field itself: one click types.
      const field = e.surface === 'mobile' ? null : (() => {
        const { Input } = $.ui.resolve(e)
        return (
          <Box key="todo-new-box" flexShrink={1}>
            <Input key="todo-new" placeholder="new" value="" submitLabel="add" onSubmit={value => { if (value.trim()) void addTyped($, value) }} />
          </Box>
        )
      })()
      todoBlock.push(
        <Box key="todo-actions" flexDirection="row" gap={1} width={todoWidth} paddingLeft={3}>
          {field}
          {pressable('todo-stash', 'stash', () => stashPrompt($))}
          <Box flexGrow={1} />
          {tick(['┘'])}
        </Box>,
      )
    }

    if (e.surface === 'desktop') {
      // Desktop draws in a proportional font: real flex layout instead of padded text and box-drawing glyphs.
      const { Svg } = $.ui.resolve(e)
      const segs = shown.map(seg => {
        if (seg.key === 'card' && c !== null && c.reqs.length > 0 && !seg.text.includes('✓')) {
          const done = c.reqs.filter(r => DONE_WORDS.has(r.word)).length
          return (
            <Box key="card-seg" flexDirection="row" alignItems="center" gap={1}>
              {pressable('card', seg.text.replace(/ (●|○)+ \d+\/\d+/, ''), seg.onPress!)}
              <Svg alt={`${done}/${c.reqs.length}`} width={40} height={4} source={progressSvg(done, c.reqs.length)} />
              <Text dimColor>{`${done}/${c.reqs.length}`}</Text>
            </Box>
          )
        }
        return seg.onPress ? pressable(seg.key, seg.text, seg.onPress) : <Text dimColor wrap="truncate-end">{seg.text}</Text>
      })
      const groups = [kbFitted, cardLines, msgLines].filter(lines => lines.length > 0)
      const below = await next(e)
      return (
        <Box flexDirection="column">
          <Box flexDirection="column" alignItems="flex-end">
            <Box flexDirection="row" flexWrap="nowrap" gap={2} paddingRight={1}>{segs}</Box>
            {(groups.length > 0 || todoBlock.length > 0) && (
              <Box flexDirection="column" borderStyle="round" borderDimColor paddingX={1} rowGap={1}>
                {groups.map((lines, g) => (
                  <Box key={`group-${g}`} flexDirection="column">
                    {lines.map((line, i) => (
                      <Box key={`row-${g}-${i}`} flexDirection="row" gap={1}>
                        <Box width={2}><Text dimColor>{line.mark ?? ''}</Text></Box>
                        {line.onPress ? pressable(`press-${g}-${i}`, line.text, line.onPress) : <Text dimColor wrap="truncate-end">{line.text}</Text>}
                      </Box>
                    ))}
                  </Box>
                ))}
                {todoBlock.length > 0 && <Box key="group-todo" flexDirection="column">{todoBlock}</Box>}
              </Box>
            )}
          </Box>
          {below}
        </Box>
      )
    }

    const segments: RenderChildren[] = shown.map(seg => seg.onPress
      ? pressable(seg.key, seg.text, seg.onPress)
      : <Text dimColor wrap="truncate-end">{seg.text}</Text>)

    // Main line and details each align to the right edge; expanding never moves the main line.
    const flat = (line: Line) => line.mark !== undefined ? `${line.mark.padEnd(2)} ${line.text}` : line.text
    const groups = [kbFitted, cardLines, msgLines].map(lines => lines.map(line => ({ ...line, text: clip(flat(line), room - 2) })))
    const textWidth = Math.max(0, ...groups.flat().map(line => cells(line.text)))
    const details = groups.flatMap(lines => {
      const texts = branch(lines.map(line => line.text), isNarrow, textWidth)
      return lines.map((line, i) => ({ ...line, text: texts[i]! }))
    })

    // Other plugins' bands sit beneath this one, so their rows show too.
    const below = await next(e)
    return (
      <Box flexDirection="column">
        <Box flexDirection="column" alignItems="flex-end">
          <Box flexDirection="row" flexWrap="nowrap">
            {segments.flatMap((seg, i) => i === 0 ? [seg] : [<Text dimColor>{SEP}</Text>, seg])}
          </Box>
          {details.length > 0 && (
            <Box flexDirection="column">
              {details.map((line, i) => line.onPress
                ? pressable(`press-${i}`, line.text, line.onPress)
                : <Text dimColor wrap="truncate-end">{line.text}</Text>)}
            </Box>
          )}
          {todoBlock.length > 0 && <Box flexDirection="column">{todoBlock}</Box>}
        </Box>
        {below}
      </Box>
    )
  })
}
