import { describe, expect, mock, test } from 'claude-code/testing'
import type { Engine, MockClock } from 'claude-code/testing'
import type { On } from 'claude-code'

import type { HudTodo } from '../types'
import { todoLines } from './register'

const BAND = { component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 100 } as never } as const

type Row = HudTodo & { done: boolean }
type Fake = { draft: string; rows: Row[]; fail: string | null; listFail: boolean; clock: MockClock }

// A stand-in for todo.py: the same argv and the same one-JSON-value-or-stderr-line contract, over an in-memory file.
function world(on: On, draft = '', store: Record<string, unknown> = {}): Fake {
  const fake: Fake = { draft, rows: [], fail: null, listFail: false, clock: mock.clock(on) }
  let minute = 0
  mock.store(on, store)
  mock.env(on, { HOME: '/home/t' })
  on('session.id', () => ({ value: 's1' }))
  on('session.cwd', () => ({ value: '/work' }))
  on('fs.read', () => ({ deny: 'absent' }) as never)
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return <Box />
  })
  on('prompt.read', () => ({ value: { text: fake.draft, cursor: fake.draft.length } }))
  on('prompt.fill', (_$, e) => {
    fake.draft = e.mode === 'append' ? fake.draft + e.text : e.text
    return { isFilled: true, text: fake.draft, cursor: fake.draft.length }
  })
  on('process.run', (_$, e) => {
    const call = e as unknown as { argv: string[]; init?: { stdin?: string } }
    const argv = call.argv.slice(2)
    const stdin = call.init?.stdin ?? ''
    const out = (value: unknown) => ({ value: { exitCode: 0, stdout: JSON.stringify(value), stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never
    const err = (line: string) => ({ value: { exitCode: 1, stdout: '', stderr: `todo.py: ${line}\n`, isStdoutTruncated: false, isStderrTruncated: false } }) as never
    if (fake.fail) return err(fake.fail)
    const arg = (name: string) => argv[argv.indexOf(name) + 1] ?? ''
    const strip = ({ done: _, ...item }: Row): HudTodo => item
    if (argv[0] === 'add') {
      minute += 1
      const row: Row = { file: 'inbox.md', created: `2026-10-13 09:${String(minute).padStart(2, '0')}`, key: stdin.split('\n')[0]!, text: stdin, project: null, done: false }
      fake.rows.push(row)
      return out(strip(row))
    }
    if (argv[0] === 'list') return fake.listFail ? err('cannot read') : out(fake.rows.filter(r => !r.done).map(strip))
    if (argv[0] === 'done') {
      const row = fake.rows.find(r => !r.done && r.file === arg('--file') && r.created === arg('--created') && r.key === arg('--key'))
      if (!row) return out({ ok: false, reason: 'not-found' })
      row.done = true
      return out({ ok: true, line: 0 })
    }
    return err('unknown')
  })
  return fake
}

const count = (n: number) => ({ key: 'todo', text: new RegExp(`^todo ${n}( ▾)?$`) })

describe('todoLines', () => {
  test('keeps short text whole, one row per line', () => {
    expect(todoLines('one\ntwo', 10)).toEqual(['one', 'two'])
  })
  test('wraps at a space when there is one, else mid-word', () => {
    expect(todoLines('alpha beta gamma', 10)).toEqual(['alpha beta', 'gamma'])
    expect(todoLines('a'.repeat(15), 10)).toEqual(['a'.repeat(10), 'a'.repeat(5)])
  })
  test('cuts past the row cap with an ellipsis', () => {
    const cut = todoLines('a'.repeat(50), 10)
    expect(cut.length).toBe(3)
    expect(cut[2]!.endsWith('…')).toBe(true)
    expect(todoLines('1\n2\n3\n4', 10)).toEqual(['1', '2', '3 …'])
  })
})

describe('todo segment', () => {
  for (const surface of ['terminal', 'desktop'] as const) {
    test(`shows the count with nothing else in the band (${surface})`, async ($, on) => {
      world(on)
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      expect(await ui.find(count(0))).toBeDefined()
      expect(await ui.find({ key: 'todo-new' })).toBeUndefined()
    })

    test(`new writes through the script; take fills the prompt and marks it done (${surface})`, async ($, on) => {
      const fake = world(on)
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      await ui.press({ key: 'todo' })
      await ui.input({ key: 'todo-new', text: 'review the diff' })
      expect(fake.rows.map(r => r.text)).toEqual(['review the diff'])
      expect(await ui.find(count(1))).toBeDefined()
      const take = await ui.find({ type: 'Button', text: 'take' })
      await ui.press({ key: take!.key! })
      expect(fake.draft).toBe('review the diff')
      expect(fake.rows[0]!.done).toBe(true)
      expect(await ui.find(count(0))).toBeDefined()
    })

    test(`take appends on a new line to a non-empty draft (${surface})`, async ($, on) => {
      const fake = world(on)
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      await ui.press({ key: 'todo' })
      await ui.input({ key: 'todo-new', text: 'B' })
      fake.draft = 'A'
      const take = await ui.find({ type: 'Button', text: 'take' })
      await ui.press({ key: take!.key! })
      expect(fake.draft).toBe('A\nB')
    })

    test(`stash moves the draft in and clears it; an empty draft is ignored (${surface})`, async ($, on) => {
      const fake = world(on, 'run the tests next\nand then lint')
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      await ui.press({ key: 'todo' })
      await ui.press({ key: 'todo-stash' })
      expect(fake.draft).toBe('')
      expect(fake.rows[0]!.text).toBe('run the tests next\nand then lint')
      await ui.press({ key: 'todo-stash' })
      expect(fake.rows.length).toBe(1)
    })

    test(`del marks done; overflow shows a more row (${surface})`, async ($, on) => {
      const fake = world(on)
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND, props: { hasSurvey: false, isWorking: false, maxRows: 5, bodyColumns: 100 } as never })
      await ui.press({ key: 'todo' })
      for (const text of ['a', 'b', 'c', 'd']) await ui.input({ key: 'todo-new', text })
      expect(await ui.find({ type: 'Text', text: /more/ })).toBeDefined()
      const del = await ui.find({ type: 'Button', text: 'del' })
      await ui.press({ key: del!.key! })
      expect(fake.rows.filter(r => r.done).length).toBe(1)
      expect(await ui.find(count(3))).toBeDefined()
    })
  }
})

