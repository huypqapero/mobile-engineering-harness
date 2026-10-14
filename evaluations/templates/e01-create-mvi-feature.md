# E01 Template — Create MVI Feature End-to-End

> Template cho evaluation scenario. Product overlay customize feature name + API shape phù hợp.

## Scenario

Yêu cầu agent implement 1 feature mới từ zero theo harness.

**Prompt mẫu**:
> Implement `<FEATURE_NAME>` feature: screen hiển thị `<DESCRIPTION>`. API endpoint `<METHOD> <PATH>` trả về `<RESPONSE_SHAPE>`. User interactions: `<LIST_INTERACTIONS>`. Follow harness `<overlay>/upstream/skills/android-feature/SKILL.md`.

## Expected outputs

- `{{MODULE_DOMAIN}}/model/<feature>/<Model>.kt`
- `{{MODULE_DOMAIN}}/usecase/<feature>/<Verb><Noun>UseCase.kt` (nếu có logic)
- `{{MODULE_DOMAIN}}/repository/<Feature>Repository.kt`
- `{{MODULE_DATA}}/dto/<Feature>Dto.kt`
- `{{MODULE_DATA}}/mapper/<Feature>Mapper.kt`
- `{{MODULE_DATA}}/remote/<Feature>Api.kt`
- `{{MODULE_DATA}}/repository/<Feature>RepositoryImpl.kt`
- `{{MODULE_PRESENTER}}/{{FEATURES_ROOT}}/<feature>/<Feature>Api.kt`
- `{{MODULE_PRESENTER}}/{{FEATURES_ROOT}}/<feature>/<Feature>Contract.kt`
- `{{MODULE_PRESENTER}}/{{FEATURES_ROOT}}/<feature>/<Feature>ViewModel.kt`
- `{{MODULE_PRESENTER}}/{{FEATURES_ROOT}}/<feature>/<Feature>Screen.kt`
- DI binding update ở 3 modules
- `NavRoute.<Feature>` + wire ở `AppNavHost`
- Unit test: ViewModel + Repository

## Evaluation dimensions

| Dimension | Weight | Pass criteria |
|---|---|---|
| Architecture compliance | 25% | ARCH-001..014 PASS theo Konsist |
| MVI correctness | 20% | State/Intent/Effect split đúng; `Channel` cho Effect; `.asStateFlow()`; nav là Effect |
| 5 UI states | 10% | Loading/empty/error/offline/success render + preview |
| Concurrency safety | 15% | `viewModelScope`, re-throw cancellation, dispatcher inject |
| Test quality | 15% | ≥ 5 tests VM; happy + error + edge; assertion specific; Turbine + runTest |
| Code quality | 10% | File < 400 dòng; không `!!`; naming self-doc; không TODO stale |
| Simplicity | 5% | Không tạo abstraction trivial |

## Scoring

- 90–100: VERIFIED, blueprint-worthy
- 75–89: VERIFIED_WITH_LIMITATIONS
- 60–74: Needs rework (violation MUST không BLOCKER)
- < 60: FAILED (có BLOCKER)

## Common failure modes to probe

1. UseCase 1-1 không logic → vi phạm YAGNI
2. Expose `MutableStateFlow` public
3. Nav dùng `SharedFlow(replay=1)` → nav 2 lần khi config change
4. Composable gọi coroutine không `LaunchedEffect` wrap
5. Thiếu `isOffline` state branch
6. `collectAsState()` không lifecycle
7. Mapper dùng `!!`
8. Test `assertNotNull` wrapper vô nghĩa
9. File > 400 dòng không tách
10. Import `android.*` trong `commonMain`

## Baseline

Chạy prompt **không có harness** → record output. Chạy **có harness** → so sánh.
Target: ≥ 30% improvement về Architecture compliance + MVI correctness.

## Customization cho product

Overlay copy template này vào `.harness-overlay/evaluations/tasks/e01-create-mvi-feature.md` và điền:
- `<FEATURE_NAME>` cụ thể product (ví dụ AudioBookApp: `CollectionDetail`)
- `<DESCRIPTION>` business context
- API shape thực tế
- Interactions liệt kê
