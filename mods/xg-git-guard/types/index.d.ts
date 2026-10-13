export type GitGuardFlag = boolean

declare module 'claude-code' {
  interface PluginState {
    'xg-git-guard': { isRemoteChecked: GitGuardFlag }
  }
}
