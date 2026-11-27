# Plan: skill telemetry + tự động hoá nhiều mức với Orca

- Status: in-progress (phase 1–2 đang làm)
- Date: 2026-11-25
- Owner: huypqapero

## Outcome

1. Biết được mỗi GitHub account trong team đã cài skill nào, dùng skill nào, dùng bao nhiêu lần, và gọi skill bằng prompt như thế nào.
2. Quy trình spec → brief → code → test → fix bug → release chạy tự động theo 4 mức trên Orca. Người chỉ chạm vào các điểm duyệt.

## Quyết định đã chốt (user, 2026-11-25)

| Câu hỏi | Chốt |
|---|---|
| Phạm vi tracking | Cả team, hook cài cùng harness trên máy từng người, gắn GitHub login |
| Nội dung prompt | Lưu toàn văn. Chỉ che chuỗi giống credential (token, key, password), vì quy tắc repo cấm đẩy secret lên git |
| Nơi gom | Repo GitHub private riêng cho telemetry; mỗi máy ghi JSONL cục bộ rồi đồng bộ |
| Thứ tự | Lập plan cả hai, làm telemetry trước |

## Constraints

- Hook không được làm chậm hay làm hỏng phiên: luôn exit 0, không in gì ra stdout, chỉ dùng Python stdlib.
- Không đẩy credential lên git. Prompt khác giữ nguyên.
- Team phải được báo trước là prompt gọi skill được lưu toàn văn (docs + lúc cài).
- Orca automation chạy trên máy có Orca runtime; thiết bị test vẫn qua ARTEMIS.
- Giữ nguyên các điểm `CLAUDE.md` bắt buộc hỏi người (scope guard, release, merge ngoài fast-path).

## Non-goals

- Không đo token/chi phí từng skill.
- Không theo dõi prompt không gọi skill.
- Không thay ARTEMIS bằng Orca emulator.
- Không tự động trả lời thay PO/BA.

## Acceptance criteria

- [x] Gõ `/bug-fix status` hoặc agent gọi Skill → một dòng event JSONL có `login`, `repo`, `skill`, `source`, `prompt`. (test + chạy tay với payload thật; chưa cài vào settings thật)
- [x] `telemetry.py backfill` nhập được lượt dùng cũ từ transcript, chạy lại không tạo trùng. (38 transcript → 89 event, lần 2 → 0)
- [x] `telemetry.py report` ra bảng: skill dùng nhiều nhất, theo người, skill đã cài nhưng chưa dùng, mẫu prompt mỗi skill.
- [ ] `telemetry.py sync --repo <owner/repo>` gộp event vào `data/<login>/<yyyy-mm>.jsonl`, không trùng id, không có credential. (logic gộp có test; chưa chạy với repo thật)
- [x] Unit test của telemetry PASS (17 test).
- [ ] Mức 1 Orca chạy được trên một app thử; mức 2–4 có phase riêng được duyệt trước khi làm.

## Phases

| # | Phase | Trạng thái | File |
|---|---|---|---|
| 1 | Collector: hook ghi event + backfill + inventory | xong: hook đã cài trên máy owner; `bootstrap.sh`, `harness-init`, `mehcli telemetry` tự cài (cần merge vào `main` để team nhận) | [phase-01](phase-01-telemetry-collector.md) |
| 2 | Sync về repo private + report + dashboard | `sync`/`report` xong; chờ tạo repo private, dashboard | [phase-02](phase-02-telemetry-sync-report.md) |
| 3 | Orca mức 1: automation `status` / `resume` / `sync-jira` | todo | [phase-03](phase-03-orca-level-1.md) |
| 4 | Orca mức 2: skill `/autopilot` + decision gate | todo | [phase-04](phase-04-autopilot-level-2.md) |
| 5 | Orca mức 3: máy runner 24/7 | todo | [phase-05](phase-05-runner-level-3.md) |
| 6 | Orca mức 4: giảm điểm chờ người | todo | [phase-06](phase-06-gate-reduction-level-4.md) |

Dependency: 2 cần 1. 4 cần 3. 5 và 6 cần 4. Telemetry (1–2) cho số liệu để chọn skill nào tự động hoá trước ở 4.

## Risks

| Risk | Giảm thiểu |
|---|---|
| Prompt toàn văn chứa dữ liệu khách hàng / link nội bộ lên repo | Repo private, quyền đọc giới hạn; thông báo team; che credential; có lệnh `uninstall` |
| Hook lỗi làm hỏng phiên | Bọc toàn bộ trong try/except, timeout 5s trong settings, test |
| Transcript chỉ giữ ~30 ngày | Hook ghi ngay lúc dùng; backfill chỉ bù phần cũ |
| `--reuse-session` của Orca không giữ được agent nền của `/bug-fix` | Thử trên một app ở phase 3 trước khi nhân rộng |

## Unresolved

- Tên repo telemetry private (ví dụ `huypqapero/skill-telemetry`) và ai được quyền đọc.
- Nguồn trạng thái feature cho `/autopilot`: Jira epic hay `features.yaml` (phase 4).
- Có cho tự merge PR thuộc fast-path không (phase 6).
- Có máy runner riêng cắm thiết bị không (phase 5).
