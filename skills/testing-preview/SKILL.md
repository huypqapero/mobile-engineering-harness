---
name: testing-preview
description: Verification gate render Compose UI headless qua Android CLI preview rồi so sánh với design/spec gốc. Trigger khi feature có UI cần verify preview, render @Preview thành PNG, đối chiếu design, inspect long-text/narrow layout, hoặc thêm preview quality gate. Capture PNG + component-tree làm evidence, review từng case, fix/retest defect khi được authorize. KHÔNG certify E2E / runtime perf / SDK integration / device fidelity (những thứ đó thuộc testing-android + Artemis device pipeline).
priority: P2
---

# Skill: testing-preview

> Optional UI verification gate của harness. Vai trò **verify** (song song `testing-android`), không phải authoring — viết `@Preview` là việc của `coding-compose`, skill này **render + đối chiếu design**. Trigger thường từ `coding-feature` Step 6 (khi feature có UI) hoặc `coding-vibe` (UI mode).

Run a bounded, evidence-based preview test. Respond in the user's language. Use official Android CLI for rendering and the agent's image-reading capability for visual review. Treat renderer success as `RENDERED_PENDING_REVIEW`, never as a UI pass.

## Inspect the project

1. Read project instructions, architecture conventions, build configuration and the requested feature. Use `rg` to find `@Preview`, screen composables, UiState, themes and existing screenshot tests. Preserve MVI, cancellation behavior and public SDK boundaries.
2. Establish project root, target, expected states, requirements and design/spec references from available context. Do not ask for information the repository already contains. Test available requirements when design is unavailable, but report design comparison as not performed. If design comparison was explicitly required, missing design is a blocker; do not silently downgrade it.
3. Inspect `android --version`, `android preview list --help`, and `android preview render --help`. If the `android` CLI is missing, install the standalone binary (user-level, no sudo) per [android-reference.md](references/android-reference.md) "Installing the Android CLI" rather than hard-blocking; it is not in `sdkmanager`/Homebrew/Android Studio. Do not upgrade AGP, Gradle or plugins solely to make a check pass. Resolve ordinary environment issues within existing authorization; report anything that still cannot be resolved precisely.
4. Discover actual FQNs with `android preview list :module --format=json`. **Module có product flavor** (lỗi `Variant 'debug' does not exist`): dùng `:module@<flavorBuildType>`, ví dụ `android preview list ":app@appDevDebug"`, và dùng cùng reference đó cho `render`. Xem [android-reference.md](references/android-reference.md), mục "Product flavors". Do not guess Kotlin-generated names or assume test-only source sets are on the CLI classpath. Retain raw output; CLI JSON schemas can vary.

## Prepare meaningful cases

Read [preview-contract.md](references/preview-contract.md) for manifest/review fields and [android-reference.md](references/android-reference.md) for commands and patterns. Copy [cases.example.json](assets/cases.example.json) into the project and adapt it; its names and expectations are examples, not discovered facts.

- Prefer one no-argument preview function per case/configuration. Render the production `Screen(UiState, onAction)` with deterministic fixtures, the real theme and a fixed viewport. Keep previews/fixtures out of published SDK artifacts.
- `android preview list` discovers only AndroidX `@Preview` (`androidx.compose.ui.tooling.preview.Preview`). In a Compose Multiplatform module it does NOT see the JetBrains annotation (`org.jetbrains.compose...Preview`) — `list` returns `"previews": []`. Put previews in `androidMain` with the AndroidX annotation over a stateless `Content(state, …)` kept in `commonMain`; see [android-reference.md](references/android-reference.md).
- Cover normal content, long content plus narrow viewport, loading and error as relevant. Add empty, RTL or wide layouts only when supported/required. Do not invent requirements such as allowing ellipsis on mandatory text.
- Out of scope: do not create or review dark-theme or large-font-scale (`fontScale` > 1) cases. Render with the default light theme and `fontScale = 1f`. If the user explicitly asks for either, report it as untested scope rather than adding cases.
- Inspect annotations and fixture bodies to confirm configuration. Manifest labels do not apply locale or dimensions. Multipreview does not imply a Cartesian product. Set exact expected output counts and review every image; prefer dedicated functions when variant identity is ambiguous.
- Freeze clocks, random values and remote media. Substitute data/resources while retaining production layout. Do not hide broken UI with `LocalInspectionMode`, change behavior to bypass Hilt, or disable assertions.
- Give requirements stable IDs and explicit expected results. Include design frame/version and viewport conventions. Export/download design only through an authorized source.

## Render evidence

Resolve this skill's directory as `SKILL_DIR`. Require Python 3.10+; the runner uses the standard library.

```bash
python3 "$SKILL_DIR/scripts/preview_test.py" render \
  --project /absolute/project/root \
  --manifest /absolute/project/root/qa/profile-preview.json
```

Read the returned absolute `run_dir`. The runner creates a unique directory outside the project, captures CLI version/help, invokes one FQN per case with a timeout, checks PNG structure and JSON presence, and writes `report.json` plus `review-template.json`. It hashes Git-visible inputs, the manifest, references and artifacts. Failed runs retain diagnostics. `--runs-dir` must be outside the project; `--timeout` is a per-render deadline.

