#!/usr/bin/env python3
"""Unit test cho check_spec.py. Chạy: python3 -m unittest test_check_spec (trong scripts/)."""

import unittest

from check_spec import check

GOOD = """# APP - Phase 1

## A. TỔNG QUAN

Flow tổng: Splash → Home

## B. MÔ TẢ CHI TIẾT

### 1. Home

| Screen | Description | UI |
| --- | --- | --- |
| **Home** | **Mô tả:** Tab Home.<br>**Logic:**<br>• Banner tự chuyển sau 5s<br>**Logic click button:**<br>• Bấm phim → Detail<br>**Remote config:** `tab_home` = home → mở Home (default) | app_1-1.png |

### ~~2. Notification (backlog)~~

## C. TỔNG HỢP REMOTE CONFIG

| Key | Default | Ghi chú |
| --- | --- | --- |
| `tab_home` | home | home / for_you |

## D. EVENT TRACKING

| Màn | Trigger | Event name |
| --- | --- | --- |
| **Home** | Vào màn | `home_view` |
"""

BAD = """# APP

## B. MÔ TẢ CHI TIẾT

### 1. Home

| Screen | Description | UI |
| --- | --- | --- |
| **Home** | **Logic click button:**<br>• X → Y<br>**Logic:**<br>• dùng `gift_box_coin` [PO confirm] | |
| **Popup** | chỉ có text | p.png |

### 2. Rewards

Không có bảng.

## C. TỔNG HỢP REMOTE CONFIG

| Key | Default | Ghi chú |
| --- | --- | --- |
| `unused_key` |  | thiếu default |

## D. EVENT TRACKING

| Màn | Trigger | Event name |
| --- | --- | --- |
| **Home** | Vào màn | `home_view` |
|  | Lặp | `home_view` |
|  | Sai tên | `HomeClick` |
"""


CONFLUENCE_QUIRKS = """## A. TỔNG QUAN

## B. MÔ TẢ CHI TIẾT

### FIRST OPEN

Đoạn giới thiệu, không có bảng.

### 1. Home

| Screen | Description | UI |
| --- | --- | --- |
| **Search** | **Mô tả:** Tìm phim.<br>**Flow:** Home → Search → Kết quả | Không có kết quả<br>**Logic:**<br>• Gợi ý top 10 | app_1-1.png |
| **Bảng coin** | Số coin lấy từ `coin_cfg` | key | value | | --- | --- | | `coin_cfg` | ``` { "watch_1_ad": 10 } ``` | Field `watch_1_ad` |  |

### ~~2. Notification (backlog)~~

| ~~**Noti**~~ | ~~lịch gửi PO confirm~~ | |

## C. TỔNG HỢP REMOTE CONFIG

| Key | Default | Ghi chú |
| --- | --- | --- |
| `coin_cfg` | {} | JSON |
| `coin_cfg` | {} | trùng |

## D. EVENT TRACKING

| Màn | Trigger | Event name |
| --- | --- | --- |
| **Home** | Vào màn | `home_view` |
"""


def messages(findings, severity):
    return [f["message"] for f in findings if f["severity"] == severity]


class CheckSpecTest(unittest.TestCase):
    def test_good_spec_has_no_error_or_warn(self):
        findings = check(GOOD)
        self.assertEqual(messages(findings, "ERROR"), [])
        self.assertEqual(messages(findings, "WARN"), [])

    def test_bad_spec_reports_expected_errors(self):
        errors = " | ".join(messages(check(BAD), "ERROR"))
        self.assertIn("tổng quan", errors)
        self.assertIn("'Popup': thiếu khối", errors)
        self.assertIn("`unused_key` thiếu default", errors)
        self.assertIn("`home_view` trùng", errors)
        self.assertIn("`HomeClick` không phải snake_case", errors)

    def test_setext_headings_from_confluence_export(self):
        setext = GOOD.replace("## A. TỔNG QUAN", "A. THÔNG TIN CHUNG\n------------------")
        setext = setext.replace("## B. MÔ TẢ CHI TIẾT", "B. MÔ TẢ CHI TIẾT\n-----------------")
        self.assertEqual(messages(check(setext), "ERROR"), [])

    def test_confluence_quirks_do_not_raise_false_positives(self):
        findings = check(CONFLUENCE_QUIRKS)
        errors = messages(findings, "ERROR")
        warns = " | ".join(messages(findings, "WARN"))
        infos = " | ".join(messages(findings, "INFO"))
        # Chỉ lỗi thật: key trùng.
        self.assertEqual(len(errors), 1)
        self.assertIn("`coin_cfg` trùng", errors[0])
        # `|` trần trong Flow không làm mất khối Logic; heading không đánh số bị bỏ qua.
        self.assertNotIn("Search", warns)
        self.assertNotIn("FIRST OPEN", warns)
        # Hàng logic không ảnh chỉ WARN; field JSON không bị coi là key lạ.
        self.assertIn("'Bảng coin': thiếu khối", warns)
        self.assertNotIn("watch_1_ad", warns)
        # PO confirm trong đoạn gạch ngang (backlog) không được liệt kê.
        self.assertNotIn("PO confirm", infos)

    def test_identifiers_declared_in_overview_table_are_known(self):
        spec = GOOD.replace("Flow tổng: Splash → Home",
            "Flow tổng: Splash → Home\n\n| Asset | Màn |\n| --- | --- |\n| `anim_confetti` | Home |")
        spec = spec.replace("• Banner tự chuyển sau 5s", "• Banner tự chuyển sau 5s, dùng `anim_confetti`")
        self.assertEqual(messages(check(spec), "WARN"), [])

    def test_bad_spec_reports_warnings_and_info(self):
        findings = check(BAD)
        warns = " | ".join(messages(findings, "WARN"))
        infos = " | ".join(messages(findings, "INFO"))
        self.assertIn("thứ tự khối sai", warns)
        self.assertIn("Module '2. Rewards'", warns)
        self.assertIn("`gift_box_coin` không có trong bảng", warns)
        self.assertIn("`unused_key` không được nhắc", infos)
        self.assertIn("PO confirm:", infos)


if __name__ == "__main__":
    unittest.main()
