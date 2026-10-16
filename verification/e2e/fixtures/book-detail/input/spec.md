# Spec: Book Detail Screen

**Feature ID:** book-detail
**Status:** draft (open items pending)
**Author:** pm@company.com

## Goal

Người dùng mở màn hình chi tiết sách, xem metadata (title, author, cover) và tap play để preview 30 giây audio.

## Scope

**IN:**
- Book Detail screen với content state
- Audio preview 30s
- Error state với Retry button

**OUT (defer):**
- Full audio player
- Rating + review

## User flows

### F1 — View book detail

1. User tap item ở Book List screen
2. Nav tới Book Detail screen với bookId
3. Fetch metadata từ API
4. Hiển thị cover + title + author + Buy button

### F2 — Preview audio

1. User tap Buy button
2. Playback 30s audio preview bắt đầu trong 500ms
3. Hiển thị progress indicator

## Business rules

- BR-001: Audio preview phải start trong 500ms sau tap
- BR-002: Error state hiển thị message + retry button
- BR-003: Offline mode: hiển thị cached data nếu có, else offline component

## Non-functional requirements

- Performance: scroll 60fps trên Pixel 6 baseline
- Accessibility: contentDescription cho mọi image + button
- i18n: hỗ trợ Vietnamese + English

## Acceptance criteria

- AC-001: Tap play button → audio playback trong 500ms (p50)
- AC-002: Render book metadata khi API success
- AC-003: Error state có Retry button, tap Retry → re-fetch
- AC-004: Offline state hiển thị cached data hoặc offline component

## Open items

- OI-01: Behavior khi preview audio fail trên cellular network?
- OI-02: Tap play → inline playback hay nav tới full player screen?

## Dependencies

- API: GET /books/{id}/metadata
- Storage: SharedPreferences cho cached metadata
