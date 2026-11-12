# Worker protocol (one bug → one PR)

Run every step in order. `Q` = `python3 <SKILL_DIR>/scripts/bug_queue.py` (absolute path from your prompt).
Verify levels (`none` / `unit` / `preview` / `device`) and the `preview` rule: `verify-tiers.md`.
`WT` = your worktree path. Run `Q` from inside the repo or `WT` (it finds the shared queue).
Never touch the main checkout's files or branch. Never merge or force-push.

## 1. Worktree

```bash
cd <repo root> && git fetch <remote> main
WT=<repo root>-worktrees/<bug-id-lower>          # e.g. ../AIP699-ShortDrama-worktrees/bug-007
BRANCH=fix/<bug-id-lower>-<short-kebab-slug>
git worktree add "$WT" -b "$BRANCH" <remote>/main
```
Copy gitignored build inputs the build needs from the main checkout (only those that exist):
`local.properties`, `.env`, `keystore.properties`, `google-services.json` if ignored. Never commit them.
`Q set <id> status=investigating branch=$BRANCH worktree=$WT`

## 2. Investigate (read-only) — fast-fix first

Speed beats ceremony: the user tests on device later in one pass. Find the cause **from the code**
first; touch the device only when the code alone cannot prove the cause.

- Scout the code for the screen/feature named in the report; read project rules first.
- Prove the root cause as **file:line + why** (quote the wrong line). This is mandatory for every bug.
- Pick **one verify level** from `verify-tiers.md` (record it in report.md, evidence.json and the PR):

| Level | When | Before/after evidence | Device |
|---|---|---|---|
| `none` | Obvious code/resource bug whose wrong → right is visible in the diff (wrong value/condition/missing call, text, dimen) | file:line before → after; compile (+ resource lint) | **No** e2e |
| `unit` | Logic in ViewModel/UseCase/repository/mapper, or a navigation/flow sequence that is wrong | The exact wrong line(s) and, for flows, the call chain (A.kt:12 → B.kt:40); regression unit test (happy + ≥ 1 edge) | **No** e2e |
| `preview` | Bug visible on a screen that has (or can get) an `@Preview` | The `preview` rule in `verify-tiers.md`: Figma ref from `docs/design-refs/figma-refs.json`, render before/after, `compare-ui-board` board, `ui-diff-review` threshold 95, still differs → `ui-fix-loop` ≤ 3 rounds | **No** e2e |
| `device` | Needs real conditions (player/SDK, ads, billing, permissions, lifecycle, timing, network) | Fix by code reasoning + unit tests where possible | **Deferred**: add to the device-test queue (step 7), do not run now |

- Device repro is allowed only if the cause cannot be proven from code (then take the lock as below,
  one short repro, then `Q device-unlock <serial> <id>`). Device lock: run `Q device-lock <serial> <id>`
  as a **standalone command** and read its exit code before any adb/gradle-install call. Never chain it
  with `&&`/`;`. Exit 3 → the device is busy (the script marks you `waiting` on the holder): touch
  nothing on the device, do not poll, report `WAITING` with `Blocked by: <holder> (device <serial>)`
  (`<holder>` is a bug id, or `batch:<id>:<JOB>` when a batch job holds the serial; the lock is shared with
  batch mode). You are resumed when the holder finishes; then run the lock command again.
- If the cause cannot be proven from code or a short repro, stop with `NEEDS_INPUT` and the exact
  question.

## 3. Plan the fix

Apply **Chuẩn fix** from `agents/bug-fixer.md`: read the project rules for the area, write
`<evidence dir>/fix-design.md` (root-cause layer, where the fix goes and why, root fix vs local patch
considered, callers affected, pattern followed), never use a pattern from its "Cấm fix ngọn" table.
List every file you expect to change (repo-relative). Keep scope to what the root cause needs, at the
right layer. If the root fix needs a contract change, a migration or a large refactor, stop with
`NEEDS_INPUT` and the design note instead of patching.

## 4. Claim files

`Q claim <id> <file> ...`
- exit 0 → base stays `main`; go to 5.
- exit 3 (WAIT) → do not edit anything. Report status `WAITING` with the blocker id and stop.
  When resumed ("blocker PR open on <branch>"), run step 4 again.
- exit 4 (STACK, `stack_on=<branch>`) → rebase your start point onto that branch:
  `git -C "$WT" fetch <remote> <branch> && git -C "$WT" reset --hard <remote>/<branch>`
  (safe: nothing edited yet). `Q set <id> base=<branch>`. PR base becomes that branch.

## 5. Fix

- Edit only in `WT`. Follow the repo's architecture, style and resource rules.
- If you must touch a file not claimed, run step 4 again with the full list **before** editing it.
  If that now returns WAIT, save your edits as a WIP commit on your own branch
  (`git -C "$WT" add <edited files> && git -C "$WT" commit -m "wip: <id>"`) and report `WAITING`.
  Never use `git stash`: the stash stack is shared by every worktree of the repo, so parallel workers
  could pop each other's changes. On resume after a stack reset, `git -C "$WT" cherry-pick <wip sha>`
  (before the reset, note the sha with `git -C "$WT" rev-parse HEAD`); squash the WIP commit into the
  real fix commit before pushing.

## 6. Verify — one round only (`preview` excepted)

