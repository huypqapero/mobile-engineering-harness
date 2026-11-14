# Code graph (Graphify) — tra cấu trúc code trước khi grep

Nguồn duy nhất của quy tắc dùng graph trong harness. Skill / agent khác chỉ trỏ về đây.

Graph = **bản đồ** (ai gọi ai, ai import ai, file:line của symbol), build bằng tree-sitter AST, offline, không gọi LLM. Graph giúp tìm chỗ cần đọc nhanh hơn; nó **không phải bằng chứng**: mọi `file:line` đưa vào scout / fix-design / review phải được Read lại trong worktree.

## Lấy graph

`CG` = `<harness>/scripts/code-graph.sh` (đường dẫn tuyệt đối).

```bash
CG ensure <worktree>    # build nếu chưa có cho HEAD, in đường dẫn graph.json (lần đầu ~30s, commit sau ~10s nhờ cache)
CG path <worktree>      # chỉ in đường dẫn nếu đã có (exit 1 nếu chưa)
```

- Graph nằm ở `<git-common-dir>/graphify/<commit>/graphify-out/graph.json`: ngoài cây làm việc, mọi worktree cùng commit dùng chung, không thể bị `git add` nhầm. Không chạy `graphify .` trực tiếp trong repo app (sinh `graphify-out/` trong cây làm việc).
- Worktree có sửa chưa commit → key `<commit>-dirty-…`, build lại mỗi lần gọi.
- Exit `2` (chưa cài graphify / không phải git repo) hoặc `1` (build lỗi) → bỏ qua graph, scout bằng Grep/Glob như cũ, ghi một dòng `graph: unavailable` trong report. Không cài đặt gì giữa chừng.
- Người điều phối (leader) build sẵn một lần và truyền `Graph: <path>` trong brief; agent con nhận path thì dùng luôn, không build lại.

## Lệnh tra (luôn kèm `--graph <path>`)

| Câu hỏi | Lệnh | Ghi chú |
|---|---|---|
| Symbol X ở đâu, nối với gì | `graphify explain "X" --graph G` | `Source: file Lnn`, các cạnh kèm `file:Lnn`; `--all` để xem hết |
| Sửa X thì ai bị ảnh hưởng (caller, màn import Contract) | `graphify affected "X" --graph G --depth 1` | Tăng `--depth 2` khi đổi contract dùng chung; X có thể là tên file `PaywallContract.kt` |
| A đi tới B thế nào (call chain, luồng điều hướng) | `graphify path "A" "B" --graph G --undirected` | Không thấy đường có hướng thì thêm `--undirected` |
| Chưa biết tên symbol, chỉ có mô tả bug | `graphify query "paywall purchase button" --graph G --budget 1500` | Từ khoá tiếng Anh theo tên code; output `TRUNCATED` → thu hẹp câu hỏi hoặc tăng `--budget` |
| Điểm nút trung tâm của module | `graphify god-nodes --graph G --top 10` | Chỉ khi cần định hướng repo lạ |

Exit code: `0` có kết quả · `3` tên trùng nhiều node (output liệt kê `id:` → chạy lại với id) · `4` không có node → Grep.

## Đọc kết quả

- `query` khớp từ khoá mờ và trộn cả file test: dùng nó để ra tên class ứng viên (`*Screen`, `*ViewModel`, `*Contract`, `*UseCase`), rồi `explain` / `affected` trên tên đó. Test xuất hiện trong `affected` = test cần chạy / sửa theo.
- `[EXTRACTED]` = thấy trực tiếp trong source (import, kế thừa, tham chiếu). `[INFERRED 0.85]` = graphify tự resolve (vd lời gọi `.setState()`), phải mở file xác nhận.
- Graph thấy thiếu hoặc không thấy: DI qua DSL (Koin `single { }` / `viewModel { }`: chỉ thấy cạnh `imports` từ `*Module.kt`, không thấy binding nào inject gì), route khai báo bằng `val`/string, reflection, resource (`strings.xml`, layout), Gradle. File chỉ có hằng / route đôi khi "yielded no symbols". Các chỗ này vẫn Grep (`*Module.kt`, `NavHost`, `R.string.`).
- File Kotlin lỗi cú pháp với tree-sitter (thường là Compose DSL phức tạp) chỉ được extract một phần: thiếu cạnh ≠ không có quan hệ.
- Graph build từ HEAD của worktree lúc gọi `ensure`; code bạn vừa sửa chưa có trong graph. Cần blast radius sau khi sửa → `ensure` lại (key dirty) hoặc Grep.

## Khi nào dùng / không dùng

Dùng: tìm entry point + Contract/ViewModel/Screen của màn từ mô tả bug, dựng call chain, liệt kê caller trước khi đổi signature/state, reviewer kiểm "fix có bỏ sót caller không", gom bug theo file/root cause chung trong batch.

Không dùng: tra một chuỗi literal / text UI / key string (Grep nhanh hơn), sửa 1 dòng đã biết rõ file, repo không phải git.
