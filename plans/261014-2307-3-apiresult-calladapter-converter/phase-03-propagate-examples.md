# Phase 3 — Propagate contract to docs, skills, blueprints

Rule for every repository example below: remove `ioDispatcher` ctor param + `: BaseRepository(ioDispatcher)`; replace `apiCall { ... }` with an `ApiResult` chain on API calls (`api.x().map { it.toDomain() }`, `.onSuccess { local... }`, `.flatMap { ... }`). API examples return `ApiResult<Dto>` (Ktor examples use `client.safeRequest<T> { ... }`). DI bindings drop `get(named("io"))` where the repository no longer takes a dispatcher. Local sources that run blocking SQLDelight queries keep/receive `withContext(ioDispatcher)` themselves.

## Task 3.1 — knowledge
- `knowledge/data/repository-pattern.md`: Rules line 12, Impl pattern 39-58, offline-first 85, Error handling 121-135 (point to `ErrorMapper` in network.md), Testing (ctor without dispatcher; fake API returns `ApiResult`).
- `knowledge/data/caching.md`: 109, 124, 162, TTL snippet.
- `knowledge/coroutines/essentials.md`: Dispatcher strategy 22-34 (no BaseRepository; show local source `withContext` for blocking IO), references 213.

## Task 3.2 — skills
- `skills/android-database/SKILL.md` 204-227; `skills/android-feature/SKILL.md` 80, 100; `skills/android-coroutines/SKILL.md` 29; `skills/android-code-review/SKILL.md` 91; `skills/android-testing/SKILL.md` ~166 (ctor without dispatcher, API returns ApiResult).

## Task 3.3 — blueprints
- `blueprints/repository/README.md` (api section, repo impl 140-165, DI 182, checklist 217).
- `blueprints/network-service/README.md` (API 40-70 → safeRequest, repo 100-121, DI 141, checklist 216).
- `blueprints/reference-feature/README.md` (repo 200-215, DI 221; CatalogApi if shown).

## Task 3.4 — agents/workflows
- `agents/implementer.md:45`, `workflows/feature-development.md:100`, `workflows/review-pull-request.md:85`.

## Verify (phase)
```bash
grep -rn "BaseRepository\|apiCall" constitution knowledge skills blueprints agents workflows evaluations verification | grep -v -i "migration"
```
Pass: no output. And `grep -rn "named(\"io\")" blueprints` prints only bindings whose constructor still takes a dispatcher (local source).

## Failure Protocol
If any Verify step does not meet its stated pass condition, STOP this phase.
Do not improvise a fix, retry blindly, or reason around the failure.
Spawn the `kongming` subagent for next-step counsel and pass:
- the phase and task id,
- what you attempted (the steps you ran),
- the exact command and its full output,
- the pass condition it failed to meet.
Apply kongming's guidance, then re-run the Verify step.
If `kongming` cannot be spawned in this environment, STOP and report the same
failure evidence to the user. Never continue by self-reasoning.
