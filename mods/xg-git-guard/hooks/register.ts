import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import { isRemoteCheck, judge } from './rules'

const remoteChecked = atom({ plugin: 'xg-git-guard', key: 'isRemoteChecked' } as const, false)

function commandOf(input: unknown): string {
  const command = (input as { command?: unknown } | null)?.command
  return typeof command === 'string' ? command : ''
}

export const register: Register = on => {
  on('tool.check', { tool: 'Bash' }, async ($, e, next) => {
    const core = await next(e)
    if (core.decision === 'deny') return core

    const verdict = judge(commandOf(e.input), await read($, remoteChecked))
    if (verdict === null) return core
    if ('deny' in verdict) return { decision: 'deny', reason: `xg-git-guard: ${verdict.deny}` }

    return { decision: 'ask', reason: `xg-git-guard: ${verdict.ask}` }
  })

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true && isRemoteCheck(e.command)) {
      await update($, remoteChecked, () => true)
    }

    return ran
  })
}