describe('todo failures', () => {
  test('a failed stash keeps the prompt and adds nothing', async ($, on) => {
    const fake = world(on, 'keep me')
    fake.fail = 'todo dir not writable'
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    await ui.press({ key: 'todo' })
    await ui.press({ key: 'todo-stash' })
    expect(fake.draft).toBe('keep me')
    expect(await ui.find(count(0))).toBeDefined()
  })

  test('a failed done keeps the item; a not-found one leaves', async ($, on) => {
    const fake = world(on)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    await ui.press({ key: 'todo' })
    await ui.input({ key: 'todo-new', text: 'x' })
    fake.fail = 'locked'
    await ui.press({ key: (await ui.find({ type: 'Button', text: 'del' }))!.key! })
    expect(await ui.find(count(1))).toBeDefined()
    fake.fail = null
    fake.rows[0]!.done = true
    await ui.press({ key: (await ui.find({ type: 'Button', text: 'del' }))!.key! })
    expect(await ui.find(count(0))).toBeDefined()
  })

  test('/todo with text that cannot be saved adds nothing', async ($, on) => {
    const fake = world(on)
    fake.fail = 'no todo.py'
    const out = await $.command.run({ command: 'todo', args: 'ask about coverage' } as never)
    expect(out.text).toBeUndefined()
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect(await ui.find(count(0))).toBeDefined()
  })
})

describe('todo refresh', () => {
  test('opening the list drops items the files no longer hold open; a failed list drops nothing', async ($, on) => {
    const fake = world(on)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    await ui.press({ key: 'todo' })
    await ui.input({ key: 'todo-new', text: 'a' })
    await ui.input({ key: 'todo-new', text: 'b' })
    await ui.press({ key: 'todo' })
    fake.rows[0]!.done = true
    fake.listFail = true
    await ui.press({ key: 'todo' })
    expect(await ui.find(count(2))).toBeDefined()
    await ui.press({ key: 'todo' })
    fake.listFail = false
    await ui.press({ key: 'todo' })
    expect(await ui.find(count(1))).toBeDefined()
  })
})

