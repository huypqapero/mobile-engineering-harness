# Screenshots placeholder

Fixture `book-detail` không commit real PNG files (binary + large). Khi chạy e2e thực tế, user cung cấp screenshots qua agent run manual.

Placeholder files describe expected content:

## book-detail-content.png

**Expected content:**
- Top app bar với back button (left)
- Icon ambiguous top-right (candidates: bookmark / favorite / share)
- Book cover large, portrait aspect, top-center
- Title text headline-large below cover
- Author text body-medium below title
- Primary button label "Add to Cart" below metadata (intentional conflict với spec "Buy")

## book-detail-loading.png

**Expected content:**
- Top app bar
- LinearProgressIndicator horizontal top
- Skeleton placeholder cho cover + title + author

## book-detail-error.png

**Expected content:**
- Top app bar
- Error illustration centered
- Error message text
- Retry button primary

## For e2e run

```bash
# Khi user chuẩn bị fixture thật:
cp /real/screenshots/*.png verification/e2e/fixtures/book-detail/input/screenshots/

# Rồi chạy agent với fixture input:
# "Prepare feature brief cho book-detail từ
#  verification/e2e/fixtures/book-detail/input/spec.md
#  và verification/e2e/fixtures/book-detail/input/screenshots/"

# Agent output vào verification/e2e/fixtures/book-detail/actual/brief.yaml
# Rồi:
./verification/e2e/scripts/run-e2e.sh book-detail
```
