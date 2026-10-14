# Blueprint: Compose Screen (Standalone)

Standalone pattern cho 1 Compose screen (route + content split) **không cần** full feature stack. Dùng khi:
- Screen hiển thị data đã có (ví dụ Settings, Legal, About)
- Prototype UI chưa wire ViewModel
- Composable reusable cross-feature

Nếu screen có remote data + MVI contract đầy đủ → dùng `reference-feature` blueprint thay vì file này.

## Layout

```
{{MODULE_PRESENTER}}/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/{{MODULE_PRESENTER}}/screen/<name>/
├── <Name>Api.kt            ← public route entry (optional)
├── <Name>Screen.kt         ← route (stateful) + content (stateless)
└── components/             ← private sub-composables (nếu > 3)
```

## 1. Public API (optional)

```kotlin
// SettingsApi.kt
@Composable
fun SettingsRoute(
    onBack: () -> Unit,
    onNavigate: (NavRoute) -> Unit,
) {
    SettingsScreen(onBack = onBack, onNavigate = onNavigate)
}
```

## 2. Route + Content

```kotlin
// SettingsScreen.kt
@Composable
internal fun SettingsScreen(
    onBack: () -> Unit,
    onNavigate: (NavRoute) -> Unit,
    viewModel: SettingsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                SettingsEffect.Back -> onBack()
                is SettingsEffect.Navigate -> onNavigate(effect.route)
            }
        }
    }
    SettingsContent(state = state, onIntent = viewModel::onIntent)
}

@Composable
private fun SettingsContent(
    state: SettingsState,
    onIntent: (SettingsIntent) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxSize()) {
        TopAppRow(
            title = stringResource(Res.string.settings_title),
            onBack = { onIntent(SettingsIntent.Back) },
        )
        SettingsItem(
            label = stringResource(Res.string.settings_theme),
            value = state.theme.displayName(),
            onClick = { onIntent(SettingsIntent.ToggleTheme) },
        )
        SettingsItem(
            label = stringResource(Res.string.settings_language),
            value = state.locale.displayName(),
            onClick = { onIntent(SettingsIntent.OpenLanguage) },
        )
    }
}
```

## 3. Preview đủ states critical

```kotlin
@Preview
@Composable
private fun SettingsContentPreview() {
    AppTheme {
        SettingsContent(
            state = SettingsState(theme = Theme.Light, locale = AppLocale.VI),
            onIntent = {},
        )
    }
}

@Preview
@Composable
private fun SettingsContentDarkPreview() {
    AppTheme(darkTheme = true) {
        SettingsContent(
            state = SettingsState(theme = Theme.Dark, locale = AppLocale.EN),
            onIntent = {},
        )
    }
}
```

## Checklist

- [ ] Stateful route (ViewModel + collect) separate khỏi stateless content
- [ ] `collectAsStateWithLifecycle()` không raw `collectAsState()`
- [ ] Content composable `internal`/`private`, nhận state + callback param
- [ ] Content composable không reference ViewModel direct
- [ ] Design token (`{{THEME_CLASS}}.colors/spacing/typography`), không hardcode
- [ ] `contentDescription` cho icon-only interactive
- [ ] Preview ≥ 2 state critical (success + 1 edge, hoặc light + dark)
- [ ] Preview wrap `{{THEME_CLASS}} { }`
- [ ] 5 UI state coverage (loading/empty/error/offline/success) nếu có remote data

## Variants

- Screen đơn giản không ViewModel → route composable không có `viewModel = koinViewModel()` param
- Screen có bottom sheet / dialog → modal nằm trong route composable, không trong content
- Screen trong nested nav → route expose `navController: NavController` thay `onNavigate: (NavRoute) -> Unit`

## Relation với reference-feature blueprint

| Pattern | Use |
|---|---|
| **compose-screen** (này) | 1 screen, ít state, không remote data cross-cutting |
| **reference-feature** | Full feature stack: domain + data + presenter + MVI contract đầy đủ |

Nếu feature expand (thêm Repository, UseCase, remote fetch) → upgrade sang `reference-feature` pattern.

## Reference

- `.harness/skills/android-compose/SKILL.md`
- `.harness/knowledge/compose/essentials.md`
- `.harness/blueprints/reference-feature/README.md`
