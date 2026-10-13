import { describe, expect, test } from 'claude-code/testing'

import { isRemoteCheck, judge } from './rules'

describe('commit messages', () => {
  test('plain message passes', () => {
    expect(judge('git commit -m "viewer: fix todo dates"', true)).toBe(null)
  })
  test('emoji is denied', () => {
    expect(judge('git commit -m "fix ✅ dates"', true)).toHaveProperty('deny')
  })
  test('circled digit is denied', () => {
    expect(judge('git commit -m "step ① done"', true)).toHaveProperty('deny')
  })
  test('workflow tail is denied', () => {
    expect(judge("git commit -m \"$(cat <<'EOF'\nviewer: x (045 Req-3)\nEOF\n)\"", true)).toHaveProperty('deny')
  })
  test('data repos may cite workflow ids', () => {
    expect(judge('cd ~/dev-workflow && git commit -m "045 Req-3 verified"', true)).toBe(null)
  })
  test('path before commit is not the message', () => {
    expect(judge('git -C ~/xxx/x commit -m "plain"', true)).toBe(null)
  })
  test('a later command in the same call is not the message', () => {
    expect(judge('git commit -m "plain" && python3 - <<\'EOF\'\nprint("✅ Req-3")\nEOF', true)).toBe(null)
    expect(judge('git commit -m \'plain\'; echo "① ✅"', true)).toBe(null)
    expect(judge('git commit -m "plain" | cat && echo ✅', true)).toBe(null)
    expect(judge('git commit -m "plain"\necho "✅"', true)).toBe(null)
  })
  test('the message is still checked in every form', () => {
    expect(judge('git commit -m "a && b ✅"', true)).toHaveProperty('deny')
    expect(judge("git commit -m 'step ① ; done'", true)).toHaveProperty('deny')
    expect(judge("git commit -m \"$(cat <<'EOF'\nfix ✅ dates\nEOF\n)\" && echo ok", true)).toHaveProperty('deny')
    expect(judge("git commit -F - <<'EOF'\nfix (045 Req-3)\nEOF\necho done", true)).toHaveProperty('deny')
    expect(judge('git commit -F - <<-TAG\n\tfix ✅\n\tTAG', true)).toHaveProperty('deny')
  })
  test('amend asks', () => {
    expect(judge('git commit --amend --no-edit', true)).toHaveProperty('ask')
  })
})

describe('fetch and remotes', () => {
  test('origin fetch passes', () => {
    expect(judge('git fetch origin main', true)).toBe(null)
    expect(judge('git fetch', true)).toBe(null)
  })
  test('foreign fetch without --no-tags is denied', () => {
    expect(judge('git fetch gpdb main', true)).toHaveProperty('deny')
    expect(judge('git fetch --all', true)).toHaveProperty('deny')
  })
  test('foreign fetch with --no-tags passes', () => {
    expect(judge('git fetch --no-tags gpdb refs/heads/main:refs/gpdb/main', true)).toBe(null)
  })
  test('remote add needs --no-tags', () => {
    expect(judge('git remote add gpdb https://x/y.git', true)).toHaveProperty('deny')
    expect(judge('git remote add --no-tags gpdb https://x/y.git', true)).toBe(null)
  })
})

describe('push and history', () => {
  test('push before remote -v is denied', () => {
    expect(judge('git push origin main', false)).toHaveProperty('deny')
  })
  test('plain push after remote -v passes', () => {
    expect(judge('git push origin main', true)).toBe(null)
  })
  test('force push and MR creation ask', () => {
    expect(judge('git push -f origin main', true)).toHaveProperty('ask')
    expect(judge('git push -o merge_request.create origin x', true)).toHaveProperty('ask')
  })
  test('reset --hard and rebase ask, rebase --continue passes', () => {
    expect(judge('git reset --hard HEAD~1', true)).toHaveProperty('ask')
    expect(judge('git rebase main', true)).toHaveProperty('ask')
    expect(judge('git rebase --continue', true)).toBe(null)
  })
  test('git -C path is parsed', () => {
    expect(judge('git -C ~/xxx/cbdb fetch gpdb', true)).toHaveProperty('deny')
  })
  test('remote check detection', () => {
    expect(isRemoteCheck('git remote -v')).toBe(true)
    expect(isRemoteCheck('cd x && git -C y remote -v && git status')).toBe(true)
    expect(isRemoteCheck('git status')).toBe(false)
  })
})
