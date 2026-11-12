# Device playbook (verifier `artemis-android` đọc trước khi chạy job)

Mẹo chung cho mọi app, rút từ các lần verify thật. Leader dán đường dẫn file này vào brief verifier (xem `device-queue.md`).

## Phần riêng theo máy: overlay của repo app

Đặc thù từng thiết bị (serial → model, RAM, lệnh bị treo, tài khoản test…) **không** ghi vào skill này. Chúng nằm ở `<repo app>/.harness-overlay/devices.md` (cạnh `overlay.yaml`, thường untracked). Leader đọc file đó ở main checkout (nếu có) và dán các mục khớp serial được giao vào brief. File chưa có thì không tạo; verifier gặp đặc thù mới → ghi vào `result.md` mục "Đặc thù máy" để user quyết định thêm vào overlay. Mỗi mục trong `devices.md`:

```
## <serial hoặc model>
- Môi trường: RAM, API level, Play Services, ngôn ngữ
- Không dùng: <lệnh/hành vi làm treo máy>
- Mẹo: <cách vượt trở ngại đã biết>
```

## Trước khi chạy

- Xác nhận đúng build: APK được leader build ngay trước khi giao job (device-queue §Chuẩn bị APK). `adb -s <S> shell dumpsys package <pkg> | grep -E "versionName|lastUpdateTime"` sau khi cài; không dùng APK có sẵn của lần trước.
- Emulator thiếu RAM / chậm: đóng app nền, `adb -s <S> shell am kill-all`; vẫn treo → báo `INCONCLUSIVE` kèm lý do, không lặp vô hạn.
- Reset trạng thái app: `am force-stop <pkg>` rồi mở lại bằng launcher/splash activity (`adb shell am start -n <pkg>/<SplashActivity>`); không `pm clear` khi checklist cần giữ dữ liệu.

## Chướng ngại lặp lại

| Hiện tượng | Cách xử lý |
|---|---|
| Quảng cáo onboarding kẹt / không đóng được | Tắt mạng (`svc wifi disable`, `svc data disable`) đúng đoạn onboarding rồi bật lại; ghi lại bước đã tắt mạng vào `result.md` |
| `uiautomator dump` treo hoặc timeout trên một số máy OEM | Dùng screenshot + `mobile_find_element`; ghi máy đó vào `devices.md` nếu chưa có |
| Backend dev trả 503 / timeout | Retry tối đa 3 lần, cách nhau 30s; vẫn lỗi → `INCONCLUSIVE (backend)`, không kết luận pass/fail cho bug |
| Cần ép Remote Config / flag để test | Ưu tiên cơ chế debug có sẵn của app. Không ghi được vào prefs (splash ghi đè) → báo leader xin APK vá tạm từ lane (có commit riêng, không push); sau khi test **gỡ APK vá, cài lại APK lane**, ghi cả hai vào `result.md` |
| Kết quả mâu thuẫn giữa các lần chạy | Chạy lại 1 lần; vẫn mâu thuẫn → `INCONCLUSIVE`, đính kèm cả hai log |

## Đo thời gian / đếm

Ảnh chụp màn hình lệch vài giây nên không dùng để đo thời lượng hoặc đếm sự kiện.
- Log có timestamp: `adb -s <S> logcat -v time -s <TAG>` (lane đã thêm log đo vào fix, xem `lane-protocol.md` §Log đo lường). Xóa buffer trước: `adb -s <S> logcat -c`.
- Kết luận bằng hiệu timestamp trong log; ảnh chỉ để minh họa trạng thái UI.
- Đã đo bằng log mà không có dòng log mong đợi → `INCONCLUSIVE`, báo leader để lane bổ sung log.

## Kết quả trả về

`result.md` trong `evidence/<KEY>/device/`: từng bước PASS/FAIL/INCONCLUSIVE + đường dẫn ảnh/log + mục "Đặc thù máy" (nếu có). FAIL/INCONCLUSIVE: nêu bước, kỳ vọng, thực tế; không đoán nguyên nhân code.
