# Manifest and review contract

## Manifest

Use JSON with `schema_version: 1`, `feature`, a Gradle `target`, optional `references`, and nonempty `cases`.

- References: objects with stable `id`, `path` (relative to manifest or absolute), and `kind` (`design` or `spec`). Each must be a local file. Export/download through an authorized tool first. Include frame/version in requirements. The runner copies and hashes reference bytes.
- Case `id`: lowercase letters/digits/hyphens/underscores, unique.
- `fqn`: discovered fully-qualified function, unique per case. Use separate functions for different fixtures/configurations.
- `expected_images`: positive integer; exactly this many PNGs and at least this many nonempty JSON companion files must be emitted. Inspect JSON and variant mapping; do not assume undocumented fields.
- `review_kind`: `requirements` or `design`. Design cases require a referenced design file. Requirements review does not establish Figma parity.
- `reference_ids`: reference IDs that must be reviewed for the case.
- `configuration_note`: viewport/locale/fixture to verify in source; descriptive, not renderer flags.
- `requirements`: nonempty list of `{id, text}`, unique IDs within case; define before testing.

Example reference: `{"id":"profile-frame-v3","path":"design/profile-v3.png","kind":"design"}`. Original reference files must remain available and unchanged until verification.

## Runner

`render --project ROOT --manifest FILE [--timeout 600] [--runs-dir DIR] [--android-bin android]`

Require a Git project root and compatible Android CLI. Outputs must be outside the project. Submodules and symlinked Git-visible inputs are blocked: use a standalone materialized checkout of the relevant project. Hashing Git-visible files has a cost on large repos. Do not replace it with timestamp-only checks. `--android-bin` permits a pinned executable; fake executables are for runner tests only.

`verify --run-dir DIR --review FILE`

Exit codes: render 0 = evidence ready, verify 0 = PASS_PREVIEW; 1 = test failure; 2 = blocked/configuration/integrity problem; verify 3 = needs review. Parse JSON status too.

Outputs: report, review template, CLI logs, reference snapshots and isolated case directories. Verification writes `verdict.json`. Integrity checks are bookkeeping, not tamper-proof attestation against someone who can rewrite all files.

## Review

Copy the template. Keep `run_id`, `report_sha256` and IDs unchanged. Supply `reviewer`, ISO-8601 `reviewed_at`, and every case's:

- `images_reviewed`: all PNG relative paths in that case's report.
- `references_reviewed`: all required reference IDs.
- `checks`: exactly one `{id, status, evidence, note}` per requirement; status `PASS`, `FAIL`, or `NEEDS_REVIEW`. Each check needs at least one same-case artifact path as evidence and a concrete note.
- `findings`: unresolved `{id, description, evidence}` records. No findings may remain in a passing case.

Never claim image review without opening images. With no image-reading capability, return NEEDS_REVIEW. Evidence paths alone do not establish correctness. PNG checks validate structure/checksums, not visual content; image decoding and interpretation belong to review.

## Failure handling

- Missing CLI/capability: BLOCKED with exact missing tool/flag; avoid legacy `android` executables.
- Preview missing: inspect source set/variant and discovery; do not invent FQNs.
- Count mismatch: examine actual variants. Correct genuinely wrong expectations with explanation; never omit failures.
- Image contains error placeholder: fail review even if valid PNG.
- Missing/malformed tree: keep logs and block; never fabricate JSON.
- Changed code/manifest/reference/artifact: rerender and rereview.
- Timeout: runner terminates the process group on POSIX and does not request daemon mode.
