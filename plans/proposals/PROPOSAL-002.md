---
id: PROPOSAL-002
type: knowledge-update + skill-change
level: L2
mode: maintain
author: harness-guardian
date: 2026-10-22
signal_source: https://github.com/huypqapero/mobile-engineering-harness/issues/9
---

# Proposal: add `knowledge/compose/ui-resilience.md` (locale text, font scale, RTL, edge-to-edge) and wire it into the Compose skills

## Rationale

User report (issue #9): when the app language changes, Compose text gets clipped or overflows. Products also hit system bar, inset and display cutout bugs. The harness gives agents no guidance to catch any of this:

- `knowledge/compose/essentials.md` covers state hoisting, recomposition, side effects, theming and previews. It has nothing on text overflow, locale-length strings, font scale, RTL or WindowInsets/edge-to-edge. Its preview example uses one locale and one font scale.
- `skills/coding-compose/SKILL.md` loads only `essentials.md`. Step 7 has a single line on font size ("không fix `fontSize` tuyệt đối"). Step 8 visual verify checks only "states + dark theme".
- `skills/coding-review/SKILL.md` checklist "D. Compose" has no locale, font scale, RTL or inset item.
- `agents/design-analyst.md` "Unknowns documentation" lists responsive, animation and dark mode. It does not flag a single-language design or a design that omits system bars.
- `verification/lint/README.md:61` enables `RtlHardcoded`, which only covers XML layouts. Compose code gets no equivalent signal.

External drivers, verified against developer.android.com and cited in the new file:
- Apps targeting SDK 35 are edge-to-edge by default on Android 15. On Android 16, apps targeting SDK 36 can no longer opt out.
- Android 14 nonlinear font scaling goes up to 200%.
- Pseudolocales `en-XA` and `ar-XB` are the official way to exercise long text and RTL.

Triage: harness gap (missing knowledge plus missing checklist items). It is not a coding-agent misinterpretation of an existing rule.

## Scope

Files touched:
- `knowledge/compose/ui-resilience.md` (new): five sections (locale text, font scale, RTL, edge-to-edge/insets, how to test), each with ❌/✅ examples, a Common mistakes table and References.
- `AGENTS.md`: list the new file right after `knowledge/compose/essentials.md`.
- `knowledge/compose/essentials.md` §Previews and §References: link to the new file (optional item 6 of the issue).
- `skills/coding-compose/SKILL.md`: Prerequisites, Step 7 (accessibility and resilience), Step 8 (visual verify), plus matching Validation checklist lines.
- `skills/coding-review/SKILL.md` §Prerequisites (load `ui-resilience.md` when the diff has Compose UI) and §D. Compose: three new one-line checklist items, plus a note that they cap at HIGH severity because no MUST rule backs them.
- `agents/design-analyst.md` §Scope summary line and §Unknowns documentation: single-language design unknown and system bar/cutout unknown.
- `CHANGELOG.md`: `## [Unreleased]` entry.

Rules affected: none. No new rule ID, no MUST rule in `constitution/`, no ADR edit. The skill text links to the knowledge file and adds procedure steps, but it does not raise any item to a BLOCKER.

Protected Baseline (ADR-001..014, MOD-001..003, CORO-001..010): not touched.

Backward compat: additive. Existing consumers lose no guidance. The skills gain extra verify steps.

## Impact map

```yaml
affected:
  rules: []
  knowledge:
    - compose/ui-resilience.md (new)
    - compose/essentials.md (§Previews, §References link only)
  skills:
    - coding-compose (Prerequisites, Step 7, Step 8, Validation)
    - coding-review (§Prerequisites, §D. Compose checklist)
  agents:
    - design-analyst (§Scope, §Unknowns documentation)
  index:
    - AGENTS.md (knowledge list)
  consumers_reading_compose_essentials_unchanged:
    - agents/implementer.md, agents/ui-judge.md, agents/input-analyst.md
    - skills/coding-feature, coding-vibe, coding-brainstorm, coding-diagnose, business-*
    - blueprints/compose-screen/README.md
    - workflows/feature-development.md, workflows/prepare-feature-brief.md
  evaluations:
    - E04 (compose recomposition list): scenario prompt + expected impl unaffected; new checks are additive
    - E02 (code review broken PR): checklist D grows, expected findings unaffected
  blueprints: []
```

Not changed, on purpose (out of the issue's scope):
- `constitution/`, Konsist or Detekt rules, `verification/lint/`.
- Automated multi-locale screenshot tests (Paparazzi/Roborazzi).
- `knowledge/input-analysis/screenshot-reading-rules.md` (it repeats the "responsive, animation, dark mode" unknown list). It is a follow-up candidate if the owner wants the two lists in lockstep.

## Diff (file list)

| File | Before | After |
|---|---|---|
| `knowledge/compose/ui-resilience.md` | missing | new, 5 sections + Common mistakes + References |
| `AGENTS.md` | `- knowledge/compose/essentials.md` | + `- knowledge/compose/ui-resilience.md — ...` next line |
| `knowledge/compose/essentials.md` | Previews: 1 locale/1 font scale, no pointer | pointer to ui-resilience §5 + References entry |
| `skills/coding-compose/SKILL.md` | Prereq 1 file; Step 7 one font line; Step 8 "states + dark theme" | Prereq + ui-resilience; Step 7 text/font/RTL/insets bullets; Step 8 multi-locale/font-scale/insets verify; Validation lines |
| `skills/coding-review/SKILL.md` | Prereq: constitution + CLAUDE.md; D. Compose 6 items | + conditional Prereq `ui-resilience.md`; D. Compose + 3 items (locale text, font scale + RTL, insets) + severity cap HIGH |
| `agents/design-analyst.md` | Unknowns 24-26 | + 27 single-language → unknown string length; + 28 no system bar/cutout → unknown insets |
| `CHANGELOG.md` | no Unreleased | `## [Unreleased]` Added/Changed |

## Risks

- Low to medium. Docs plus skill procedure. Agents running `coding-compose` load one more knowledge file (about 300 lines), which costs context. Mitigation: the file is self-contained, and Step 7 links to its sections instead of copying them.
- Platform facts can drift (SDK 36+ behavior). Mitigation: every platform claim links developer.android.com so the weekly knowledge audit can recheck it.
- CMP vs Android: `essentials.md` targets Compose Multiplatform. The new file has a table saying where each API can be used per profile. `enableEdgeToEdge`, `WindowCompat`, `supportsRtl`, pseudolocales and the multipreview annotations are Android-only. `@Preview(locale, fontScale)` works in `commonMain` only from CMP 1.10. The table stops agents from putting Android imports in `commonMain`.
- Placeholder filename `ui-resilience.md` (issue assumption): the owner may rename it in review. A rename touches 5 references, all listed above.

## Validation plan

- Schema check: no YAML touched except this proposal's front matter, which must parse.
- Reference check: every relative path in changed files resolves, and `knowledge/compose/ui-resilience.md` is referenced from AGENTS.md, coding-compose and essentials.md.
- External links: each developer.android.com URL in the new file resolves (fetched during drafting).
- Stale reference check: no leftover "responsive, animation, dark mode"-only summary in `agents/design-analyst.md`.
- Konsist template: not touched.
- Eval: E02/E04 are manual prompt templates with no runner in this repo. Re-read them to confirm the expected outputs still hold. Fixtures stay unchanged.

## Rollback plan

`git revert <merge sha>`. The change is additive, so reverting removes the file and the checklist lines with no migration.

## Approval required

L2: independent reviewer (human or a separate agent) must review the PR. `agents/` is listed under CODEOWNERS in `agents/harness-guardian.md` §Enforcement, so the `agents/design-analyst.md` edit may also need owner review.
