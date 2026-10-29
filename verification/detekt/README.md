# Detekt Verification

Scaffold cho Detekt code quality rules trong product overlay. Harness upstream cung cấp baseline config + hướng dẫn setup. Product tự copy + customize.

## Why Detekt

Konsist cover architecture-level (dependency direction, class structure). Detekt cover code-level: unsafe null cast, exception handling, naming, complexity, performance.

Chuỗi gate: **Konsist** (ARCH, MOD) + **Detekt** (KOT, code quality) + **Android Lint** (platform-specific) → full coverage.

## Setup

### 1. Add plugin

`gradle/libs.versions.toml`:

```toml
[versions]
detekt = "1.23.6"

[plugins]
detekt = { id = "io.gitlab.arturbosch.detekt", version.ref = "detekt" }
```

Root `build.gradle.kts`:

```kotlin
plugins {
    alias(libs.plugins.detekt) apply false
}

subprojects {
    apply(plugin = "io.gitlab.arturbosch.detekt")
    configure<io.gitlab.arturbosch.detekt.extensions.DetektExtension> {
        config.setFrom(rootProject.file("detekt.yml"))
        buildUponDefaultConfig = true
        baseline = file("detekt-baseline.xml")
    }
}
```

### 2. Copy baseline config

Copy `detekt-config-template.yml` (file bên cạnh) vào project root:

```bash
cp .harness-overlay/upstream/verification/detekt/detekt-config-template.yml ./detekt.yml
```

Review + customize per product. Config tối ưu cho harness rule enforcement.

### 3. Generate baseline (one-time, cho project đã có code)

```bash
./gradlew detektBaseline
```

Sinh `detekt-baseline.xml` capture violation hiện tại → không block merge nhưng ngăn new violation.

### 4. Run

```bash
./gradlew detekt                                      # full project
./gradlew :<module>:detekt                            # module-scoped
./gradlew detekt --auto-correct                       # fix formatting auto
```

### 5. Integrate CI

```yaml
- name: Detekt
  run: ./gradlew detekt
```

Fail CI nếu violation ngoài baseline.

## Custom rule enforcement

Detekt mặc định có ~140 rules. Harness kích hoạt / tune 1 số critical cho enforcement constitution:

| Detekt rule | Enforces |
|---|---|
| `potential-bugs:UnsafeCallOnNullableType` | KOT-002 (no `!!`) |
| `potential-bugs:ExplicitGarbageCollectionCall` | KOT general |
| `exceptions:TooGenericExceptionCaught` | KOT-009 (no `Exception` broad) |
| `exceptions:SwallowedException` | CORO-004 (preserve cancellation) |
| `exceptions:ReturnFromFinally` | KOT general |
| `style:MagicNumber` | KOT (constants) |
| `style:ReturnCount` | KOT (readability) |
| `complexity:LongMethod` | KOT (file < 400) |
| `complexity:LongParameterList` | SRP |
| `complexity:TooManyFunctions` | SRP |
| `naming:ClassNaming`, `FunctionNaming`, `VariableNaming` | KOT-001 |
| `performance:SpreadOperator` | perf heuristic |

Chi tiết trong `detekt-config-template.yml`.

## Custom rule (advanced)

Khi harness rule không có trong default Detekt, viết custom rule:

```kotlin
// detekt-rules module (optional)
class PreferLifecycleAwareCollect : Rule() {
    override val issue = Issue(
        id = "PreferLifecycleAwareCollect",
        severity = Severity.CodeSmell,
        description = "Use collectAsStateWithLifecycle instead of collectAsState",
        debt = Debt.FIVE_MINS,
    )

    override fun visitCallExpression(expression: KtCallExpression) {
        super.visitCallExpression(expression)
        if (expression.calleeExpression?.text == "collectAsState") {
            report(CodeSmell(issue, Entity.from(expression), issue.description))
        }
    }
}
```

Register qua `RuleSetProvider` → compile thành jar → add vào `detektPlugins` config.

**Khi nào custom rule**: harness rule MUST không catch được bằng Konsist + default Detekt + manual review. Thường rare — document pattern trước, add rule sau khi vi phạm 3+ lần.

## Severity levels trong Detekt

| Severity | Mapping to harness |
|---|---|
| `error` | MUST rule → fail build |
| `warning` | SHOULD rule → warning |
| `info` | Suggestion → log |

Config trong `detekt-config-template.yml`.

## Baseline strategy

- **Fresh project**: không cần baseline, enforce clean từ đầu
- **Existing project**: generate baseline → freeze current violations → prevent new
- **Review baseline định kỳ**: shrink baseline khi fix cũ, re-generate

## Common issues

| Issue | Fix |
|---|---|
| False positive quá nhiều | Add `@Suppress("RuleName")` ở class/function; không disable rule globally |
| Rule không fit team style | Tune threshold trong `detekt.yml`, không disable |
| Baseline grow uncontrolled | Policy: PR mới không được add vào baseline (except explicit review) |
| CI slow | `--parallel` + build cache |
| Compose composable name `PascalCase` fail `FunctionNaming` | Exclude pattern composable từ FunctionNaming |

## Compose-specific exclusions

Composable function `PascalCase` conflict với `FunctionNaming` rule. Fix trong `detekt.yml`:

```yaml
naming:
  FunctionNaming:
    excludes: ['**/*Composable*.kt', '**/compose/**']
    functionPattern: '[a-z][a-zA-Z0-9]*'
    excludeClassPattern: '$^'
```

Hoặc dùng `@Suppress("FunctionNaming")` per composable (verbose).

## References

- Detekt: https://detekt.dev
- `.harness/constitution/kotlin-conventions.md [KB → team/arch-constitution, kb_search "kotlin conventions"]`
- `.harness/constitution/concurrency-rules.md [KB → team/arch-constitution, kb_search "concurrency rules"]`
- Konsist: `../architecture-tests/TemplateArchitectureRulesTest.kt`
