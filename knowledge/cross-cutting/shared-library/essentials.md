# Shared Library — Essentials

Kiến thức nền cho **KMP/Android library ở repo riêng + publish artifact**, dùng chung giữa nhiều product.

Consume bởi: `library-architect`, `architect` (khi plan module layout lib), `coder` (khi impl), `reviewer` (API/code review), `qa` (matrix test).

> **Đọc kèm bắt buộc trước khi dùng checklist này**: `sdk-mindset.md` (ADR SDK-001..006). File `essentials.md` là **rule checklist cứng**; `sdk-mindset.md` là **triết lý quyết định** trước khi mở checklist. Thiếu mindset mà apply checklist → feature-first drift.
>
> **Phase 0 Brainstorm trước Stage 3 Contract**: xem `brainstorm-process.md`. Không skip.

## 13 nhóm tiêu chí

### LIB-SCOPE-001..003 — Boundary & responsibility

**LIB-SCOPE-001**: 1 lib = 1 trách nhiệm. Responsibility viết được trong 1 câu không có từ "và". Có "và" → tách.

**LIB-SCOPE-002**: Cấm leak concept product-specific vào public API. Tên class, field, resource không được chứa tên product/feature cụ thể.

**LIB-SCOPE-003**: Phân loại rõ 3 flavor, mỗi flavor constraint khác:
- KMP-common pure: logic 100% commonMain, không SDK platform
- Platform-only (Android/iOS): dùng SDK platform, không expect/actual
- expect/actual bridge: logic common, 1-2 call platform-specific

### LIB-API-001..006 — API contract & versioning

**LIB-API-001**: SemVer bắt buộc. Start từ `0.1.0`. `0.x` cho phép breaking tự do (vẫn CHANGELOG). `>= 1.0` MAJOR = binary breaking.

**LIB-API-002**: Public API tối thiểu. Mọi thứ không cần expose → `internal`. Enforce qua Kotlin `explicitApi()` mode.

**LIB-API-003**: Binary compat gate: `binary-compatibility-validator` plugin (Kotlin BCV). API dump file `api/<module>.api` committed vào git. CI `./gradlew apiCheck` phải pass. Breaking → `apiDump` + bump MAJOR.

**LIB-API-004**: Deprecation window: `@Deprecated(level = WARNING)` 1 minor → `ERROR` 1 minor → remove ở MAJOR kế. Mỗi `@Deprecated` phải có `replaceWith` nếu có thay thế.

**LIB-API-005**: Experimental API phải annotate `@RequiresOptIn` để consumer biết signal "chưa stable". Ví dụ `@ExperimentalMyLibApi`.

**LIB-API-006**: `data class` trong public API chỉ expose khi: không bao giờ thêm field (hoặc chấp nhận bump MAJOR mỗi lần thêm). Thường ưu tiên interface + factory function.

### LIB-CONFIG-001..005 — Per-project configurability

**LIB-CONFIG-001**: Config qua Builder/DSL hoặc Config object immutable, **không** qua `object SingletonLib.init()` trừ khi lib buộc phải là singleton (crash handler, process-wide listener).

**LIB-CONFIG-002**: Config field có default khi lib vẫn vận hành được không set. Required chỉ khi lib không có cách default an toàn (ví dụ `apiKey`). Required không default → fail-fast với error message chỉ ra fix cụ thể.

**LIB-CONFIG-003**: Feature toggle default = tắt. Consumer explicit opt-in. Lý do: thêm feature mới sau không được bật-mặc-định phá consumer.

**LIB-CONFIG-004**: DI-agnostic. Lib không được bind cứng Koin/Hilt/Dagger. Expose factory function + interface. Consumer tự wire vào DI framework của họ.

**LIB-CONFIG-005**: Config matrix per-consumer document trong `config-matrix.md`. Mỗi field × mỗi consumer rõ ràng. Giúp phát hiện "field này chỉ 1 consumer cần" → có thể move về consumer-side.

### LIB-PORT-001..004 — Side-effect ports injection

Mọi side-effect lib dùng phải expose port cho consumer inject:

**LIB-PORT-001**: `Logger` interface. Default `NoopLogger`. Consumer có thể wrap Timber/Napier/println.

**LIB-PORT-002**: `AnalyticsPort` interface (nếu lib muốn emit event). Default `NoopAnalytics`. Consumer wrap Firebase/Mixpanel/custom.

