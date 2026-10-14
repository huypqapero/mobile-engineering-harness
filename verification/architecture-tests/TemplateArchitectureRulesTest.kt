/**
 * Architecture rules enforcement with Konsist.
 *
 * This file is a TEMPLATE. Do NOT edit it in the upstream harness repo.
 * Run `install.sh --overlay <path>` to render a product-specific copy into
 * `<overlay>/verification/architecture-tests/ArchitectureRulesTest.kt`.
 *
 * Setup (one-time per product):
 * 1. Add Konsist dependency to the product's `libs.versions.toml`.
 * 2. Copy the rendered test file into:
 *       <module>/src/jvmTest/kotlin/{{PACKAGE_ROOT_PATH}}/harness/ArchitectureRulesTest.kt
 * 3. Run:
 *       ./gradlew konsistTest
 *
 * Rule IDs reference `constitution/architecture-rules.md` (upstream).
 */
package {{PACKAGE_ROOT}}.harness

import com.lemonappdev.konsist.api.Konsist
import com.lemonappdev.konsist.api.ext.list.withNameEndingWith
import com.lemonappdev.konsist.api.ext.list.withoutNameEndingWith
import com.lemonappdev.konsist.api.ext.list.properties
import com.lemonappdev.konsist.api.verify.assertFalse
import com.lemonappdev.konsist.api.verify.assertTrue
import kotlin.test.Test

class ArchitectureRulesTest {

    // ARCH-001 — Domain purity
    @Test
    fun `ARCH-001 domain has no platform or android imports`() {
        val forbiddenPrefixes = listOf({{DOMAIN_FORBIDDEN_PREFIXES_KT}})
        Konsist
            .scopeFromModule("{{MODULE_DOMAIN}}")
            .files
            .assertFalse { file ->
                file.hasImport { imp ->
                    forbiddenPrefixes.any { imp.name.startsWith(it) }
                }
            }
    }

    // ARCH-002 — Presenter không import data
    @Test
    fun `ARCH-002 presenter does not import data module`() {
        Konsist
            .scopeFromModule("{{MODULE_PRESENTER}}")
            .files
            .assertFalse { file ->
                file.hasImport { it.name.startsWith("{{PACKAGE_ROOT}}.{{MODULE_DATA}}.") }
            }
    }

    // ARCH-003 — ViewModel không depend trực tiếp Repository impl
    @Test
    fun `ARCH-003 viewmodel does not depend on repository impl`() {
        Konsist
            .scopeFromModule("{{MODULE_PRESENTER}}")
            .classes()
            .withNameEndingWith("ViewModel")
            .properties()
            .assertFalse { prop ->
                prop.type?.name?.endsWith("RepositoryImpl") == true
            }
    }

    // ARCH-005 — Mapper là object
    @Test
    fun `ARCH-005 mappers are objects`() {
        Konsist
            .scopeFromModule("{{MODULE_DATA}}")
            .classes(includeNested = false)
            .withNameEndingWith("Mapper")
            .assertTrue { clazz -> clazz.hasModifier(com.lemonappdev.konsist.api.KoModifier.OBJECT) }
    }

    // ARCH-007 — ViewModel extends {{MVI_BASE_CLASS}}
    @Test
    fun `ARCH-007 viewmodel extends base viewmodel`() {
        Konsist
            .scopeFromModule("{{MODULE_PRESENTER}}")
            .classes()
            .withNameEndingWith("ViewModel")
            .withoutNameEndingWith("{{MVI_BASE_CLASS}}")
            .assertTrue { clazz ->
                clazz.hasParent { parent -> parent.name == "{{MVI_BASE_CLASS}}" }
            }
    }

    // ARCH-010 — Platform SDK chỉ ở data androidMain / iosMain
    @Test
    fun `ARCH-010 platform SDK restricted to platform source sets`() {
        val platformPrefixes = listOf({{PLATFORM_SDK_PREFIXES_KT}})
        Konsist
            .scopeFromProject()
            .files
            .filter {
                // allow in data/androidMain, data/iosMain, data/jvmMain
                !it.path.contains("/{{MODULE_DATA}}/src/androidMain/") &&
                !it.path.contains("/{{MODULE_DATA}}/src/iosMain/") &&
                !it.path.contains("/{{MODULE_DATA}}/src/jvmMain/")
            }
            .assertFalse { file ->
                file.hasImport { imp ->
                    platformPrefixes.any { imp.name.startsWith(it) }
                }
            }
    }

    // ARCH-013 — Mapper không dùng !! (non-null assertion)
    @Test
    fun `ARCH-013 mappers avoid non-null assertion`() {
        Konsist
            .scopeFromModule("{{MODULE_DATA}}")
            .files
            .filter { it.path.contains("/mapper/") }
            .assertFalse { file -> file.text.contains("!!") }
    }

    // CORO-001 — GlobalScope cấm toàn project
    @Test
    fun `CORO-001 no global scope anywhere`() {
        Konsist
            .scopeFromProject()
            .files
            .assertFalse { file ->
                file.text.contains("GlobalScope.launch") ||
                    file.text.contains("GlobalScope.async") ||
                    file.text.contains("GlobalScope.produce")
            }
    }

    // MOD-002 — Public API không expose ViewModel type
    @Test
    fun `MOD-002 feature api files do not expose viewmodel`() {
        Konsist
            .scopeFromModule("{{MODULE_PRESENTER}}")
            .files
            .withNameEndingWith("Api.kt")
            .assertFalse { file ->
                file.text.contains(": ViewModel") ||
                    file.text.contains("ViewModel>") ||
                    file.text.contains("<out ViewModel")
            }
    }
}
