---
name: ui-diff-review
description: So UI actual/preview vs expected/figma rồi VIẾT NHẬN XÉT DIFF + TỰ SUY LUẬN ACCURACY (match_score 0-100) + verdict pass/fail theo ngưỡng. Khác compare-ui-board (chỉ liệt kê diff thô), skill này thêm lớp đánh giá: nhận xét từng khác biệt, chấm điểm độ khớp bằng thị giác có rubric, và ghi result.json để trace. Dùng khi cần "fix này đạt design chưa", verify sau fix, review mức độ khớp, hoặc gate pass/fail. Chống sót bằng pass 2: crop + zoom từng component, checklist trục cố định, và đo màu vùng (sample_region.py) để chốt khác biệt nền/nút/đậm-nhạt thay vì tin mắt. Tách localization (bỏ qua) khỏi style (tính). Tái dùng create_board.py của compare-ui-board để dựng board; model chấm điểm, script chỉ record/đo. Input ảnh sạch có nhãn do caller truyền.
---

# ui-diff-review

> So UI trên MỘT board có nhãn → **nhận xét khác biệt** → **tự suy luận match_score
> (0-100)** → **verdict pass/fail**. Điểm là phán đoán thị giác của model (không
> pixel-diff); script `verdict.py` chỉ ghi lại con số + tính pass/fail theo ngưỡng.
>
> Quan hệ với `compare-ui-board`: skill đó **liệt kê diff thô**; skill này thêm lớp
> **đánh giá + chấm điểm + verdict**. Dựng board thì tái dùng `create_board.py` của
> compare-ui-board (DRY), không copy lại.

## Khi nào dùng

- "Fix này đã đạt design chưa?" — verify sau khi có ảnh/preview mới.
- Gate pass/fail theo ngưỡng (vd ≥ 95 mới coi là khớp).
- Review mức độ khớp giữa actual/preview và expected/figma, cần cả nhận xét lẫn điểm.
- Khi caller cần một con số match_score + lý do để quyết định lặp fix hay dừng.

Nếu chỉ cần **liệt kê diff** (không cần điểm/verdict) → dùng thẳng `compare-ui-board`.

## BẮT BUỘC — so ảnh bằng cách GHÉP, không đọc lẻ

Luật cứng kế thừa từ `compare-ui-board`: khi so/chấm giữa ≥ 2 ảnh, **PHẢI ghép vào
MỘT board có nhãn rồi đọc một lượt**. CẤM đọc lẻ từng ảnh qua các lượt rồi chấm bằng
trí nhớ — vision model đếm/ước lượng tỉ lệ không đáng tin, dễ "ảo" khác biệt và cho
điểm sai. Ghép board trước, nhận xét + chấm sau.

## Pipeline (node flow)

```
① LẤY INPUT          ② GHÉP BOARD           ③ ĐỌC BOARD 1 LƯỢT
(caller, ngoài skill)   create_board.py        vision + CHECKLIST TRỤC
  Jira/prnt.sc  ───►   actual|expected  ───►   duyệt từng region
  → ảnh sạch           → board.png             (container/title/icon/button/layout)
                                                     │
                              ┌──── nghi màu/đậm-nhạt/structure/component? ────┐
                              │ CÓ                                     KHÔNG   │
                              ▼                                                ▼
                   ④ PASS 2 — SOI SÁT (có điều kiện)                   (bỏ qua ④)
                      crop component → zoom board                            │
                      + sample_region.py (đo hex/brightness)                 │
                              └───────────────────┬─────────────────────────┘
                                                  ▼
                                    ⑤ SUY LUẬN match_score (rubric)
                                                  ▼
                                    ⑥ GHI VERDICT → result.json (PASS/FAIL)
```

| Node | Input | Hành động | Tool | Output |
|------|-------|-----------|------|--------|
| ① Lấy input | URL Jira / prnt.sc | **Caller** fetch — skill KHÔNG tự tải | (ngoài skill) | ảnh sạch có nhãn |
| ② Ghép board | 2–4 ảnh | Dán vào 1 canvas có nhãn | `create_board.py` | board.png |
| ③ Đọc board | board.png | Nhìn 1 lượt, chạy checklist trục, tách localization | vision | diff thô |
| ④ Pass 2 *(có điều kiện)* | ảnh gốc | Crop+zoom component; đo màu vùng nghi | `create_board.py` + `sample_region.py` | hex/brightness |
| ⑤ Chấm điểm | findings | Model suy luận 0–100 theo rubric | model | match_score + reason |
| ⑥ Verdict | score, board | Ghi file + pass/fail theo ngưỡng | `verdict.py` | result.json, exit 0/2 |

