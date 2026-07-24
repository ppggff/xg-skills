# Reference: Frontend / mobile testing (browser + real-device)

Branch-specific test principles for **UI / mobile-facing slices**. Load this only when the
requirement has a browser or mobile-web surface; backend / DB (cbdb-class) projects don't need it.
These extend the general test principles in `references/steps/test.md`.

- **Verify UI/frontend slices in a real browser**, not only headless — Playwright / chrome-devtools
  MCP. A DOM-rendered terminal/output appears in the accessibility snapshot (directly assertable);
  drive input via the real input element (e.g. the hidden `<textarea>`, not a `role=textbox` wrapper).
  Pair browser acceptance with the unit/integration tests; record it under "Manual verification".
- **Mobile web needs a real-DEVICE walk, not only a desktop browser.** A desktop browser is a
  forensic oracle (see 实现's Diagnosis section) but structurally cannot surface a whole class of
  mobile-Safari bugs: native `prompt`/`confirm` suppressed, inputs `<16px` triggering tap-zoom,
  nested flex dropping `min-width:0`, `visualViewport`/soft-keyboard layout shifts, a dependency's
  shipped CSS painting differently on iOS. For a mobile-facing flow, a real-device pass is a
  non-skippable acceptance gate: mark a criterion `[x]` only after the device walk; if it's verified
  only by mechanism or desktop, say so explicitly rather than claiming `[x]`.
