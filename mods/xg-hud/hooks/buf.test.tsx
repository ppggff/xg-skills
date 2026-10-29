import { describe, expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const BAND = { component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 100 } as never } as const

type Fake = { draft: string; store: Record<string, unknown>; storedAtFill: unknown[] }

// The store is the test's own map, so a test can read what the band wrote and when.
function world(on: On, draft = '', store: Record<string, unknown> = {}, state: Record<string, unknown> = {}): Fake {
  const fake: Fake = { draft, store: { ...store }, storedAtFill: [] }
  mock.clock(on)
  on('store.get', (_$, e) => ({ value: fake.store[e.key] }) as never)
  on('store.set', (_$, e) => {
    fake.store[e.key] = e.value
    return { value: undefined } as never
  })
  on('store.delete', (_$, e) => {
    delete fake.store[e.key]
    return { value: undefined } as never
  })
  mock.env(on, { HOME: '/home/t' })
  on('session.id', () => ({ value: 's1' }))
  on('session.cwd', () => ({ value: '/work' }))
  on('fs.read', () => ({ deny: 'absent' }) as never)
  on('fs.list', () => ({ value: [] }) as never)
  on('process.run', () => ({ value: { exitCode: 0, stdout: '[]', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never)
  on('command.register', (_$, e) => ({ value: { command: (e as unknown as { name: string }).name } }) as never)
  on('session.start', () => ({ cwd: '/work' }) as never)
  on('state.get', (_$, e, next) => {
    const key = (e as { plugin: string; key: string }).key
    return key in state ? ({ value: { value: state[key], version: 1 } } as never) : next(e)
  })
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return <Box />
  })
  on('prompt.read', () => ({ value: { text: fake.draft, cursor: fake.draft.length } }))
  on('prompt.fill', (_$, e) => {
    fake.storedAtFill.push(fake.store['buf:s1'])
    fake.draft = e.mode === 'append' ? fake.draft + e.text : e.text
    return { isFilled: true, text: fake.draft, cursor: fake.draft.length }
  })
  return fake
}

const start = ($: Engine) => $.session.start({ cwd: '/work', surface: 'terminal', isInteractive: true } as never)
const seg = async (ui: { find: (q: object) => Promise<{ text?: string } | undefined> }) => (await ui.find({ key: 'buf' }))?.text

describe('buf segment', () => {
  for (const surface of ['terminal', 'desktop'] as const) {
    test(`reads buf while empty and buf N after appends (${surface})`, async ($, on) => {
      const fake = world(on, 'first part')
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      expect(await seg(ui)).toBe('buf')
      await ui.press({ key: 'buf' })
      await ui.press({ key: 'buf-append' })
      expect(await seg(ui)).toBe('buf 1 ▾')
      fake.draft = 'second part'
      await ui.press({ key: 'buf-append' })
      expect(await seg(ui)).toBe('buf 2 ▾')
    })

    test(`append moves the draft in and clears the prompt; an empty draft adds nothing (${surface})`, async ($, on) => {
      const fake = world(on, 'draft one\nline two  \n')
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      await ui.press({ key: 'buf' })
      await ui.press({ key: 'buf-append' })
      expect(fake.draft).toBe('')
      expect(fake.store['buf:s1']).toEqual(['draft one\nline two'])
      expect(fake.storedAtFill[0]).toEqual(['draft one\nline two'])
      fake.draft = '   '
      await ui.press({ key: 'buf-append' })
      expect(fake.draft).toBe('   ')
      expect(fake.store['buf:s1']).toEqual(['draft one\nline two'])
    })

    test(`take fills the prompt with every part and keeps them; a draft gets them on a new line (${surface})`, async ($, on) => {
      const fake = world(on, '', { 'buf:s1': ['A', 'B'] })
      await start($)
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      await ui.press({ key: 'buf' })
      await ui.press({ key: 'buf-take' })
      expect(fake.draft).toBe('A\nB')
      fake.draft = 'mine'
      await ui.press({ key: 'buf-take' })
      expect(fake.draft).toBe('mine\nA\nB')
      expect(await seg(ui)).toBe('buf 2 ▾')
    })

    test(`clear empties it; take and clear show only while it holds something (${surface})`, async ($, on) => {
      const fake = world(on, 'keep me')
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, ...BAND })
      await ui.press({ key: 'buf' })
      expect(await ui.find({ key: 'buf-take' })).toBeUndefined()
      expect(await ui.find({ key: 'buf-clear' })).toBeUndefined()
      await ui.press({ key: 'buf-append' })
      expect(await ui.find({ type: 'Text', text: 'keep me' })).toBeDefined()
      await ui.press({ key: 'buf-clear' })
      expect(await seg(ui)).toBe('buf ▾')
      expect(fake.store['buf:s1']).toBeUndefined()
      expect(await ui.find({ key: 'buf-take' })).toBeUndefined()
    })
  }

  test('a resumed session gets its parts back; another session does not see them', async ($, on) => {
    world(on, '', { 'buf:s1': ['from before'], 'buf:s0': ['other session'] })
    await start($)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect(await seg(ui)).toBe('buf 1')
    await ui.press({ key: 'buf' })
    expect(await ui.find({ type: 'Text', text: 'from before' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'other session' })).toBeUndefined()
  })

  test('a long buffer previews its first rows and counts the parts left out', async ($, on) => {
    world(on, '', { 'buf:s1': ['one', 'two', 'three', 'four', 'five', 'six'] })
    await start($)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    await ui.press({ key: 'buf' })
    expect(await ui.find({ type: 'Text', text: 'one' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'six' })).toBeUndefined()
    expect(await ui.find({ type: 'Text', text: /… 3 more/ })).toBeDefined()
  })

  test('a card title leaves room for the buf segment', async ($, on) => {
    const card = {
      project: 'xg-skills',
      card: { project: 'xg-skills', id: '050', title: 'a card title long enough to fill whatever room the line has left '.repeat(2), status: 'executing', summary: '', dir: '/d', reqs: [] },
    }
    world(on, '', {}, { card })
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect(await seg(ui)).toBe('buf')
    expect((await ui.find({ key: 'card' }))?.text).toMatch(/…/)
  })
})
