# Screen registry (spec ↔ Figma ↔ code)

Nguồn duy nhất để tra một màn: căn cứ spec, frame Figma, `@Preview` và file source. Dùng chung cho `ui-fix-loop`, `bug-fix` (cả hai mode), `ui-diff`, `bug-scout`. Thay cho `docs/design-refs/figma-refs.json` cũ (một file chung).

## Vị trí và lý do tách file

`<repo>/docs/references/screens/<screen-id>.json`, **một file / màn** (kể cả mỗi state có frame Figma riêng: `app-01-home`, `app-01a-home-loading`). Nhiều lane / worker song song sửa màn khác nhau thì không đụng nhau; hai lane cùng màn thì đụng cùng file nên `check-plan` tự xếp `after`. Commit được, không chứa secret.

`screen-id`: kebab-case, chỉ `[A-Za-z0-9._-]`, ổn định (đặt theo frame Figma, vd `ls-07-mcq`). Đổi tên màn thì giữ id cũ.

## Schema mỗi file

```json
{
  "screen": "app-01-home",
  "name": "APP · 01 · Home",
  "section": "home",
  "figma_url": "https://www.figma.com/design/<fileKey>/...?node-id=646-5489",
  "file_key": "<fileKey>",
  "node_id": "646:5489",
  "screenshot": "docs/figma/png/app-01-home_646-5489.png",
  "spec": ["docs/spec-phase1/spec-parts/02-home-lesson-completion.md#Home"],
  "module": ":composeApp",
  "source_files": ["composeApp/src/commonMain/kotlin/.../HomeScreen.kt"],
  "previews": [{"fqn": "com.x.home.HomeScreenPreview", "source": "composeApp/.../HomeScreenPreview.kt"}],
  "note": "",
  "updated": "2026-11-14T01:10:00+07:00"
}
```

- `spec`: đường dẫn repo-relative + `#mục` (hoặc `confluence:<pageId>#<mục>@v<version>`). Nhiều mục được.
- `screenshot`: PNG mốc Figma trong repo (nếu có), để so mà không gọi Figma API.
- Đọc được format cũ (`spec` là chuỗi, `preview_fqn` đơn): script tự chuẩn hoá khi ghi.

## Lệnh (`ui-fix-loop/scripts/uifix_state.py`, mặc định `--refs docs/references/screens`)

| Lệnh | Việc |
|---|---|
| `ref-get --screen S` | in entry (exit ≠ 0 nếu chưa có) |
| `ref-list` | bảng screen · node · preview · số mục spec |
| `ref-add --screen S [--url] [--name] [--section] [--screenshot] [--spec P#m …] [--source P …] [--preview-fqn F …] [--module] [--note]` | thêm / cập nhật một màn; scalar mới ghi đè, list hợp lại |
| `ref-merge --delta F.json` | gộp nhiều màn từ `{"screens": {id: entry}}` hoặc `{id: entry}`; dùng cho delta của scout, lane và để chuyển `figma-refs.json` cũ |

## Khi nào ghi

| Ai | Lúc | Ghi gì |
|---|---|---|
| `ui-fix-loop` Bước 0 / worker `preview` | màn chưa có entry | `ref-add` đủ trường trong worktree của mình, commit cùng PR |
| `bug-scout` (batch) | Phase 2 | `B/registry-delta.json` cho mọi màn đã map (không ghi repo) |
| Lane `bug-fixer` | khi fix đổi source / thêm preview / tìm thêm mục spec của màn trong lane | `ref-add` vào worktree lane, commit cùng PR (file màn nằm trong `files` của lane) |
| Leader batch | Phase 6 | PR docs "registry sync": `ref-merge` `B/registry-delta.json` cho các màn chưa lane nào cập nhật |

Không sửa tay khi có script; sửa tay thì giữ đúng schema.

## Repo chưa có registry

Lần đầu: `ref-merge --delta docs/design-refs/figma-refs.json` (nếu có file cũ), rồi bổ sung từ scout. Thêm `docs/references/README.md` một đoạn: "Tra màn → `docs/references/screens/<id>.json` (spec ↔ Figma ↔ code), lệnh `uifix_state.py ref-get/ref-list`".
