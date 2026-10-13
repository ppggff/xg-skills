import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'

function seed(on: On, values: Record<string, unknown>): void {
  on('state.get', (_$, e, next) => {
    const key = (e as { plugin: string; key: string }).key
    return key in values ? ({ value: { value: values[key], version: 1 } } as never) : next(e)
  })
  on('ui.render', () => ({ type: 'Box', props: {}, children: [] }) as never)
}

const CARD = {
  project: 'xg-skills',
  card: {
    project: 'xg-skills', id: '045', title: 'viewer-todo-editor-plus', status: 'executing', summary: '在做。', dir: '/d',
    reqs: [{ n: 1, word: '已验证', title: '进入编辑' }, { n: 2, word: '待做', title: '工具栏' }, { n: 3, word: '放弃', title: '旧方案' }],
  },
}
const KB = { project: 'cbdb', rows: [{ project: 'cbdb', raw: 43, wiki: 27, uncompiled: 7, slugs: ['a', 'b'] }], reads: ['wiki/cbdb/a.md', ''], added: ['raw/cbdb/x.md'], updated: [] }

describe('dashboard validates on terminal and desktop', () => {
  for (const surface of ['terminal', 'desktop'] as const) {
    test(`three tiles with data (${surface})`, async ($, on) => {
      seed(on, { kb: KB, card: CARD })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 120 } as never })
      expect(ui).toBeDefined()
    })
    test(`expanded (${surface})`, async ($, on) => {
      seed(on, { kb: KB, card: CARD, isKbOpen: true, isCardOpen: true })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 120 } as never })
      expect(ui).toBeDefined()
    })
    test(`narrow (${surface})`, async ($, on) => {
      seed(on, { kb: KB, card: CARD, isKbOpen: true, isCardOpen: true })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 30 } as never })
      expect(ui).toBeDefined()
    })
    test(`expanded beyond the row budget (${surface})`, async ($, on) => {
      const many = { ...CARD, card: { ...CARD.card, reqs: Array.from({ length: 31 }, (_, i) => ({ n: i + 1, word: '已验证', title: `需求 ${i + 1}` })) } }
      seed(on, { kb: KB, card: many, isKbOpen: true, isCardOpen: true })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 8, bodyColumns: 120 } as never })
      expect(ui).toBeDefined()
    })
    test(`done shown, second page (${surface})`, async ($, on) => {
      const many = { ...CARD, card: { ...CARD.card, reqs: Array.from({ length: 31 }, (_, i) => ({ n: i + 1, word: i % 3 ? '已验证' : '待做', title: `需求 ${i + 1}` })) } }
      seed(on, { kb: KB, card: many, isCardOpen: true, isDoneShown: true, cardPage: 1 })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 8, bodyColumns: 120 } as never })
      expect(ui).toBeDefined()
    })
    test(`kb pages when both are open (${surface})`, async ($, on) => {
      const manyReads = { ...KB, reads: Array.from({ length: 30 }, (_, i) => `wiki/cbdb/c${i}.md`) }
      seed(on, { kb: manyReads, card: CARD, isKbOpen: true, isCardOpen: true, kbPage: 2 })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 120 } as never })
      expect(ui).toBeDefined()
    })
    test(`no card, short band (${surface})`, async ($, on) => {
      seed(on, { kb: KB, card: { project: 'xg-skills', card: null } })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 2, bodyColumns: 80 } as never })
      expect(ui).toBeDefined()
    })
    test(`no card, full band (${surface})`, async ($, on) => {
      seed(on, { kb: KB, card: { project: 'xg-skills', card: null } })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 80 } as never })
      expect(ui).toBeDefined()
    })
  }
})

describe('msg segment beside the others', () => {
  for (const bodyColumns of [80, 120, 200]) {
    test(`shows with KB, card and todo at ${bodyColumns} columns`, async ($, on) => {
      seed(on, { kb: KB, card: CARD, times: { message: Date.UTC(2026, 9, 13, 6, 5), reply: null } })
      const ui = await $.ui.mount({ plugin: 'xg-hud', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns } as never })
      expect(await ui.find({ key: 'msg' })).toBeDefined()
    })
  }
})
