---
name: compare-ui-board
description: Compare image service — ghép ≥2 ảnh UI liên quan (actual, expected/figma, before/after, các biến thể asset) vào MỘT canvas có nhãn để vision model so trực tiếp 1 lần nhìn, rồi xuất findings JSON. Dùng khi phải so sánh / phân biệt / chọn giữa nhiều ảnh: detect lệch design, verify before/after, chọn 1 asset trong N biến thể. CHỈ làm compare image — không scaffold, không fix code, không render preview, không chấm điểm. Input là ảnh sạch có nhãn do caller (thường là skill khác) truyền vào; output là board.png + findings. Board mode: pair / quad / before-after / tự do.
---

# compare-ui-board

> Skill này **chỉ làm một việc: compare image**. Nhận ảnh sạch có nhãn do caller
> truyền vào → ghép board → đọc 1 lượt → trả findings JSON. Mọi thứ khác (tải ảnh,
> tìm code, fix, render preview, chấm điểm, trace folder) là việc của caller/orchestrator.

## Vấn đề giải quyết

Khi đưa model 2 ảnh ở 2 message/context khác nhau, model mô tả mỗi ảnh thành text
rồi tự so 2 đoạn text → mất chi tiết, hay "ảo" khác biệt. Thay vào đó: **ghép tất
cả ảnh liên quan vào 1 canvas có nhãn rõ**, model nhìn một lần và chỉ ra lệch trực
tiếp trên cùng khung tham chiếu. EXPECTED / FIGMA là nguồn chuẩn (source of truth).

> Kết quả đọc board dùng để **chấm điểm / pass-fail** → theo quy tắc "Người chấm" của `ui-diff-review` (agent `ui-board-judge`, Opus); đọc board chỉ để liệt kê diff thô thì caller tự đọc.

## Khi nào dùng

- So actual app vs design (detect bug UI "khác design").
- So before/after/expected sau khi đã có ảnh mới (verify một lượt).
- Chọn 1 asset đúng trong nhiều biến thể (mascot, icon, illustration, thumbnail...).
- Bất cứ lúc nào phải **so sánh / phân biệt / chọn** giữa ≥ 2 ảnh.

## BẮT BUỘC — so ảnh bằng cách GHÉP, không đọc lẻ

**Luật cứng (MANDATORY, NO EXCEPTIONS):** Bất cứ khi nào phải **so sánh / phân biệt /
chọn** giữa ≥ 2 ảnh — **PHẢI ghép tất cả ảnh liên quan vào MỘT board có nhãn
(`create_board.py`) rồi đọc một lượt**. CẤM đọc lẻ từng ảnh ở các lượt/tin nhắn khác
nhau rồi so bằng trí nhớ mô tả.

Lý do: vision model (1) **đếm không đáng tin** (1 tay vs 2 tay, số item), (2) **kém
phân biệt near-duplicate** — ảnh cùng style chỉ khác chi tiết cục bộ, (3) so ảnh qua
các lượt khác nhau = so bằng *mô tả đã nhớ*, mất chi tiết → "ảo" khác biệt, (4) ước
lượng **tỉ lệ/kích thước tuyệt đối sai** — phải đo bằng tool, không tin mắt.

