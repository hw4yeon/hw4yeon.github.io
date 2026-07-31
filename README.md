# hw4yeon.github.io

개인 포트폴리오 + 기술 블로그. Jekyll 기반, GitHub Pages 자동 빌드.

## 구조

```
├── _config.yml       사이트 설정 (제목, 이메일, 링크 등)
├── index.html        메인 (About + 최근 글)
├── blog.html         글 목록  → /blog/
├── projects.html     프로젝트  → /projects/
├── _layouts/         공통 껍데기 (default, post)
├── _posts/           ★ 글은 전부 여기에
└── assets/css/       스타일
```

## 글 쓰기

`_posts/YYYY-MM-DD-slug.md` 로 파일 생성:

```markdown
---
title: "글 제목"
date: 2026-08-01 10:00:00 +0900
tags: [웹해킹, XSS]
summary: "목록에 보일 한 줄 요약"
---

본문 (마크다운)
```

```bash
git add . && git commit -m "post: 글 제목" && git push
```

푸시 후 1~2분이면 반영됩니다.

## 로컬 미리보기 (선택)

```bash
bundle install
bundle exec jekyll serve   # http://localhost:4000
```

## 고칠 만한 곳

| 뭘 바꾸고 싶을 때 | 파일 |
|---|---|
| 이름·이메일·사이트 제목 | `_config.yml` |
| 첫 화면 소개 문구, 스킬 | `index.html` |
| 프로젝트 카드 | `projects.html` |
| 색상·폰트 | `assets/css/style.css` (맨 위 `:root`) |
| 메뉴 항목 | `_layouts/default.html` |