Budget: once the cause is found and fixed, verify **once** and move on. The exception is `preview`: it keeps
going through `ui-fix-loop` (≤ 3 fix rounds per bug, `verify-tiers.md`) while the score is under the threshold.

- Always: compile with the repo's command + the narrowest relevant unit test (new or existing).
  Run the full module test suite only if the change touched shared code (DI, base classes,
  navigation, repositories).
- `preview`: the `preview` rule in `verify-tiers.md` (render after the fix, board, `ui-diff-review`; score under
  the threshold → `ui-fix-loop`, max 3 rounds; still under after round 3 → `NEEDS_INPUT` with the board and the
  remaining findings, do not open the PR as passing).
- `none` / `unit`: no device. `device`: no device now (deferred, step 7).
- If compile/test fails, fix it (never weaken or skip tests). 3 failed fix attempts → `FAILED`.
- Outside `preview`, do not loop on polish, extra screenshots or repeated runs.

## 7. Evidence

Write `<evidence dir>/report.md` (Vietnamese, short):
- Bug id (+ Jira key if any), title, reported text, **verify level** (`none` / `unit` / `preview` / `device`)
- Root cause: file:line + the wrong line quoted + why (for a flow bug also the call chain)
- Fix (files, what changed)
- Verification actually run (commands + results; preview, board and `ui-diff-review` result paths and rounds for `preview`)
- **Chưa test trên thiết bị** + the manual test steps the user should run later (every level)
- PR link (fill after step 8)
Redact tokens, emails, phone numbers before writing.

Then write `<evidence dir>/evidence.json` per `skills/bug/schemas/evidence.schema.json` (same schema batch mode
uses): `issue` = bug id, `commit` = the base commit your branch started from (`git -C "$WT" merge-base HEAD
<base>` / the stack base tip), `fix_commit` = the fix sha (fill after the commit), `verdict` (`PASS` when the
level's evidence ran and passed; `device` level stays `NEEDS_VERIFICATION` until the manual device pass),
`bug_type`, `verification` (`compile`, `unit`, `preview`, `device`: PASS/FAIL/SKIP), `artifacts` (paths relative
to the evidence dir: `report.md`, `fix-design.md`, `self-review.md`, plus `preview-before.png`,
`preview-after.png`, `board.png` for `preview`; the call chain lives in `report.md`), and
`acceptance_criteria` (each expected behaviour → `result` + an `evidence` artifact that exists). No artifact, no
`PASS`. Check it before the commit:
`python3 <harness>/skills/bug/scripts/validate_evidence.py --evidence-dir <evidence dir>` (`<harness>` = absolute
path in your prompt; `NEEDS_VERIFICATION` for `device` is expected, anything else must pass).

**Device-test queue** (every bug, append-only, one block per bug) at
`<repo root>/plans/reports/bugs/DEVICE-TEST-QUEUE.md` (create with a `# Hàng chờ test thiết bị`
title if missing; append with `>>`, never rewrite other blocks):

```
## <BUG-ID> — <title>   (PR: <url>)   Level: <level>
- [ ] <manual step 1 → expected result>
- [ ] <manual step 2 → expected result>
Điều kiện đặc biệt: <for `device`: device/ads/billing/permission/network conditions; else "-">
```

## 8. Commit, push, PR

```bash
cd "$WT"
git add <only the changed source/test files>          # never git add -A
git diff --cached | grep -iE '^\+.*(api[_-]?key|secret|password|token)' && echo STOP
git commit -m "fix(<scope>): <what is fixed, imperative>"   # no AI references, no BUG id in code
git push -u <remote> "$BRANCH"
gh pr create --base <main or stacked base> --head "$BRANCH" --draft \
  --title "fix(<scope>): <summary>" --body-file <tmp body file>
```
PR body (Vietnamese): bug report quote · **Verify level** · root cause (file:line, wrong line quoted)
· fix · verification actually run · a section **"⚠️ Chưa test trên thiết bị — cần test tay"** with
the manual checklist (same as the device-test queue block; for `device` also the special
conditions) · "Evidence (local): <evidence dir>" · if stacked: "Stacked on #<pr> — merge that first".
Add the GitHub label `needs-device-test` (`gh pr edit --add-label`; if the label does not exist,
create it once with `gh label create needs-device-test`; if that fails, skip the label — the PR
section is enough).
Before the commit, go through the A–J checklist of `skills/coding-review/SKILL.md` for your diff and
write `<evidence dir>/self-review.md`. The PR stays **draft**: the orchestrator marks it ready only after
`bug-reviewer` approves. If it sends review findings, fix them in the same worktree, update
`fix-design.md`/`self-review.md`, push, and report `DONE` again (max 2 rounds).
Then `Q set <id> status=pr_open pr=<url>` and add the PR link to report.md.

## 9. Clean up

Keep the worktree: the reviewer reads it and review fixes happen there (`status` → `sync-merged`
removes it after the PR merges). Stop only processes you started (emulator stays).

## Final status block (last lines of your reply)

```
Status: DONE | WAITING | NEEDS_INPUT | FAILED
Bug: <id> — <title>
Level: <none | unit | preview | device>   Device test: deferred (DEVICE-TEST-QUEUE.md)
PR: <url or ->            Base: <main | stacked branch>
Blocked by: <id or ->     Root cause: <one sentence>
Evidence: <evidence dir>
Question: <only for NEEDS_INPUT>
```