Exit 0 from `render` means evidence collection completed, not visual correctness. Nonzero means failed/blocked. Missing artifacts, count mismatches, invalid files, CLI errors and changed inputs prevent a pass. Never fabricate fallback images, trees, results or baselines.

## Review and verify

1. Read `report.json`. Open every actual PNG with an image-reading tool. Inspect relevant component-tree data and source locations. Open each design image or read each spec required by the case.
2. Check adaptation, mandatory text, component presence, expected state and design intent. Distinguish confirmed defects, uncertainty and intentional changes. Align density/fonts/system-bar conventions before comparing images.
3. Do not infer clipping, touchability, accessibility compliance or callback behavior from bounds alone. Use dedicated tests for text layout/semantics and devices for interactions. Mark uncertainty `NEEDS_REVIEW`.
4. Copy `review-template.json` to `review.json`. Fill reviewer/time, images/references reviewed, every requirement's check and actionable findings. Do not edit report requirements, expected counts or captured inputs. A PASS requires every check to pass with no unresolved findings. The verifier checks integrity/completeness, not whether the agent really saw or correctly judged an image.
5. Run:

```bash
python3 "$SKILL_DIR/scripts/preview_test.py" verify \
  --run-dir /absolute/run/directory \
  --review /absolute/run/directory/review.json
```

Only report `PASS_PREVIEW` after `verify` succeeds. Rerender if project files/inputs changed. Fingerprints cover Git-visible files and explicit references, not all ignored/external build inputs. Pin the environment and inspect external dependencies before trusting CI results.

## Fix and retest

For test-only requests, report findings without modifying production code. When fixes are authorized (including an existing autofix workflow), make focused changes and rerender. Keep stable finding IDs across runs. Allow at most three fix/retest rounds, then summarize the blocker. Do not reduce font, drop cases, weaken checks, update baselines or alter acceptance requirements to force a pass. Follow the project's normal review process for intentional design/baseline changes; existing authorization still applies.

Use fresh evidence for every revision. During iteration inspect affected cases; before completion run the full manifest. Never reuse a review from another run/revision.

## Existing screenshot gate and runtime handoff

If screenshot tests exist, discover and run their validation task, preserve the exit code/report and include its outcome in the final decision. Do not run baseline update tasks. Read the Android reference before changing setup; do not mix legacy and AGP test-suite task names.

A failed required screenshot test overrides the runner's PASS_PREVIEW: report FAIL_PREVIEW with that test's evidence. A skipped/no-test required suite is BLOCKED. The bundled verifier only covers its captured preview manifest and explicit review; it does not automatically run or verify external Gradle tests.

Hand navigation, IME, lifecycle, permission, R8, performance and SDK-host integration to the project's Maestro/Artemis/device pipeline. Preview PASS is not E2E PASS. Do not publish/release as part of this skill.

## Report

Return feature, revision, case count and `PASS_PREVIEW`, `FAIL_PREVIEW`, `NEEDS_REVIEW` or `BLOCKED`. Link report and representative evidence where supported. State untested scope, missing design/baseline, environment limitations, screenshot-test outcome and next action. Never claim the entire feature/app is verified from previews alone.

---

## Harness context

- Role: optional UI verification gate. Vai verify song song `testing-android` (interaction test); bổ sung chứ không thay thế.
- Boundary với skill khác:
  - `coding-compose` Step 6 **viết** `@Preview` (5 state) → skill này **render + đối chiếu design**. Đừng lẫn authoring với verification.
  - `testing-android` = compose-ui-test (interaction, semantics). Preview PASS ≠ E2E PASS.
  - Navigation / IME / lifecycle / permission / performance / SDK-host → chuyển Artemis device pipeline (`~/.claude/rules/artemis.md`).
- Upstream trigger: `coding-feature` Step 6 (UI feature, optional) + `coding-vibe` (UI mode, optional gate sau implement).
- Guardrails: `~/.claude/rules/development-rules.md`, `review-audit-self-decision.md`.

## Prerequisites (môi trường)

- **`android` standalone CLI** (binary user-level, không có trong sdkmanager/Homebrew/Android Studio). Thiếu → cài theo `references/android-reference.md §Installing the Android CLI`, không hard-block, không nâng AGP/Gradle chỉ để pass.
- **Python 3.10+** (runner dùng standard library). Trong harness dùng `~/.claude/skills/.venv/bin/python3` nếu venv tồn tại, else `python3` hệ thống.
- CI consumer không cài được `android` CLI → gate này **luôn optional**, không được đặt làm bắt buộc trong quality gate của `coding-feature`/`coding-vibe`.

## Overlay gate

Skill chạy tại repo product (có `.harness-overlay/overlay.yaml`). Preview target module resolve theo placeholder `{{MODULE_PRESENTER}}` / `{{MODULE_APP}}` khi gọi `android preview list :module`. Nếu overlay chưa có → vẫn chạy được bằng module path trực tiếp, report "overlay not resolved, dùng explicit module path".
