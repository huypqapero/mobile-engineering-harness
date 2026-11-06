# Android CLI and Compose reference

Verified against official documentation on 2026-10-30. Check installed `--help`; versions and DSLs change.

## Installing the Android CLI

The `android` CLI (the agent tool that provides `android preview list` / `android preview render`)
is a standalone Google download — it is NOT in `cmdline-tools`, `sdkmanager`, Homebrew, or Android
Studio. If `command -v android` finds nothing, install it (user-level, no sudo):

```bash
# macOS Apple Silicon (swap darwin_arm64 → darwin_x86_64 / linux_x86_64 for other hosts)
curl -fsSL https://dl.google.com/android/cli/latest/darwin_arm64/install.sh | bash
# installs to ~/.local/bin/android and appends it to PATH in your shell profile
```

The installer's first run unpacks an embedded SDK and prints the Android SDK Terms of Service; pipe
`yes` to accept non-interactively (`yes | android --version`). Afterwards:

- `android --version` prints the version (e.g. `1.1.x`).
- Point it at the project SDK with `--sdk=<path>` (from `local.properties` `sdk.dir`) or `~/.androidrc`.
- The runner locates the binary with `shutil.which`; if `~/.local/bin` is not on the session PATH,
  pass `--android-bin "$HOME/.local/bin/android"` to `preview_test.py render`.
- Download page (OS-detected): https://developer.android.com/tools/agents/android-cli/download

## Multiplatform preview annotation

Only AndroidX `@Preview` (`androidx.compose.ui.tooling.preview.Preview`) is discovered by
`android preview list`. In a Compose Multiplatform module, the JetBrains annotation
(`org.jetbrains.compose.ui.tooling.preview.Preview`, from `compose.components.uiToolingPreview`) is
NOT detected — `list` returns `"previews": []`. Put preview functions in `androidMain` with the
AndroidX annotation (`implementation("androidx.compose.ui:ui-tooling-preview")` +
`debugImplementation(compose.uiTooling)`), referencing a stateless `Content(state, …)` composable
kept in `commonMain`.

## Symlinked project inputs

`project_state` fingerprints each symlink by its committed target path (`os.readlink`), so repos that
symlink shared agent/harness files into the tree (e.g. `.claude/agents/*.md`) are supported without a
materialized checkout. It does not follow the link, so the external target need not exist.

## Headless commands

```bash
android --version
android preview list :feature:profile --format=json
android preview render :feature:profile \
  --fqn=com.example.profile.ProfilePreviewsKt.ProfileDefaultPreview \
  --component-tree --format=json --output=/absolute/output
```

- https://developer.android.com/tools/agents/android-cli
- https://developer.android.com/tools/agents/android-cli/commands/preview_list
- https://developer.android.com/tools/agents/android-cli/commands/preview_render

### Product flavors: chỉ định variant bằng `@<variant>`

Module có product flavor thì không có variant `debug`. Mặc định CLI gọi task `generateDebugComposePreviewRunfiles` nên sẽ fail với lỗi `Variant 'debug' does not exist in project ':app'. Available variants: appDevDebug, ...`. Truyền variant ngay sau module bằng `@`:

```bash
android preview list ":app@appDevDebug" --format=json
android preview render ":app@appDevDebug" --format=json --output=/abs/out \
  --fqn=<fqn1> --fqn=<fqn2>   # render bắt buộc có ít nhất 1 --fqn
```

- Lấy tên variant từ dòng `Available variants:` trong lỗi, hoặc dùng `./gradlew :app:tasks --all`. Ưu tiên flavor dev + Debug.
- Các cách sau KHÔNG có tác dụng, đừng thử lại: `:app?appDevDebug`, `:app:appDevDebug`, `-- -P<anything>=appDevDebug`.
- `@appDev` (chỉ có flavor, không có build type) cũng fail. Phải ghi đủ `<flavor><BuildType>`.
- Render nhiều preview: tạo danh sách `--fqn=` từ JSON của `list`. Trong zsh phải tách từ bằng `${=ARGS}`, nếu không cả chuỗi sẽ thành 1 FQN.
- Variant build qua Gradle thật, nên lỗi cấu hình của variant đó (google-services thiếu client cho applicationId, secret bắt buộc trong `build.gradle.kts`…) sẽ chặn preview. Báo lỗi đó cho user rồi xử lý theo cách đảo ngược được, ví dụ env var tạm cho riêng lệnh render. Không sửa file cấu hình mà không hỏi.

`list` discovers FQNs including custom multipreview annotations. `render` builds and exports PNG and optional component-tree JSON. Tree data includes bounds, names, semantics and source information; do not assume undocumented fields or runtime fidelity. The runner uses one FQN per case, no daemon, retaining raw output.

## Preview pattern

Adapt to existing types/imports; this is not a complete feature:

```kotlin
@Preview(widthDp = 320, heightDp = 640, locale = "vi")
@Composable
fun ProfileStressPreview() {
    AppTheme {
        ProfileScreen(state = ProfileFixtures.longName, onAction = {})
    }
}
```

Use the real screen with fixed state and callback. Keep Hilt/ViewModel/lifecycle at the route boundary. Preview does not supply a complete Android framework or network/filesystem environment. Multipreview annotations produce their own variants, not all cross-products. Inspect configuration in source.

- https://developer.android.com/develop/ui/compose/tooling/previews
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/reference/kotlin/androidx/compose/ui/text/TextLayoutResult

Use dedicated tests for overflow/semantics assertions. Arbitrary bound overlaps are not automatically defects: scrolling, clipping and overlays can be intentional.

## Existing screenshot tests

Official docs recommend AGP test suites over the unmaintained standalone plugin. Test-suite integration is experimental; verify compatibility before changes. Discover tasks with `./gradlew :module:tasks --all`. For suite `screenshotTest`, target `Default`, variant `Debug`, validation can be:

```bash
./gradlew :feature:profile:testScreenshotTestDefaultDebugTestSuite
```

Do not confuse this with legacy `validateDebugScreenshotTest`. Do not update baselines to resolve unexpected diffs. Inspect test counts and actual reports; skipped/no-test tasks are not evidence of coverage.

- https://developer.android.com/studio/preview/compose-screenshot-testing
- https://developer.android.com/studio/preview/compose-screenshot-testing-with-testsuites

## Runtime handoff

Use existing Maestro/Artemis/device workflows for navigation, keyboard, lifecycle, performance and SDK-host behavior. Build the required variant, including R8 where relevant. A debug preview does not verify a production APK.

- https://developer.android.com/tools/agents/android-cli/commands/run
- https://developer.android.com/tools/agents/android-cli/commands/screen_capture
- https://developer.android.com/tools/agents/android-cli/commands/layout
