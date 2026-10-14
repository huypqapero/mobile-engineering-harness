# Contributing

Welcome contribute vào Mobile Engineering Harness. Guidelines dưới đây giữ changes consistent + reviewable.

## Before you contribute

1. **Mở issue** mô tả scope + rationale trước PR
2. **Discuss** approach để tránh work duplicate hoặc misalign
3. Confirm change fit vào upstream (generic) hay nên là product overlay

## Scope boundary

### IN scope upstream

- Generic rule + skill + knowledge áp dụng được nhiều Android/CMP project
- Pattern có evidence (được 2+ product độc lập request)
- Tool/CLI improvements cho harness workflow
- Bug fix (install.sh validation, Konsist test template)

### OUT of scope upstream (product overlay thay)

- Product-specific rule (analytics event naming, feature-specific pattern)
- Platform SDK details (Firebase Analytics config, RevenueCat setup)
- Business logic domain-specific
- Infrastructure (CI/CD, VPS, device farm, dashboard)

## Development

### Setup

```bash
git clone https://github.com/huypqapero/mobile-engineering-harness.git
cd mobile-engineering-harness
./install.sh version
```

### Changes

- Edit upstream files cho generic improvements
- Test render với AudioBookApp-like overlay (hoặc tạo fake overlay test)
- Verify `./install.sh task validate` nếu touch task contract schema
- Check backward compat: overlay cũ không có field mới vẫn work

### Testing

Chưa có automated test suite upstream. Smoke test manual:

```bash
# Test render
./install.sh install --overlay /path/to/test-overlay

# Test task validator
./install.sh task validate --plan blueprints/task-contract/template.yaml

# Test uninstall
./install.sh uninstall --overlay /path/to/test-overlay
```

### Markdown

Follow existing style trong `knowledge/`, `skills/`, `blueprints/`:
- Vietnamese prose cho explanation
- English cho code identifier + technical term
- Code block với language tag
- Tables cho comparison matrix
- Rule format: `**MUST** / **SHOULD** / **MAY** / **FORBIDDEN**`

## PR process

1. Fork → feature branch (`feat/<short-name>` hoặc `fix/<short-name>`)
2. Commit convention: Conventional Commits
   ```
   feat: add android-graphql skill
   fix(install): handle empty overlay.yaml
   docs: update README stack options table
   chore: bump versions
   ```
3. Push → open PR
4. PR description:
   - Scope (what/why)
   - Testing done (smoke test commands)
   - Breaking changes (if any)
   - Migration path (if breaking)
5. Review by maintainer
6. Squash merge với commit message well-formed

## Rule / skill contribution

Khi add rule mới hoặc skill mới:

1. **User story thực tế**: AI đã vi phạm pattern này ≥ 3 lần?
2. **Verifiable**: Konsist test hoặc Detekt rule hoặc explicit review checklist?
3. **Severity rõ**: MUST/SHOULD/MAY/FORBIDDEN?
4. **Rationale 1 câu**: tại sao rule tồn tại?
5. **Violation example + fix**: concrete, không vague "best practice"
6. **Add Konsist/Detekt test** cùng commit, không delay enforcement

Khi add skill mới:

1. **Trigger rõ**: khi nào invoke skill?
2. **Prerequisites**: file cần đọc trước
3. **Procedure có steps rõ**
4. **Required policies**: rule nào từ constitution áp dụng
5. **Common mistakes**: anti-patterns với fix
6. **Output contract**: deliverable cụ thể

## Release process

Maintainer only:

1. Update `CHANGELOG.md` với version entry
2. Bump version trong relevant files (README, harness.yaml.template nếu applicable)
3. Commit `chore: release vX.Y.Z`
4. `git tag vX.Y.Z && git push origin vX.Y.Z`
5. `gh release create vX.Y.Z --notes-file ...`

## Code of conduct

- Respect reviewers + contributors
- Focus trên code/rule, không personal
- Assume good intent
- Share credit cho idea sources

## Reporting

- **Bug**: open issue với reproducer
- **Security**: email trực tiếp (private)
- **Feature request**: open issue với use case + rationale

## License

Contributions assumed under MIT License (xem [LICENSE](./LICENSE)).