Node ④ **có điều kiện**: chỉ chạy khi diff ở mức component / màu tinh vi / nghi
structure. Case presence/absence rõ ngay ở board overview thì bỏ qua ④ để khỏi tốn
bước. Chi tiết từng node ở phần Flow dưới.

## Người chấm (agent `ui-board-judge`, Opus)

Đây là chỗ DUY NHẤT mô tả quy tắc này; `ui-diff`, `ui-fix-loop`, `compare-ui-board`, `bug-fix` đều trỏ về đây.

Bước ③–⑥ (đọc board, soi sát, chấm điểm, verdict — §2, §2b, §3 bên dưới) **luôn giao cho agent `ui-board-judge`** (`model: opus`, `agents/ui-board-judge.md`), không tự chấm trong phiên đang chạy (thường là Sonnet). Caller vẫn lo bước ①–② (lấy ảnh sạch, dựng board).

- **Người đang dựng board** (phiên chính, hoặc agent con như lane `bug-fixer`, worker note, subagent lane của `ui-fix-loop`): tự spawn 1 `ui-board-judge` / board. Prompt truyền `Board:` (hoặc `Actual:` + `Expected:`), `Screen:`, `Threshold:` (mặc định 95), `Out dir:`, `Accepted:` nếu có. Nhiều board → spawn song song, `run_in_background`. Chờ xong rồi đọc `<Out dir>/result.json` (+ `findings.json`) và tự đi tiếp: dưới ngưỡng thì fix vòng kế theo `ui-fix-loop` (≤ 3 vòng), đạt ngưỡng hoặc hết vòng thì kết thúc. Người sửa code không tự chấm board (judge ≠ người fix).
- **Agent con cũng spawn được judge** (tối đa 3 tầng dưới phiên chính, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`). Môi trường không spawn được (vượt độ sâu / thiếu Agent tool) → dừng và báo người gọi (kèm board + lý do), không tự chấm.
- **Chưa có agent `ui-board-judge`** trong danh sách agent: chạy `scripts/activate-claude-agents.sh` của harness và báo user reload session. Trong lúc chờ, chỉ tự chấm khi phiên hiện tại đang là Opus; không phải Opus thì dừng và báo user, không chấm thay.
- Judge ghi `findings.json` + `result.json` (qua `verdict.py`); caller không sửa điểm. Muốn đổi ngưỡng thì truyền `Threshold:` lúc spawn, không chỉnh sau.

## Flow

### 1. Dựng board (tái dùng compare-ui-board)

```bash
# before/after verify (phổ biến nhất cho skill này)
python3 ~/.claude/skills/compare-ui-board/scripts/create_board.py --mode before-after \
  --before actual.png --expected design.png --after after-preview.png \
  --note "<ghi chú fix>" --title "<ISSUE> — Verify" --output board.png

# hoặc pair khi chỉ có actual/after vs expected
python3 ~/.claude/skills/compare-ui-board/scripts/create_board.py --mode pair \
  --actual after.png --expected design.png --title "<ISSUE>" --output board.png
```

Nếu caller đã đưa board sẵn thì bỏ qua bước này. (Chi tiết mode/panel: xem
`compare-ui-board/SKILL.md`.)

### 2. Đọc board → nhận xét diff + chấm điểm (prompt chuẩn)

Đọc board MỘT lượt bằng prompt dưới. Output gồm 2 phần: **findings** (nhận xét từng
khác biệt) và **match_score + reason** (tự suy luận theo rubric).

```text
Bạn là Mobile UI Review Agent. Bạn nhận MỘT ảnh ghép nhiều panel có nhãn.
Vai trò panel: ACTUAL/BEFORE/AFTER = bản hiện tại; EXPECTED/FIGMA = nguồn chuẩn;
COMPOSE PREVIEW = preview code.

Nhiệm vụ:
1. So AFTER/ACTUAL/PREVIEW với EXPECTED/FIGMA trên cùng khung.
2. Duyệt TỪNG region theo CHECKLIST TRỤC bên dưới — KHÔNG chỉ báo cái nổi bật.
   Với mỗi trục có khác biệt: ghi region + trục + mô tả actual vs expected + loại
   lỗi (layout|spacing|size|color/style|wrong-asset|missing/extra|text/content) +
   severity (high|med|low) + đã khớp hay còn lệch.
3. TỰ SUY LUẬN match_score 0-100 theo rubric, kèm 1-2 câu lý do nêu điểm trừ đến
   từ finding nào.

CHECKLIST TRỤC (chạy cho MỖI region/component, đừng bỏ trục nào):
- Container: nền (màu + độ sáng), bo góc, viền, shadow, PHẠM VI bọc (card bọc cả
  nút hay nút nằm ngoài?).
- Title: nội dung, màu, độ đậm, cỡ, CASING (UPPERCASE vs sentence-case).
- Subtitle/body: nội dung, màu.
- Icon: có/không, vị trí (cạnh title?), loại.
- Mỗi Button: màu nền (fill), màu chữ, hình (pill/tròn/vuông), viền, cỡ, vị trí
  (trong hay ngoài container), nhãn + casing.
- Layout/structure: thứ tự, khoảng cách, nhóm phần tử.

Rule:
- EXPECTED/FIGMA là chuẩn. Bỏ qua khác biệt do status bar / nội dung động (data,
  state, text value thay đổi) — KHÔNG trừ điểm.
- TÁCH localization khỏi style: khác NGÔN NGỮ (FR vs EN) = KHÔNG trừ điểm; nhưng
  CASING/text-transform (HOA vs thường), màu, cỡ, vị trí của chữ VẪN là style → tính.
- Deviation user/PO đã chấp nhận (nếu caller nêu) = không trừ điểm, ghi "accepted".
- Màu/nền/nút: nếu nghi đảo scheme hoặc đậm↔nhạt, ĐO bằng sample_region.py rồi so
  hex/brightness, ĐỪNG chốt bằng mắt.
- KHÔNG bịa số đo px/dp. Chỉ nhận xét vùng khác, không mô tả cả màn.
- Đánh dấu điểm chưa chắc là "confidence: low".
```

#### Rubric chấm match_score

| Khoảng | Ý nghĩa |
|---|---|
| 97–100 | Khớp design; chỉ khác do data/state động hoặc deviation đã accepted. Không lỗi UI thật. |
| 90–96 | Về cơ bản khớp; 1 khác biệt nhỏ (spacing/size/màu nhẹ) ở 1 vùng phụ. |
| 75–89 | Lệch rõ ở 1 vùng (sai màu/size/spacing đáng kể) hoặc vài lệch nhỏ gộp lại. |
| 50–74 | Sai asset / sai layout ở vùng quan trọng (hero, CTA). |
| < 50 | Lệch cấu trúc lớn, nhiều vùng sai, khác hẳn design. |

Ngưỡng pass mặc định **95** (caller đổi qua `--threshold`). Lặp fix ↔ review tới khi
đạt ngưỡng.

### 2b. Soi sát từng component (BẮT BUỘC khi so popup/card/button hoặc board panel nhỏ)

Chấm từ 1 board tổng panel nhỏ là **nguyên nhân gốc gây sót** (miss nền/structure/
casing). Khi diff ở mức component — hoặc actual là full-screen còn design là crop —
PHẢI làm pass 2:

1. **Crop + normalize**: crop vùng component ở actual (vd popup ở đáy màn) rồi ghép
   board pair riêng với design crop, mỗi board **chỉ 1 cặp** để panel đủ lớn. Scale 2
   panel về chiều cao gần nhau (create_board tự cân) để size so được.
   ```bash
   python3 - <<'PY'
   from PIL import Image
   Image.open("actual_full.png").crop((x0,y0,x1,y1)).save("crop_actual.png")  # vùng popup
   PY
   python3 ~/.claude/skills/compare-ui-board/scripts/create_board.py --mode pair \
     --actual crop_actual.png --expected design_crop.png \
     --title "<ISSUE> · <component> — zoom" --output board_zoom.png
   ```
2. **Đọc board zoom + chạy CHECKLIST TRỤC** cho từng component. Mỗi popup/card là 1
   lượt soi riêng.
3. **Đo màu chốt nghi ngờ** (nền, nút, chữ) — đừng tin mắt với đậm↔nhạt / đảo scheme:
   ```bash
   # chạy trên CẢ actual-crop lẫn design-crop ở vùng tương ứng (frac bền resolution)
   python3 ~/.claude/skills/ui-diff-review/scripts/sample_region.py --image crop_actual.png --frac \
     --region "card-bg=0.55,0.08,0.92,0.22" --region "button=0.2,0.72,0.8,0.92"
   python3 ~/.claude/skills/ui-diff-review/scripts/sample_region.py --image design_crop.png --frac \
     --region "card-bg=0.2,0.15,0.9,0.38"  --region "button=0.2,0.72,0.9,0.92"
   ```
   So `mean` hex + `bright`: lệch brightness lớn (vd 134 vs 240) = đảo đậm/nhạt → finding
   color/style chắc chắn, confidence high (có số). Chọn vùng sample tránh chữ để `std` nhỏ.

Chỉ sau pass 2 (zoom + checklist + đo màu) mới chấm điểm. Nếu bỏ pass 2 cho case
component, điểm không đáng tin.

### 3. Ghi verdict (script chỉ record, không tự tính điểm)

```bash
python3 ~/.claude/skills/ui-diff-review/scripts/verdict.py \
  --score <0-100> --board board.png --out result.json \
  [--threshold 95] [--issue <ISSUE>] [--screen "<màn>"] \
  --reason "<1-2 câu lý do cho điểm>"
```
Exit 0 = PASS (score ≥ threshold), exit 2 = FAIL. `result.json` chứa match_score,
ngưỡng, pass/fail, reason, board, thời điểm — làm trace/evidence.

## Output format

### Findings (nhận xét diff)

```json
{
  "screen": "Learning Path - Result",
  "issue": "AAP079-33",
  "summary": "Hero đã đổi sang mascot khớp design; streak badge còn (accepted).",
  "findings": [
    {
      "id": "F1",
      "region": "Hero/Illustration",
      "severity": "high",
      "actual": "Mascot robot nữ ăn mừng",
      "expected": "Mascot robot nữ ăn mừng (figma 34:213)",
      "type": "wrong-asset",
      "status": "khớp",
      "confidence": "high"
    },
    {
      "id": "F2",
      "region": "Streak badge",
      "severity": "low",
      "actual": "Có '+1 day streak'",
      "expected": "Frame design không có badge",
      "type": "missing/extra",
      "status": "accepted (PO giữ)",
      "confidence": "medium"
    }
  ]
}
```

### Verdict (result.json — do verdict.py ghi)

```json
{
  "issue": "AAP079-33",
  "screen": "Learning Path - Result",
  "match_score": 96,
  "pass_score": 95,
  "pass": true,
  "reason": "Hero khớp design; chỉ còn streak badge là deviation đã accepted.",
  "board": "board.png",
  "scored_by": "model-visual-judgment",
  "verified_at": "2026-11-05T10:20:00+07:00"
}
```

## Gotchas

- `match_score` là **phán đoán thị giác của model**; màu/nền/nút thì ĐO bằng
  `sample_region.py` (tier-2) để chốt, đừng tin mắt với đậm↔nhạt / đảo scheme.
- **Hay sót nhất**: khác biệt NỀN/CONTAINER và STRUCTURE (nút nằm trong hay ngoài
  card), và CASING. Case component PHẢI làm pass 2 (zoom + checklist + đo màu) — xem
  §2b. Chấm từ board tổng panel nhỏ là nguồn gốc miss.
- Đừng trừ điểm cho data/state động (số liệu, text value, status bar) và khác NGÔN
  NGỮ (localization) — nhưng casing/text-transform, màu, cỡ VẪN tính.
- Deviation đã được user/PO chấp nhận thì ghi "accepted" và KHÔNG trừ điểm — nhưng
  phải nêu rõ trong reason để trace.
- Giữ ≤ 4 ô/board; board quá nhiều ô làm model chấm loạn.
- Skill này **không** fix code, không tải ảnh, không render preview, không locate
  source — caller lo các bước đó và truyền ảnh sạch vào.
- Phụ thuộc `compare-ui-board/scripts/create_board.py` để dựng board. Nếu skill đó
  không có, caller phải tự cung cấp board.
