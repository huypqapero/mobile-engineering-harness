---
id: PROPOSAL-001
type: skill-change
level: L2
mode: maintain
author: harness-guardian
date: 2026-10-15
signal_source: https://github.com/huypqapero/mobile-engineering-harness/issues/7
---

# Proposal: add `android-sdk-structure` skill (extract feature into reusable SDK/library)

## Rationale

User request (issue #7): a procedure for turning a feature into an SDK/library reused by several products, with UI and flow customization.

Evidence in the repo that the gap is real:
- `skills/android-refactor/SKILL.md` P-07 had 5 bare steps and said "Chi tiết trong `android-sdk-structure` skill (future khi có)".
- `agents/architect.md` listed `android-sdk-structure` as "(future)".
- `workflows/feature-development.md:125` and `skills/android-feature/SKILL.md:147` pointed the same skill name at a different topic, "Platform SDK integration (ExoPlayer, AVPlayer)", which ARCH-010 already governs. Two meanings for one skill name.
- MOD-001..003 and profile `sdk-library` (`overlay.schema.yaml:68-69`, `README.md:520-528`) define the rules but no procedure applies them.

Triage: harness gap (missing procedure + inconsistent references), not a coding-agent misinterpretation and not an external change.

## Scope

Files touched:
- `skills/android-sdk-structure/SKILL.md` (new)
- `skills/android-refactor/SKILL.md` §P-07 (pointer)
- `agents/architect.md` §Pair với skills (drop "future")
- `workflows/feature-development.md` §Blocker conditions (platform SDK → ARCH-010)
- `skills/android-feature/SKILL.md` §Reference selection (platform SDK → ARCH-010; feature reuse → new skill)
- `AGENTS.md` task routing + file index
- `CHANGELOG.md` Unreleased

Rules affected: none changed. MOD-001..003, ARCH-006/007/009/010/011 are referenced and applied only. Protected Baseline untouched.

Backward compat: yes. Additive skill plus reference corrections.

## Impact map

```yaml
affected:
  rules: []                       # referenced only: MOD-001..003, ARCH-002/006/007/009/010/011
  knowledge: []                   # referenced: patterns/common-patterns.md §Adapter, mvi/essentials.md, architecture/architecture-profiles.md
  skills: [android-sdk-structure (new), android-refactor, android-feature]
  workflows: [feature-development]
  agents: [architect]
  blueprints: []
  verification: []                # TemplateArchitectureRulesTest MOD-002 reused, not edited
  evaluations: []                 # no scenario covers SDK extraction
  index: [AGENTS.md, CHANGELOG.md]
```

## Design decisions

1. **Platform SDK integration stays out of the new skill.** It already has a rule (ARCH-010) and a knowledge section (`common-patterns.md §Adapter`). The two references now point there. Matches the issue's stated assumption.
2. **Single module by default; no `:feature-<x>-api` split.** MOD-001 says "1 file `<Feature>Api.kt`" per feature and says nothing about a two-module layout. Prescribing a split would be interpreting a Protected Baseline rule, so the skill tells the user to open an `evolve` proposal first. Expected outcome of such a proposal: a `-api` module still holds exactly one `<Feature>Api.kt`, so the owner may rule it MOD-001-compatible without a rule change. That ruling belongs to the owner, not to this skill.
3. **All public customization types live in `<Feature>Api.kt`** (config, theme, slots, flow, step, result). This keeps MOD-001 literal. `explicitApi()` gives a compile-time gate for it.
4. **Flow customization goes through `StepScope` (next/back/cancel) mapped to internal Intents.** Host never sees State or Intent, so ARCH-007 holds inside the SDK.
5. **CMP resource caveat.** Android resource merging allows key override; Compose Multiplatform `composeResources` do not merge by name, so text override for CMP goes through config.

## Risks

- Kotlin/Compose snippets are illustrative and not compiled in this repo (no Gradle project here). Mitigation: snippets use only stable APIs (`staticCompositionLocalOf`, `explicitApi()`, type-safe `composable<T>`, Navigation 2.8+), reviewed by hand and by an independent advisory pass.
- Binary-compat tooling names may shift (BCV vs KGP built-in ABI validation). Mitigation: skill names BCV `apiCheck`/`apiDump` and tells the reader to confirm against the Kotlin docs for their version.
- Skill length 350 lines, under the 400-line split threshold.

## Validation plan

- Schema: frontmatter parses as YAML with `name/description/priority` (same keys as other skills).
- Reference check: every backticked repo path in touched files exists; every rule ID cited exists in `constitution/`; no remaining "android-sdk-structure (future)" or "nếu có" references.
- Konsist: template not edited; snippet in skill is a copy of the existing MOD-002 test with scope changed.
- Eval: no scenario in `evaluations/templates/` (E01-E05) covers SDK extraction or the touched sections, so no run is needed.

## Rollback plan

`git revert <merge-sha>` and drop the CHANGELOG Unreleased lines. No consumer migration involved.

## Approval

L2: independent reviewer required (human). Guardian does not self-approve or merge.

## Follow-ups (out of scope here)

- Konsist test for the customization contract (L2, separate issue).
- Blueprint/sample SDK module (L1/L2).
- If two-module (`-api`) layout is wanted: L3 `evolve` proposal clarifying MOD-001.
- `agents/harness-guardian.md` names proposals both `<id>-<slug>.md` (§Draft change) and `PROPOSAL-NNN.md` (§Output); this proposal follows the latter. L0 cleanup.
- Pre-existing broken link `blueprints/complete-mvi-feature/README.md` in `skills/android-feature/SKILL.md` and `workflows/feature-development.md` (not touched here). L0 cleanup.
