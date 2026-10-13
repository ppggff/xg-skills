/** Pure judgement of one Bash command against the git conventions in ~/.claude/CLAUDE.md. */

export type Verdict = { deny: string } | { ask: string } | null

const GIT_SUB = /\bgit((?:\s+-[Cc]\s+\S+)*)\s+([a-z][\w-]*)([^\n;&|]*)/g
const EMOJI = /[\p{Emoji_Presentation}\u{FE0F}]/u
const ENCLOSED_DIGIT = /[①-⓿❶-➓㉈-㉏㉑-㉟㊀-㊿\u{1F10B}-\u{1F10C}]/u
const WORKFLOW_REF =
  /\(\d{3} Req-\d+\)|\bReq-\d+\b|\[\[(?:raw|wiki)\/|\bADR-\d{4}\b|\bdev_root\b|~\/knowledge|dev-workflow\//

const DATA_REPO = /(?:~|\/Users\/[^/\s]+)\/(?:knowledge|dev-workflow)\b/

type Call = { sub: string; args: string[]; at: number }

function gitCalls(command: string): Call[] {
  return [...command.matchAll(GIT_SUB)].map(m => ({
    sub: m[2]!,
    args: m[3]!.trim().split(/\s+/).filter(Boolean),
    at: (m.index ?? 0) + 3 + m[1]!.length,
  }))
}

// The KB and dev_root data repos may cite workflow ids; only product repos may not.
function commitMessageProblem(command: string, at: number): string | null {
  const message = command.slice(at)
  const found: string[] = []
  if (EMOJI.test(message)) found.push('emoji')
  if (ENCLOSED_DIGIT.test(message)) found.push('circled/boxed digits')
  const ref = DATA_REPO.test(command) ? null : message.match(WORKFLOW_REF)
  if (ref) found.push(`workflow/KB reference "${ref[0]}"`)
  return found.length ? found.join(', ') : null
}

function firstPositional(args: string[]): string | undefined {
  return args.find(a => !a.startsWith('-'))
}

export function judge(command: string, isRemoteChecked: boolean): Verdict {
  const calls = gitCalls(command)
  const asks: string[] = []

  for (const { sub, args, at } of calls) {
    if (sub === 'commit') {
      const problem = commitMessageProblem(command, at)
      if (problem) return { deny: `Commit message must be plain text with no ${problem}; drop it and retry.` }
      if (args.includes('--amend')) asks.push('git commit --amend rewrites an existing commit')
    }

    if (sub === 'fetch' || sub === 'pull') {
      const remote = firstPositional(args)
      const isForeign = args.includes('--all') || (remote !== undefined && remote !== 'origin')
      if (isForeign && !args.includes('--no-tags')) {
        return { deny: `git ${sub} from a non-origin remote must pass --no-tags (foreign tags leak into origin on the next push).` }
      }
    }

    if (sub === 'remote' && args[0] === 'add' && !args.includes('--no-tags')) {
      return { deny: 'git remote add must pass --no-tags so fetches never pull foreign tags.' }
    }

    if (sub === 'push') {
      if (!isRemoteChecked) return { deny: 'Run `git remote -v` first to confirm the push target, then retry the push.' }
      if (args.some(a => a.includes('merge_request.create'))) asks.push('push creates a merge request')
      if (args.some(a => /^(-f|--force(-with-lease)?(=.*)?)$/.test(a) || a.startsWith('+'))) asks.push('force push')
      if (args.includes('--tags')) asks.push('push --tags')
    }

    if (sub === 'reset' && args.includes('--hard')) asks.push('git reset --hard discards work')
    if (sub === 'rebase' && !args.some(a => /^--(abort|continue|skip)$/.test(a))) asks.push('git rebase rewrites history')
  }

  if (/\bglab\s+mr\s+update\b/.test(command)) asks.push('glab mr update: confirm the MR id belongs to this branch')

  return asks.length ? { ask: asks.join('; ') } : null
}

export function isRemoteCheck(command: string): boolean {
  return gitCalls(command).some(c => c.sub === 'remote' && (c.args.includes('-v') || c.args[0] === 'get-url'))
}
