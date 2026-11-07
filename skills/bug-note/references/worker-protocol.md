# Worker protocol (one bug → one PR)

Run every step in order. `Q` = `python3 ~/.claude/skills/bug-note/scripts/bug_queue.py`.
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
- Classify the bug into **one verify tier** (record it in report.md and the PR):

| Tier | When | Before/after evidence | Device |
|---|---|---|---|
| `T1-code` | Obvious code bug (wrong value/condition/missing call, visible in code) | file:line before → after; compile + the narrowest unit test if one exists | **No** e2e |
| `T2-ui` | Bug visible on a screen that has (or can get) an `@Preview` | Render the preview (`android preview render ":app@appDevDebug" --fqn=…`) before/after, put it next to the Figma image with skill `compare-ui-board`, then score with skill `ui-diff-review` (threshold 95). Do not use `ui-diff`: it only compares a screen recording with Figma | **No** e2e |
| `T3-flow` | Navigation/flow/logic sequence wrong | Point the exact wrong line(s) and the call chain (A.kt:12 → B.kt:40); unit test the ViewModel/effect if cheap | **No** e2e |
| `T4-device` | Needs real conditions (player/SDK, ads, billing, permissions, lifecycle, timing, network) | Fix by code reasoning + unit tests where possible | **Deferred**: add to the device-test queue (step 7), do not run now |

- Device repro is allowed only if the cause cannot be proven from code (then take the lock as below,
  one short repro, then `Q device-unlock <serial> <id>`). Device lock: run `Q device-lock <serial> <id>`
  as a **standalone command** and read its exit code before any adb/gradle-install call. Never chain it
  with `&&`/`;`. Exit 3 → the device is busy (the script marks you `waiting` on the holder): touch
  nothing on the device, do not poll, report `WAITING` with `Blocked by: <holder id> (device <serial>)`.
  You are resumed when the holder finishes; then run the lock command again.
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

## 6. Verify — one round only

Budget: once the cause is found and fixed, verify **once** and move on.

- Always: compile with the repo's command + the narrowest relevant unit test (new or existing).
  Run the full module test suite only if the change touched shared code (DI, base classes,
  navigation, repositories).
- `T2-ui`: one preview render after the fix + one `compare-ui-board` board scored by `ui-diff-review`.
- `T1-code` / `T3-flow`: no device. `T4-device`: no device now (deferred, step 7).
- If compile/test fails, fix it (never weaken or skip tests). 3 failed fix attempts → `FAILED`.
- Do not loop on polish, extra screenshots or repeated runs.

## 7. Evidence

Write `<evidence dir>/report.md` (Vietnamese, short):
- Bug id, title, reported text, **verify tier** (`T1-code` / `T2-ui` / `T3-flow` / `T4-device`)
- Root cause: file:line + the wrong line quoted + why (for `T3-flow` also the call chain)
- Fix (files, what changed)
- Verification actually run (commands + results; preview, board and `ui-diff-review` result paths for `T2-ui`)
- **Chưa test trên thiết bị** + the manual test steps the user should run later (every tier)
- PR link (fill after step 8)
Redact tokens, emails, phone numbers before writing.

**Device-test queue** (every bug, append-only, one block per bug) at
`<repo root>/plans/reports/bugs/DEVICE-TEST-QUEUE.md` (create with a `# Hàng chờ test thiết bị`
title if missing; append with `>>`, never rewrite other blocks):

```
## <BUG-ID> — <title>   (PR: <url>)   Tier: <tier>
- [ ] <manual step 1 → expected result>
- [ ] <manual step 2 → expected result>
Điều kiện đặc biệt: <for T4-device: device/ads/billing/permission/network conditions; else "-">
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
PR body (Vietnamese): bug report quote · **Verify tier** · root cause (file:line, wrong line quoted)
· fix · verification actually run · a section **"⚠️ Chưa test trên thiết bị — cần test tay"** with
the manual checklist (same as the device-test queue block; for `T4-device` also the special
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
Tier: <T1-code | T2-ui | T3-flow | T4-device>   Device test: deferred (DEVICE-TEST-QUEUE.md)
PR: <url or ->            Base: <main | stacked branch>
Blocked by: <id or ->     Root cause: <one sentence>
Evidence: <evidence dir>
Question: <only for NEEDS_INPUT>
```