**LIB-PORT-003**: `Clock` interface. Default `SystemClock`. Giúp test determistic + consumer dùng custom clock (NTP sync).

**LIB-PORT-004**: `CoroutineDispatcher` + `HttpClient` inject khi lib async/network. Dispatcher default `Dispatchers.Default`. HttpClient không default (yêu cầu consumer provide hoặc lib pin version Ktor engine).

Lý do: không hardcode = test isolate được, consumer control hoàn toàn observability.

### LIB-DEP-001..005 — Dependency hygiene

**LIB-DEP-001**: `implementation(...)` mặc định. `api(...)` **chỉ** khi type xuất hiện trong public signature (return/param/super). Nghi ngờ → `implementation`.

**LIB-DEP-002**: Zero transitive leak: consumer thêm `implementation(libs.myLib)` không được bất ngờ nhận các transitive dep nặng. Verify qua `./gradlew dependencies`.

**LIB-DEP-003**: Pin version qua `libs.versions.toml` nội bộ lib repo. Không depend vào catalog của consumer.

**LIB-DEP-004**: Cấm `concrete framework` của consumer-side. Ví dụ lib không-UI không được `import androidx.compose.*`. Lib không-DI không được `import org.koin.*`.

**LIB-DEP-005**: Dep nặng (Firebase, Retrofit, OkHttp) phải justify trong `library-contract.md §Dependency policy`. Ưu tiên: để consumer inject (`HttpClient` port) thay vì lib pin.

### LIB-PLATFORM-001..004 — Platform & compat matrix

**LIB-PLATFORM-001**: Khai báo rõ trong README + contract: `kotlin >= X.Y`, Android `minSdk / compileSdk / targetSdk`, iOS deployment target (nếu có).

**LIB-PLATFORM-002**: Hỗ trợ **2 version thấp hơn** của Kotlin/AGP so với latest trừ khi có lý do mạnh (dùng feature mới). Document reason trong CHANGELOG khi bump floor.

**LIB-PLATFORM-003**: KMP target set tối thiểu: common + android. Thêm iOS nếu ≥ 1 consumer là KMP app. Thêm JVM/JS chỉ khi có use case thực.

**LIB-PLATFORM-004**: Test matrix CI: min version Kotlin + max version. Build + unit test cả hai. Fail bất kỳ → block release.

### LIB-RES-001..003 — Resource & namespace (Android)

**LIB-RES-001**: `android.namespace = "<group-id>.<artifact>"`. Không trùng namespace consumer.

**LIB-RES-002**: Resource prefix: `lib_<name>_` cho string, drawable, color, dimen. Enforce qua `android { resourcePrefix "lib_myname_" }`.

**LIB-RES-003**: `consumer-rules.pro` ship cùng artifact chứa R8/ProGuard rules cần giữ cho lib. Không yêu cầu consumer viết lại.

### LIB-ERROR-001..003 — Error handling contract

**LIB-ERROR-001**: Operation có-thể-fail do input/network/state → trả `Result<T>` hoặc sealed `Outcome<T, E>`. Không throw unchecked bừa.

**LIB-ERROR-002**: Exception được phép escape phải document trong KDoc + contract: `@throws IllegalArgumentException` khi config sai (bug caller), hoặc `@throws CancellationException` cho suspend.

**LIB-ERROR-003**: Mỗi public API document rõ thread-safety: `main-safe` / `blocking` / `suspend` / `thread-confined`. Suspend function nội bộ tự `withContext(dispatcher)` khi I/O, consumer không cần tự switch.

### LIB-TEST-001..003 — Testability

**LIB-TEST-001**: Unit test chạy không cần Android instrumentation. Robolectric chỉ khi test code Android SDK-specific (SharedPreferences, Context).

**LIB-TEST-002**: Public API phải có `fake` / testdouble ship kèm (module `test-utils` hoặc `-testing` artifact): `FakeLogger`, `FakeAnalytics`, `InMemoryXRepository`. Consumer dùng để test code của họ.

**LIB-TEST-003**: Coverage touched: happy path + ≥ 2 edge case per public API. Không enforce số % toàn module cứng; enforce "mỗi public API có test".

### LIB-DOC-001..004 — Documentation

**LIB-DOC-001**: `README.md` phải có: install (1 dòng gradle + 1 dòng catalog), quickstart ≤ 20 dòng chạy được, config matrix pointer, migration note cho major mới nhất.

