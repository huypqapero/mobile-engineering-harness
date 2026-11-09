# Hàng chờ thiết bị (Phase 5)

Bug tier `device` không chặn lane: lane fix + unit + build APK + xếp job, mở PR draft. Leader điều phối thiết bị riêng. `S` = state script, `B` = batch dir.

## Trạng thái

```
issue: fixed → pending_device → verifying_device → verified | failed
job:   pending → running → done | failed        (release thủ công → pending)
```

Một thiết bị giữ tối đa 1 job (`state.devices[serial].holder`). ARTEMIS cũng có mutex riêng theo thiết bị — hai lớp khóa, không chạy 2 job trên 1 emulator.

## Khi nào leader dispatch

Gọi `S device-dispatch B --exclude <serial…>` mỗi khi:
- một lane báo `DONE` có device job,
- một device job xong (`device-done`),
- user hỏi status.

`--exclude` = thiết bị đang bận ngoài batch: task ARTEMIS khác (`mobile_diagnose` → `tasks.active`), session `bug-note` đang giữ (`bug_queue.py list`), hoặc user nói đang dùng. Không chắc → coi là bận.

Kết quả:
- In `DJ-001 emulator-5554 PROJ-48 verify` → spawn verifier cho từng dòng (cột cuối `repro` hoặc `verify`).
- Exit 3 → còn job nhưng không có thiết bị rảnh: báo user "N bug đang chờ thiết bị", **không** chiếm thiết bị đang bận, không poll vòng lặp — chờ sự kiện kế tiếp ở trên.
- Không in gì, exit 0 → hết job.

Không có thiết bị nào (`adb devices` rỗng) → job giữ `pending`; báo user cắm máy / bật emulator (`mobile_diagnose(launch_avd=…)`), batch vẫn đóng được với bug `pending_device` + checklist test tay.

## Brief cho `artemis-android`

```
Verify fix <KEY> trên device_serial=<SERIAL> (chỉ thiết bị này).
APK: <path APK của lane>  (cài: adb -s <SERIAL> install -r <apk>)   Package: <applicationId>
Checklist: <B>/evidence/<KEY>/device-checklist.md
Bug gốc: actual=<…> expected=<…>  Điều kiện: <remote key, mạng, quyền, ads test…>
Chụp evidence vào <B>/evidence/<KEY>/device/ (screenshot mỗi bước, logcat khi crash: adb -s <SERIAL> logcat -d > logcat.txt).
Không sửa code. Trả: PASS/FAIL từng bước + đường dẫn ảnh + log.
Đọc trước: <SKILL_DIR>/references/device-playbook.md
Đặc thù máy <SERIAL>: <dán mục khớp từ <repo app>/.harness-overlay/devices.md nếu có | không có>
```

Model ARTEMIS: thao tác ngắn/đơn giản → Flash; flow dài, cần log/ADB/report → Pro (xem rule ARTEMIS của user). Chờ thời gian (vd hộp quà 30s) → trừ độ trễ bước của model.

## Job `repro` (crash chưa có stack, trước khi fix)

Cài APK build từ base (`<remote>/<base>`, build trong `R` hoặc một worktree tạm), làm theo repro của Jira, lưu `logcat.txt` + screenshot vào `B/evidence/<KEY>/device/`. Xong → `S device-done B <JOB> --result pass` (tái hiện được) hoặc `fail` (không tái hiện → hỏi reporter thêm thông tin), rồi `S lane B <L> status=planned` để lane chạy với log đó.

## Khi job verify xong

1. `S device-done B <JOB> --result pass|fail`.
2. Cập nhật `evidence/<KEY>/evidence.json`: thêm artifact device, AC runtime → `PASS`/`FAIL`, `verdict`.
3. PASS: khi mọi issue của lane `verified` → `gh pr ready <pr>`, tick checklist trong PR body. FAIL: SendMessage cho lane `bug-fixer` (cùng agent; agent đã kết thúc → spawn mới với brief đủ ngữ cảnh) kèm bước fail + đường dẫn evidence/log; **lane tự truy root cause** (leader không tự đọc log/dexdump/grep), fix lại (cap 2 vòng). Lane push code mới → `bug-reviewer` review lại → job mới xếp lại.
4. `S device-dispatch B …` để lấy job tiếp.

Agent device treo > 45 phút (`device-dispatch` cảnh báo trên stderr) → kiểm agent; treo thật → `TaskStop`, `S device-release B <SERIAL>` (job quay về pending).
