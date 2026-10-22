# Independent review — issue #9 / PROPOSAL-002 (L2)

- Date: 2026-10-22
- Reviewer: separate code-reviewer agent (fresh context, read-only), not the proposing Guardian session
- Scope: `knowledge/compose/ui-resilience.md` (new), `skills/coding-compose/SKILL.md`, `skills/coding-review/SKILL.md`, `agents/design-analyst.md`, `knowledge/compose/essentials.md`, `AGENTS.md`, `CHANGELOG.md`, `plans/proposals/PROPOSAL-002.md`
- Verdict: DONE_WITH_CONCERNS → all findings fixed in the same PR. Severity count: 0 Critical / 4 Important / 7 Minor, resolved 11/11.

This agent review doesn't replace the human independent review that L2 requires (`knowledge/harness-governance/essentials.md` §Review requirements).

## Findings and resolution

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | Important | Claim that nested `safeDrawingPadding()` + Scaffold insets pad twice was wrong. Inset padding modifiers consume what they apply, while `padding(innerPadding)` does not | Rewrote: inset modifiers self-consume; add `consumeWindowInsets(innerPadding)` when a child uses inset modifiers. Added a ❌/✅ example and a Common mistakes row |
| 2 | Important | `safeDrawing` already includes IME, so `.safeDrawingPadding().imePadding()` is redundant | Stated that `safeDrawing` includes IME; `imePadding()` only when padding just system bars or `innerPadding`. Same change in coding-compose Step 7 |
| 3 | Important | `Alignment.Left` doesn't exist | `AbsoluteAlignment.Left` |
| 4 | Important | Source-set table mislabeled the `kmp` profile (no shared UI) and `android-only` (no `commonMain`) | Table now has columns `cmp` vs `kmp (Android UI) / android-only` |
| 5 | Minor | `enableEdgeToEdge` deprecation overstated; release note only recommends `WindowCompat.enableEdgeToEdge(window)` | Reworded; dropped the `SystemBarStyle` deprecation claim |
| 6 | Minor | `ScrollableTabRow` is deprecated in M3 | Lead with `PrimaryScrollableTabRow` / `SecondaryScrollableTabRow` |
| 7 | Minor | Multipreview annotations in `commonMain` not backed by the CMP docs | Restricted the common claim to `@Preview(locale, fontScale)` (CMP 1.10+); multipreview is Android-only |
| 8 | Minor | ARCH-010 cited outside its scope (could be escalated to BLOCKER) | Removed; the reason given is "won't compile for iOS" |
| 9 | Minor | Device check not always runnable by agents | "Khi có device"; otherwise the report says insets weren't verified on device |
| 10 | Minor | Proposal risk line out of sync (`values-ldrtl`, preview source set) | Proposal updated |
| 11 | Minor | Linear `Density(fontScale)` caveat; ❌/✅ string key mismatch | Caveat added; example aligned |

## Verified correct by the reviewer

Android 15 / SDK 35 edge-to-edge default; Android 16 / SDK 36 opt-out disabled; `@PreviewFontScale` (singular, 7 steps up to 2.0); multipreview from ui-tooling 1.6.0; `isPseudoLocalesEnabled` and `en-XA`/`ar-XB` behavior; `ImageVector.Builder(autoMirror)`, `Icons.AutoMirrored`; Scaffold `innerPadding` semantics; W3C/IBM expansion figures; E04 golden answer still holds and E02 is unaffected; no new placeholder and no MUST/rule ID added.