**LIB-DOC-002**: `CHANGELOG.md` theo Keep-a-Changelog + SemVer. Mỗi entry phân loại: Added / Changed / Deprecated / Removed / Fixed / Security.

**LIB-DOC-003**: KDoc cho mọi public symbol. `@sample` link vào `samples/` module.

**LIB-DOC-004**: `samples/` module gradle sub-module chạy được. Mỗi major use-case 1 sample. Giúp consumer onboard < 5 phút.

### LIB-PUBLISH-001..005 — Publishing

**LIB-PUBLISH-001**: Group ID + artifact ID lock từ `0.1.0`. Đổi = tạo lib mới + migration cost N consumer.

**LIB-PUBLISH-002**: Repository: Maven Central (public) hoặc internal Nexus/Artifactory (private). GitHub Packages chỉ cho internal.

**LIB-PUBLISH-003**: Signing GPG bắt buộc cho Maven Central. Sigstore acceptable alternative. Internal repo tùy policy.

**LIB-PUBLISH-004**: Snapshot repo riêng cho `-SNAPSHOT` version. Release repo immutable (không override).

**LIB-PUBLISH-005**: CI publish pipeline: tag `vX.Y.Z` trigger → `./gradlew publish` → verify artifact resolve từ external repo trong smoke step. Tag match version trong `gradle.properties`.

### LIB-PATTERN-001..006 — Design patterns bắt buộc

Những pattern này không optional — chúng cover case thường gặp khi lib có ≥ 2 consumer và cần extensible. Library Architect verify trong Stage 3 (Contract design).

**LIB-PATTERN-001 — Strategy**: algorithm có nhiều variant phải expose qua interface, consumer swap impl runtime. Áp dụng cho: `CacheStrategy` (LRU/LFU/TTL), `RetryPolicy` (exponential/linear/none), `BackoffPolicy`, `SerializationStrategy`, `TokenRefreshStrategy`. Lib ship 2-3 default impl + cho consumer tự viết. Cấm: hardcode 1 algorithm "vì team hiện chỉ cần vậy".

**LIB-PATTERN-002 — Chain of Responsibility**: pipeline xử lý (network request, event dispatch, auth token flow) phải expose `Interceptor` interface + builder để consumer thêm/xóa chain. Order mặc định ship kèm (ví dụ auth → log → retry → actual call). Consumer có thể insert interceptor custom giữa chain. Cấm: fix chain cứng.

**LIB-PATTERN-003 — Observer qua Kotlin Flow**: event stream (auth state change, cache invalidate, download progress, config refresh) expose `Flow<Event>` — hot `StateFlow`/`SharedFlow` cho state hiện tại, cold `Flow` cho stream một chiều. Không dùng listener callback (`setListener(...)`) trừ khi tương tác Java interop bắt buộc. Lý do: Flow tự handle cancellation, backpressure, multi-subscriber.

**LIB-PATTERN-004 — Facade**: mỗi lib có **1 entry point** rõ ràng (ví dụ `MyLib.Builder()`, hoặc `createMyLib(config)` factory). Consumer import duy nhất entry point này; internal class không được public. Facade che complexity của N class internal. Verify: consumer `import` không bao giờ chạm sâu hơn 1 package.

**LIB-PATTERN-005 — Decorator**: khi lib ship base impl + optional cross-cutting concern (log, cache, metric, retry), expose base + decorator function thay vì nhồi flag vào Config. Ví dụ: `createClient().withLogging().withCache(policy)`. Lý do: config flag combinatorial explode, decorator compose rõ hơn + consumer tự extend.

**LIB-PATTERN-006 — Adapter helper modules**: khi consumer phổ biến dùng 3rd-party (Firebase, Timber, Napier, OkHttp, Mixpanel) wrap qua port, ship **adapter module optional** `<lib>-firebase`, `<lib>-timber`, `<lib>-okhttp` để consumer onboard < 5 dòng. Core lib **không** depend adapter module (consumer opt-in). Lý do: lib core sạch dep nhưng consumer vẫn integrate nhanh.

### LIB-GOV-001..004 — Governance

**LIB-GOV-001**: Breaking change `>= 1.0` yêu cầu RFC file `rfcs/<id>-<slug>.md` + ≥ 2 consumer sign-off (hoặc 1 consumer nếu lib chỉ 2 consumer total).

