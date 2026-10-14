# Android Lint Verification

Scaffold cho Android Lint custom rules + baseline cho product overlay. Harness upstream chỉ document approach — Android Lint config phần lớn built-in, product-specific.

## Why Android Lint

| Tool | Scope |
|---|---|
| **Konsist** | Architecture structure (dependency direction, class hierarchy) |
| **Detekt** | Code-level smell (null safety, exception, complexity, naming) |
| **Android Lint** | Platform-specific (resource, manifest, permission, API level, i18n, a11y) |

Lint catch những thứ 2 tool kia không catch: unused resource, missing contentDescription, hardcoded string (nên dùng string resource), misconfigured manifest, deprecated API level call.

## Setup

Lint built-in trong AGP, không cần dep. Enable config trong `build.gradle.kts`:

```kotlin
// {{MODULE_APP}}/build.gradle.kts
android {
    lint {
        checkDependencies = true
        checkReleaseBuilds = true
        abortOnError = true
        warningsAsErrors = false       // soft start, bump sau khi baseline clean
        baseline = file("lint-baseline.xml")
        lintConfig = file("lint.xml")
    }
}
```

## Baseline strategy

### Fresh project

```bash
./gradlew :{{MODULE_APP}}:lintRelease
# → populate lint-baseline.xml khi chạy lần đầu nếu empty
# → sau đó commit baseline file
```

Baseline freeze current issues. PR mới không được add vào baseline (except explicit review).

### Existing project

```bash
./gradlew :{{MODULE_APP}}:updateLintBaseline
```

Regenerate baseline sau cleanup.

## Rules to tune in `lint.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<lint>
    <!-- MUST catch -->
    <issue id="HardcodedText" severity="error" />
    <issue id="ContentDescription" severity="error" />
    <issue id="RtlHardcoded" severity="error" />
    <issue id="Autofill" severity="warning" />

    <!-- Performance -->
    <issue id="UnusedResources" severity="warning" />
    <issue id="Overdraw" severity="warning" />
    <issue id="ViewHolder" severity="warning" />

    <!-- Security -->
    <issue id="AllowAllHostnameVerifier" severity="error" />
    <issue id="TrustAllX509TrustManager" severity="error" />
    <issue id="GradleDependency" severity="warning" />
    <issue id="HardcodedDebugMode" severity="error" />

    <!-- API level -->
    <issue id="NewApi" severity="error" />
    <issue id="ObsoleteSdkInt" severity="warning" />

    <!-- i18n -->
    <issue id="MissingTranslation" severity="warning" />
    <issue id="MissingDefaultResource" severity="warning" />

    <!-- Accessibility -->
    <issue id="LabelFor" severity="error" />
    <issue id="ClickableViewAccessibility" severity="warning" />

    <!-- Disable (nếu intentional) -->
    <issue id="GoogleAppIndexingWarning" severity="ignore" />
</lint>
```

## Compose + Lint

Compose có bộ Lint rule riêng (via Android Studio + Compose Compiler):

- `ComposableLambdaParameterNaming` → lambda param `PascalCase` convention
- `ComposableLambdaParameterPosition` → trailing lambda position
- `ComposableNaming` → PascalCase composable
- `ComposableReturnType` → không return non-Unit từ composable
- `ModifierParameter` → `modifier: Modifier = Modifier` default position
- `StateHolderNaming` → convention cho state holder class

Enable via Compose Compiler plugin trong `build.gradle.kts`:

```kotlin
composeCompiler {
    enableStrongSkippingMode = true
    reportsDestination = ...
}
```

## Custom Lint rule (advanced)

Khi harness rule không cover được bằng Konsist + Detekt + Lint built-in:

```kotlin
// lint-rules module
class HardcodedBookIdDetector : Detector(), SourceCodeScanner {
    override fun getApplicableUastTypes() = listOf(ULiteralExpression::class.java)

    override fun createUastHandler(context: JavaContext) = object : UElementHandler() {
        override fun visitLiteralExpression(node: ULiteralExpression) {
            val value = node.value as? String ?: return
            if (value.matches(Regex("^book-\\d+$"))) {
                context.report(
                    issue = ISSUE,
                    location = context.getLocation(node),
                    message = "Hardcoded book id — use test fixture",
                )
            }
        }
    }

    companion object {
        val ISSUE = Issue.create(
            id = "HardcodedBookId",
            briefDescription = "Hardcoded book id in production code",
            explanation = "...",
            category = Category.CORRECTNESS,
            priority = 6,
            severity = Severity.WARNING,
            implementation = Implementation(HardcodedBookIdDetector::class.java, Scope.JAVA_FILE_SCOPE),
        )
    }
}
```

Register qua `IssueRegistry`:

```kotlin
class HarnessLintRegistry : IssueRegistry() {
    override val issues = listOf(HardcodedBookIdDetector.ISSUE)
    override val api = CURRENT_API
    override val vendor = Vendor(
        vendorName = "{{PRODUCT_NAME}}",
        feedbackUrl = "https://...",
    )
}
```

Register module trong `lintPublish` config:

```kotlin
// {{MODULE_APP}}/build.gradle.kts
dependencies {
    lintChecks(project(":lint-rules"))
}
```

**Khi nào custom rule**: harness rule MUST không catch bằng Konsist + Detekt + Lint built-in. Thường rare — document pattern 3+ lần vi phạm, rồi mới write rule.

## Running Lint

```bash
./gradlew lint                              # all variants
./gradlew lintRelease                        # release variant only
./gradlew :{{MODULE_APP}}:lintDebug          # specific
```

Output: `{{MODULE_APP}}/build/reports/lint-results-*.html`.

## CI integration

```yaml
# .github/workflows/ci.yml
- name: Lint
  run: ./gradlew lintRelease
```

Fail CI khi violation ngoài baseline (`abortOnError = true`).

## Baseline hygiene

Policy:
- **PR mới không được add issue vào baseline** (except explicit review approval)
- **Shrink baseline** mỗi sprint (fix 1-2 old issues)
- **Re-generate** sau major refactor cleanup

## Hoãn tới khi evidence

Hiện tại (v0.6.0): scaffold README only. Custom Lint rule chưa write — chờ evidence Konsist + Detekt + Lint built-in không catch được pattern cụ thể.

Prioritize:
1. Enable built-in Lint rules trong product
2. Generate baseline, freeze current issues
3. Enforce CI gate
4. Custom rule chỉ khi pattern Konsist/Detekt bỏ sót + lặp 3+ lần

## Reference

- Android Lint: https://developer.android.com/studio/write/lint
- Compose lint rules: https://developer.android.com/jetpack/compose/tooling/lint
- Custom Lint rule tutorial: https://developer.android.com/studio/write/lint-rules
- `.harness/verification/architecture-tests/` — Konsist
- `.harness/verification/detekt/` — Detekt
