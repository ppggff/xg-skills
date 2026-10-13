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

// The last prompt typed in the composer and the last main-conversation reply, epoch ms.
export type HudTimes = { message: number | null; reply: number | null }

// One todo the band shows: where it lives in the viewer's todo files and its text.
export type HudTodo = {
  file: string
  created: string
  key: string
  text: string
  project: string | null
  depth?: number
  done?: boolean
  progress?: [number, number]
  // The text todo.py's list reads back for it; while the file still says this, `text` (the original) is kept.
  listed?: string
}

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
      todoSessionRefs: string[]
      todoAt: number
      times: HudTimes
      isMsgOpen: boolean
      msgNow: number
    }
  }
}
