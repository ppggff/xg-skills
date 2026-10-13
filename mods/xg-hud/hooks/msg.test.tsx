import { describe, expect, mock, test } from 'claude-code/testing'
import type { Engine, MockClock } from 'claude-code/testing'
import type { On } from 'claude-code'

import { agoText, clockText } from './register'

const BAND = { component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 120 } as never } as const

function world(on: On, store: Record<string, unknown> = {}): MockClock {
  const clock = mock.clock(on)
  mock.store(on, store)
  mock.env(on, { HOME: '/home/t' })
  on('session.id', () => ({ value: 's1' }))
  on('session.cwd', () => ({ value: '/work' }))
  on('fs.read', () => ({ deny: 'absent' }) as never)
  on('fs.list', () => ({ value: [] }) as never)
  on('process.run', () => ({ value: { exitCode: 0, stdout: '[]', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never)
  on('command.register', (_$, e) => ({ value: { command: (e as unknown as { name: string }).name } }) as never)
  on('session.start', () => ({ cwd: '/work' }) as never)
  on('prompt.submit', (_$, e) => ({ text: e.text }) as never)
  on('turn.complete', () => ({ text: 'done' }) as never)
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return <Box />
  })
  return clock
}

const typed = ($: Engine, kind = 'composer') => $.prompt.submit({ text: 'hi', wait: false, origin: { kind } } as never)
const replied = ($: Engine) => $.turn.complete({ turnId: 't1', answer: 'done', durationMs: 1, isInterrupted: false, reason: 'end_turn' } as never)
const start = ($: Engine) => $.session.start({ cwd: '/work', surface: 'terminal', isInteractive: true } as never)

describe('time text', () => {
  test('clock and ago read as a person would', () => {
    expect(clockText(new Date(2026, 9, 13, 9, 5).getTime())).toBe('09:05')
    expect(agoText(30_000)).toBe('<1m ago')
    expect(agoText(12 * 60_000)).toBe('12m ago')
    expect(agoText((2 * 60 + 5) * 60_000)).toBe('2h 5m ago')
    expect(agoText(3 * 24 * 3600_000)).toBe('3d ago')
  })
})

describe('msg segment', () => {
  test('hidden until a typed message; other origins do not count', async ($, on) => {
    const clock = world(on)
    await clock.set(new Date(2026, 9, 13, 14, 5).getTime())
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect(await ui.find({ key: 'msg' })).toBeUndefined()
    await typed($, 'task-notification')
    expect(await ui.find({ key: 'msg' })).toBeUndefined()
    await typed($)
    expect((await ui.find({ key: 'msg' }))?.text).toBe('msg 14:05')
  })

  test('open shows the last message and the last reply with how long ago, kept fresh', async ($, on) => {
    const clock = world(on)
    await clock.set(new Date(2026, 9, 13, 14, 5).getTime())
    await start($)
    await clock.settle()
    await typed($)
    await clock.advance(3 * 60_000)
    await replied($)
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    await ui.press({ key: 'msg' })
    expect(await ui.find({ type: 'Text', text: /msg 14:05 · 3m ago/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /reply 14:08 · <1m ago/ })).toBeDefined()
    await clock.advance(60_000)
    expect(await ui.find({ type: 'Text', text: /reply 14:08 · 1m ago/ })).toBeDefined()
  })

  test('a resumed session shows the times it had', async ($, on) => {
    const at = new Date(2026, 9, 13, 8, 30).getTime()
    const clock = world(on, { 'times:s1': { message: at, reply: at + 60_000 } })
    await clock.set(at + 3600_000)
    await start($)
    await clock.settle()
    const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', ...BAND })
    expect((await ui.find({ key: 'msg' }))?.text).toBe('msg 08:30')
  })
})