**LIB-GOV-002**: Pre-release channel `-alpha.N`, `-beta.N` cho API chưa stable. Consumer đồng ý thử trước stable.

**LIB-GOV-003**: CI gate PR: BCV `apiCheck`, API dump diff visible, dep diff visible, artifact size diff (AAR/klib) visible.

**LIB-GOV-004**: Steward 1 người chịu trách nhiệm final approve RFC + release. Thường là Library Architect kiêm.

## Quick decision table

| Tình huống | Rule |
|---|---|
| Chỉ 1 consumer | Không tạo lib, giữ ở product (LIB-SCOPE-001 trigger) |
| 2 consumer, boundary chưa chắc | Dùng monorepo shared module trước, extract sau khi ổn định |
| ≥ 2 consumer + boundary ổn định | Tạo lib riêng |
| Consumer muốn config khác nhau | Config matrix, không hardcode (LIB-CONFIG-005) |
| Breaking change đã `1.0` | RFC + sign-off (LIB-GOV-001) |
| Thêm field vào data class public | Bump MAJOR hoặc đổi sang interface + factory (LIB-API-006) |
| Lib cần log/analytics | Inject port, default no-op (LIB-PORT-001..002) |
| Lib Android dùng Context | KMP common không được, chỉ androidMain (LIB-SCOPE-003) |
| Lib có N algorithm (cache, retry, backoff) | Strategy interface, không hardcode (LIB-PATTERN-001) |
| Lib có pipeline (network, event dispatch) | Interceptor chain, consumer extend được (LIB-PATTERN-002) |
| Lib emit event cho consumer subscribe | `Flow<T>` thay listener callback (LIB-PATTERN-003) |
| Lib wrap 3rd-party (Firebase, Timber) | Ship adapter module optional `<lib>-firebase` (LIB-PATTERN-006) |

## Anti-patterns

- `object Lib { fun init(context) }` singleton + global state → không test, không multi-instance
- `data class PublicConfig(val a, val b)` không freeze field → thêm field = binary break
- `api(libs.firebase)` không có lý do → leak transitive, consumer bắt buộc nhận Firebase
- Resource không prefix → merge conflict với consumer `strings.xml`
- "Sẽ có consumer thứ 2 sau" → vi phạm trigger check, giữ monorepo
- Breaking change ship thẳng không `@Deprecated` giai đoạn → consumer bị force migrate ngay
- Public API dùng `Context` cho logic pure → không reusable cho KMP consumer
- Config required không có error message helpful → consumer debug mò giờ đầu
- Hardcode cache/retry/serialization algorithm → consumer bị khóa, vi phạm LIB-PATTERN-001
- Fix interceptor chain cứng → consumer không insert được auth/log custom, vi phạm LIB-PATTERN-002
- Expose `setListener(cb)` thay vì `events: Flow<T>` → leak callback, không cancel được, vi phạm LIB-PATTERN-003
- Lib core depend trực tiếp Firebase/Timber thay vì ship adapter module optional → consumer bị force transitive, vi phạm LIB-PATTERN-006

## Pair với

### SDK-level knowledge (bắt buộc đọc)

- `sdk-mindset.md` — ADR SDK-001..006: SDK ≠ feature module, 3 guarantee (Stability/Configurability/Extensibility), anti-pattern cấm
- `pattern-catalog.md` — design pattern canonical mapping cho mỗi SDK component (Facade/Builder/Strategy/Chain/Observer/Spec/Null Object/...)
- `layered-architecture.md` — 5-layer kernel-plugin model (L0-L4), rule bất biến, 3 SPI mandatory
- `brainstorm-process.md` — 10-step top-down Phase 0 trước Contract design, use case matrix 3-axis, straw-man persona rule
- `testing-kit-rules.md` — artifact `:lib-testing` mandatory, fake/driver/assertion spec

### Agent & workflow

- Agent: `library-architect.md`
- Workflow: `agents/workflows/library-flow.md`
- Skill: `skills/library-new/SKILL.md`, `skills/library-extract/SKILL.md`

### Cross-cutting knowledge

- `knowledge/coding/clean-arch/architecture-profiles.md`
- `knowledge/cross-cutting/build-strategy/essentials.md`
- `knowledge/cross-cutting/security/essentials.md` (khi lib handle credential)
