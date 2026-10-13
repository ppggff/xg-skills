export type HudReq = { n: number; word: string; title: string }

export type HudCard = {
  project: string
  id: string
  title: string
  status: string
  summary: string
  reqs: HudReq[]
  dir: string
}

export type HudCardSlot = { project: string | null; card: HudCard | null }

export type HudKbRow = { project: string; raw: number; wiki: number; uncompiled: number; slugs: string[] }

export type HudKb = {
  project: string | null
  rows: HudKbRow[]
  reads: string[]
  added: string[]
  updated: string[]
}

export type HudKbStart = { at: number; names: string[] }

// One item of this session's todo working set: where it lives in the viewer's todo files and its text.
export type HudTodo = { file: string; created: string; key: string; text: string; project: string | null }

declare module 'claude-code' {
  interface PluginState {
    'xg-hud': {
      card: HudCardSlot | null
      kb: HudKb | null
      kbStart: HudKbStart | null
      kbReads: string[]
      kbTouched: string[]
      isDoneShown: boolean
      cardPage: number
      kbPage: number
      isKbOpen: boolean
      isCardOpen: boolean
      todos: HudTodo[]
      isTodoOpen: boolean
      isTodoLoading: boolean
      todoCandidates: HudTodo[]
      todoLoadAt: number
    }
  }
}
