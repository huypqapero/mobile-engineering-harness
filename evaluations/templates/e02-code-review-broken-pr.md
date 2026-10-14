# E02 Template — Code Review Deliberately Broken PR

> Template. Product overlay viết fixture diff cụ thể dùng naming thực của product.

## Scenario

Chuẩn bị 1 diff với **8 vi phạm cố ý**. Giao agent review bằng `skills/android-code-review`. Agent phải catch ≥ 6/8.

## Prompt mẫu

> Review PR diff dưới đây theo harness `.harness-overlay/upstream/skills/android-code-review/SKILL.md`. Output findings: severity, file, line, evidence, fix.

## Broken diff template (customize naming per product)

```diff
--- a/{{MODULE_PRESENTER}}/src/.../LibraryViewModel.kt
+++ b/{{MODULE_PRESENTER}}/src/.../LibraryViewModel.kt
+import android.content.Context                                   // BUG-1: ARCH-001/010
+import {{PACKAGE_ROOT}}.{{MODULE_DATA}}.repository.LibraryRepositoryImpl  // BUG-2: ARCH-002
+import kotlinx.coroutines.GlobalScope                            // BUG-3: CORO-001
 import kotlinx.coroutines.flow.MutableStateFlow

-class LibraryViewModel : {{MVI_BASE_CLASS}}<...>(
+class LibraryViewModel(
+    private val repo: LibraryRepositoryImpl,                     // BUG-4: ARCH-003
+    private val context: Context,                                // BUG-5: ARCH-001
+) : {{MVI_BASE_CLASS}}<...>(
 ) {

-    val mutableState = MutableStateFlow(LibraryState())          // BUG-6: expose MutableStateFlow
+    val mutableState = MutableStateFlow(LibraryState())

+    fun load() {
+        GlobalScope.launch {
+            try {
+                mutableState.value = LibraryState(items = repo.getAll())
+            } catch (e: Exception) {                             // BUG-7: swallow Cancellation
+                println(e)
+            }
+        }
+    }
```

```diff
--- a/{{MODULE_DATA}}/src/.../mapper/LibraryMapper.kt
+++ b/{{MODULE_DATA}}/src/.../mapper/LibraryMapper.kt
-object LibraryMapper {
-    fun LibraryDto.toDomain() = Library(id = id, name = name)
+class LibraryMapper {                                             // BUG-8: ARCH-005
+    fun LibraryDto.toDomain() = Library(id = id!!, name = name)   // BUG-9: ARCH-013
 }
```

## Expected findings

| # | Rule | Severity |
|---|---|---|
| 1 | ARCH-002 | BLOCKER |
| 2 | ARCH-003 | BLOCKER |
| 3 | CORO-001 | BLOCKER |
| 4 | ARCH-001 | HIGH |
| 5 | ARCH-007 (MutableStateFlow public) | HIGH |
| 6 | CORO-004 (swallow cancellation) | BLOCKER |
| 7 | ARCH-005 (mapper không object) | BLOCKER |
| 8 | ARCH-013 (!! trong mapper) | BLOCKER |

## Scoring

- 8/8: 100
- 7/8: 90
- 6/8: 75 (threshold pass)
- 5/8: 50
- < 5: FAIL

Trừ điểm nếu:
- Finding thiếu file + line
- Severity sai
- Fix suggestion vague
- Nitpick LOW che BLOCKER

## Baseline

Không harness: thường 2–4/8. Có harness: target ≥ 6/8.

## Customization

Product overlay thay `LibraryViewModel`, `LibraryRepositoryImpl`, `LibraryMapper` bằng naming thực. Giữ structure 8 bug để scoring consistent.