describe('todo load', () => {
  test('load lists other open todos, add brings one in, load again returns', async ($, on) => {
    const fake = world(on)
    fake.rows.push({ file: 'work.md', created: '', key: 'from viewer', text: 'from viewer', project: null, done: false })
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    await ui.press({ key: 'todo' })
    await ui.input({ key: 'todo-new', text: 'mine' })
    await ui.press({ key: 'todo-load' })
    const adds = await ui.findAll({ type: 'Button', text: 'add' })
    expect(adds.length).toBe(1)
    await ui.press({ key: adds[0]!.key! })
    expect(await ui.find({ type: 'Text', text: 'no other open todos' })).toBeDefined()
    await ui.press({ key: 'todo-load' })
    expect(await ui.find(count(2))).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'from viewer' })).toBeDefined()
  })
})

function sessionHooks(on: On): void {
  on('command.register', (_$, e) => ({ value: { command: (e as unknown as { name: string }).name } }) as never)
  on('fs.list', () => ({ value: [] }) as never)
  on('session.start', () => ({ cwd: '/work' }) as never)
}

// session.start leaves the todo restore running unawaited (it calls the script); settle lets it finish.
async function startSession($: Engine, fake: Fake): Promise<void> {
  await $.session.start({ cwd: '/work', surface: 'terminal', isInteractive: true } as never)
  await fake.clock.settle()
}

describe('todo restore and migration', () => {
  test('items kept before the inbox are written once at session start', async ($, on) => {
    const fake = world(on, '', { 'todos:s1': [{ id: 'old-1', text: 'from before' }] })
    sessionHooks(on)
    await startSession($, fake)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect(fake.rows.map(r => r.text)).toContain('from before')
    expect(await ui.find(count(1))).toBeDefined()
  })

  test('a resumed session gets its working set back from the store', async ($, on) => {
    const saved = { file: 'inbox.md', created: '2026-10-13 08:00', key: 'kept', text: 'kept', project: null }
    const fake = world(on, '', { 'todos:s1': [saved] })
    sessionHooks(on)
    fake.rows.push({ ...saved, done: false })
    await startSession($, fake)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect(await ui.find(count(1))).toBeDefined()
  })

  test('old items that cannot be written wait for the next start instead of being dropped', async ($, on) => {
    const fake = world(on, '', { 'todos:s1': [{ id: 'old-1', text: 'a' }, { id: 'old-2', text: 'b' }] })
    sessionHooks(on)
    fake.fail = 'no todo.py'
    await startSession($, fake)
    expect(fake.rows.length).toBe(0)
    fake.fail = null
    await startSession($, fake)
    expect(fake.rows.map(r => r.text)).toEqual(['a', 'b'])
    await startSession($, fake)
    expect(fake.rows.map(r => r.text)).toEqual(['a', 'b'])
  })
})

describe('todo identity', () => {
  test('of two identical items, del ticks and removes one', async ($, on) => {
    const twin = { file: 'inbox.md', created: '2026-10-13 08:00', key: 'same', text: 'same', project: null }
    const fake = world(on, '', { 'todos:s1': [twin, twin] })
    sessionHooks(on)
    fake.rows.push({ ...twin, done: false }, { ...twin, done: false })
    await startSession($, fake)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    await ui.press({ key: 'todo' })
    await ui.press({ key: (await ui.find({ type: 'Button', text: 'del' }))!.key! })
    expect(fake.rows.filter(r => r.done).length).toBe(1)
    expect(await ui.find(count(1))).toBeDefined()
  })
})

describe('/todo', () => {
  test('with text queues it and prints nothing', async ($, on) => {
    const fake = world(on)
    const out = await $.command.run({ command: 'todo', args: 'ask about coverage' } as never)
    expect(out.text).toBeUndefined()
    expect(fake.rows.map(r => r.text)).toEqual(['ask about coverage'])
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect(await ui.find(count(1))).toBeDefined()
  })
})