Áp dụng:
- **Chọn asset trong N biến thể** (vd mascot_a..d khớp design nào): ghép **TẤT CẢ N
  biến thể + panel nguồn chuẩn** vào 1 board (mode tự do `--panel`), đọc 1 lượt. Trước
  khi chọn, **mô tả rành mạch điểm khác của từng biến thể** ("a=2 tay giơ thẳng;
  b=1 tay giơ 1 tay co; c=2 tay chắp; ...") rồi mới khớp với nguồn chuẩn. KHÔNG chốt ở
  biến thể đầu tiên thấy "na ná".
- **Kích thước / tỉ lệ / vị trí**: KHÔNG phán bằng mắt. Đo bbox bằng script (vd đếm
  vùng non-white, tính `wfrac/hfrac/title_y` so màn) và đối chiếu số với nguồn chuẩn.
- **Nếu còn mơ hồ** mascot/asset nào là đúng: hỏi thẳng designer/QA ID asset trong
  design — rẻ và chắc hơn mọi suy luận vision.

Vi phạm luật này (đọc lẻ rồi đoán) là nguyên nhân gốc của lỗi chọn sai biến thể /
rơi finding — đã xảy ra thực tế. Ghép board trước, phán sau.

## Tool

```bash
python3 ~/.claude/skills/compare-ui-board/scripts/create_board.py --mode <mode> ... --output board.png
```
Chạy bằng `python3` hệ thống (cần Pillow). Nguồn mỗi panel là **đường dẫn local**
hoặc **URL**; URL `prnt.sc`/`lightshot` được tự resolve sang ảnh gốc.

### Modes

| Mode | Bố cục | Dùng khi |
|---|---|---|
| `pair` | `[ACTUAL] \| [EXPECTED]` | chỉ có 2 ảnh |
| `quad` | `[ACTUAL]\|[EXPECTED]` / `[COMPOSE PREVIEW]\|[FIGMA NODE]` | đủ 4 ảnh: suy được lỗi ở runtime hay preview |
| `before-after` | `[BEFORE]\|[EXPECTED]` / `[AFTER]\|[NOTE/PREVIEW]` | evidence sau fix |
| tự do | mỗi `--panel "Nhãn=nguồn"` = 1 ô (2 ô/hàng) | input bất kỳ |

Lưu ý: nhãn panel KHÔNG được chứa dấu `=` (parser tách `Nhãn=nguồn` ở dấu `=` đầu tiên).

```bash
# pair
python3 .../create_board.py --mode pair \
  --actual "https://prnt.sc/xxxx" --expected design.png \
  --title "AAP079-43 · AI Tutor" --subtitle "Issue: UI differs | Mode: Actual vs Expected" \
  --output board.png

# quad
python3 .../create_board.py --mode quad \
  --actual a.png --expected e.png --preview preview.png --figma node.png \
  --title "AI Tutor — Runtime+Preview+Design" --output board.png

# before-after (evidence)
python3 .../create_board.py --mode before-after \
  --before before.png --expected e.png --after after.png \
  --note "Fixed: hero navy + mascot + badge" \
  --title "AAP079-43 — Evidence" --output board_after.png

# tự do (N biến thể + nguồn chuẩn)
python3 .../create_board.py --panel "ACTUAL=a.png" --panel "EXPECTED=e.png" --panel "FIGMA NODE=f.png" --output board.png
```

## Prompt chuẩn cho bước đọc board

```text
Bạn là Mobile UI Compare Agent. Bạn nhận MỘT ảnh ghép gồm nhiều panel có nhãn.
Hiểu vai trò panel theo nhãn:
- ACTUAL / BEFORE / AFTER = bản hiện tại (runtime).
- EXPECTED / FIGMA NODE = nguồn chuẩn (source of truth).
- COMPOSE PREVIEW = preview code.

Nhiệm vụ:
1. So ACTUAL/PREVIEW với EXPECTED/FIGMA trên cùng khung.
2. Chỉ liệt kê KHÁC BIỆT có ý nghĩa, nhóm theo component/region.
3. Phân loại lỗi: layout | spacing | size | color/style | wrong-asset | missing/extra | text/content | runtime-only vs preview-level.
Rule:
- EXPECTED/FIGMA là chuẩn. So vùng tương ứng.
- Bỏ qua khác biệt do status bar thiết bị hoặc nội dung động (data/state).
- KHÔNG bịa số đo px/dp. KHÔNG mô tả cả màn, chỉ báo chỗ khác.
- Phân biệt lỗi UI thật với khác biệt do content/state. Đánh dấu điểm chưa chắc.
```

## Findings JSON (format cố định — output của skill)

Xuất ra path do caller chỉ định (hoặc trả inline nếu caller không cần file). Mỗi
finding kèm `source_hint` để caller biết hướng fix, và phân loại UI-thật vs data/state.

```json
{
  "screen": "AI Tutor",
  "issue": "AAP079-43",
  "summary": "Hero section, mascot asset, badge position, bubble icon lệch design.",
  "findings": [
    {
      "id": "F1",
      "region": "Hero/Header",
      "severity": "high",
      "actual": "Header trắng + tiêu đề, robot khối nhỏ",
      "expected": "Hero navy lớn + robot nữ lấp đầy",
      "type": "layout",
      "source_hint": "container background + cấu trúc header",
      "runtime_or_preview": "both",
      "confidence": "high"
    }
  ]
}
```

## Gotchas

- Ảnh rất dài/nhỏ: tool cap chiều cao panel (`MAX_H`); nếu vẫn khó đọc, ghép thêm board theo từng vùng (crop) rồi so riêng.
- Board quá nhiều ô → model dễ loạn; giữ ≤ 4 ô/board.
- Đây là so sánh **nhận thức thị giác**, không đo px tuyệt đối. Khi cần số tuyệt đối thì bổ sung pixel-diff/metadata (tầng 2, chưa làm).
- `prnt.sc` đôi khi đổi cấu trúc trang; nếu resolve fail, lấy URL `img.lightshot.app/*.png` thủ công rồi truyền vào.
- Skill này **không** tải ảnh từ Jira/Figma, không tìm code, không fix, không render preview, không chấm điểm. Caller chuẩn bị ảnh sạch và xử lý các bước đó.
