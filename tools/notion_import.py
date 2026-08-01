#!/usr/bin/env python3
"""
Notion 에서 내보낸 zip 을 블로그 글(.md)로 변환합니다.

Notion export 는 그대로 쓸 수 없는 이유가 몇 가지 있습니다.
이 스크립트가 아래를 한 번에 처리합니다.

  1. zip 안에 zip (ExportBlock-*.zip) 이 또 들어 있음
  2. 한글 파일명이 UTF-8 플래그 없이 저장돼서 unzip 이 못 읽음
  3. 맨 위 H1 이 글 제목과 중복됨 (front matter 로 옮겨야 함)
  4. 제목 단계가 한 칸씩 높아서 목차(##/### 를 읽음)가 비어 보임
  5. Notion 속성 줄(번호: 2, 완료: Yes ...)이 본문에 섞여 나옴
  6. 이미지 경로가 %20 범벅 + 한글 자모분리(NFD) 라 안 뜸

사용법:
  python3 tools/notion_import.py "<zip 경로>" --slug system-architecture \\
      --categories "Study, Dreamhack, System Hacking" \\
      --summary "한 줄 요약"

옵션을 생략하면 slug 는 파일명에서, 제목은 본문 H1 에서, 날짜는 오늘로 채웁니다.
"""

import argparse
import datetime
import os
import pathlib
import re
import shutil
import sys
import tempfile
import unicodedata
import urllib.parse
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def extract(zip_path, dest):
    """한글 파일명이 깨지지 않게 zip 을 푼다."""
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            # UTF-8 플래그(0x800)가 없으면 cp437 로 잘못 읽힌 이름 → 되돌린다
            if not (info.flag_bits & 0x800):
                try:
                    name = name.encode("cp437").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            target = dest / name
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def unwrap(zip_path, work):
    """바깥 zip → (있으면) 안쪽 ExportBlock zip 까지 풀고 최종 폴더를 돌려준다."""
    outer = work / "outer"
    outer.mkdir(parents=True)
    extract(zip_path, outer)

    # glob 은 경로에 든 대괄호([Dreamhack] 등)를 문자 집합으로 해석해 버린다.
    # 폴더를 직접 훑어서 찾는다.
    nested = sorted(p for p in outer.iterdir()
                    if p.is_file() and p.name.startswith("ExportBlock-")
                    and p.suffix.lower() == ".zip")
    if not nested:
        return outer

    inner = work / "inner"
    inner.mkdir(parents=True)
    extract(nested[0], inner)
    return inner


def norm(s):
    """자모분리(NFD) / 결합(NFC) 차이를 무시하고 비교하기 위한 정규화."""
    return unicodedata.normalize("NFC", s)


def build_file_index(root):
    """실제 파일들을 '정규화된 상대경로 → 실제 경로' 로 색인."""
    index = {}
    for p in root.rglob("*"):
        if p.is_file():
            index[norm(str(p.relative_to(root)))] = p
            index[norm(p.name)] = p
    return index


def strip_notion_props(lines):
    """H1 바로 뒤에 붙는 Notion 속성 줄(번호: 2, 완료: Yes ...)을 걷어낸다."""
    out = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            out.extend(lines[i:])
            return out
        # '이름: 값' 형태의 짧은 속성 줄이면 버린다
        if re.match(r"^[^:#\-*>|]{1,40}:\s+\S", stripped):
            continue
        if stripped == "":
            continue
        out.extend(lines[i:])
        return out
    return out


def top_heading_level(text):
    """본문에서 가장 높은(숫자가 작은) 제목 단계. 코드블록 안은 세지 않는다."""
    top, in_fence = None, False
    for line in text.split("\n"):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+\S", line)
        if m:
            lv = len(m.group(1))
            if top is None or lv < top:
                top = lv
    return top


def shift_headings(text):
    """모든 제목을 한 단계 내린다 (# → ##). 코드블록 안은 건드리지 않는다."""
    result, in_fence = [], False
    for line in text.split("\n"):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            result.append(line)
            continue
        if not in_fence:
            m = re.match(r"^(#{1,5})(\s+)(.*)$", line)
            if m:
                line = "#" + m.group(1) + m.group(2) + m.group(3)
        result.append(line)
    return "\n".join(result)


def escape_angles(text):
    """<destination> 같은 꺾쇠 표현을 마크다운 변환기가 HTML 태그로 오해하지
    않도록 이스케이프한다.

    이걸 안 하면 kramdown 이 <destination> 을 '열린 태그'로 보고 닫는 태그를
    찾다가, 못 찾으면 그 뒤 문서 전체를 HTML 덩어리로 삼켜서 글이 통째로
    깨진다(제목·표·코드블록이 전부 글자로 보임).

    코드블록 · 인라인코드 · 자동링크(<https://...>) 는 건드리지 않는다.
    """
    out, in_fence = [], False
    for line in text.split("\n"):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        # 인라인 코드(`...`)는 그대로 두고 바깥쪽만 처리
        parts = re.split(r"(`[^`]*`)", line)
        for i, part in enumerate(parts):
            if part.startswith("`"):
                continue
            parts[i] = re.sub(r"<(?!https?://)([^<>\s][^<>]*)>",
                              r"&lt;\1&gt;", part)
        out.append("".join(parts))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path")
    ap.add_argument("--slug", help="파일명/주소에 쓸 영문 slug")
    ap.add_argument("--title", help="글 제목 (기본: 본문 첫 H1)")
    ap.add_argument("--date", help="YYYY-MM-DD (기본: 오늘)")
    ap.add_argument("--time", help="HH:MM (같은 날 글끼리 순서를 정할 때. 기본: 현재 시각)")
    ap.add_argument("--categories", default="Study",
                    help='쉼표로 구분. 예: "Study, Dreamhack, System Hacking"')
    ap.add_argument("--summary", default="", help="목록에 보일 한 줄 요약")
    args = ap.parse_args()

    zip_path = pathlib.Path(args.zip_path).expanduser()
    if not zip_path.is_file():
        sys.exit(f"zip 을 못 찾았습니다: {zip_path}")

    work = pathlib.Path(tempfile.mkdtemp(prefix="notion-import-"))
    try:
        src = unwrap(zip_path, work)

        mds = [p for p in src.rglob("*.md")]
        if not mds:
            sys.exit("zip 안에 .md 가 없습니다. Notion 에서 'Markdown & CSV' 로 내보냈는지 확인하세요.")
        md_path = max(mds, key=lambda p: p.stat().st_size)
        raw = md_path.read_text(encoding="utf-8")
        lines = raw.split("\n")

        # 첫 H1 = Notion 페이지 제목 → front matter 로 옮기고 본문에서 제거
        title = args.title
        if lines and lines[0].startswith("# "):
            if not title:
                title = lines[0][2:].strip()
            lines = lines[1:]
        if not title:
            title = md_path.stem

        lines = strip_notion_props(lines)
        body = "\n".join(lines)

        # Notion 페이지에 따라 최상위 제목이 # 일 때도, ## 일 때도 있다.
        # 목차는 h2/h3 만 읽으므로 최상위가 h2 가 되도록 맞춘다.
        # (이미 ## 부터 시작하는 글을 또 내리면 목차가 반쯤 비어 보인다.)
        top = top_heading_level(body)
        shifted = top == 1
        if shifted:
            body = shift_headings(body)

        body = escape_angles(body).strip()

        slug = args.slug or re.sub(r"[^a-z0-9]+", "-",
                                   md_path.stem.lower()).strip("-") or "post"

        # Jekyll 은 미래 시각 글을 발행하지 않는다(future: false 가 기본).
        # 시각을 고정값으로 박으면 새벽에 올릴 때 글이 안 보이므로 현재 시각을 쓴다.
        now = datetime.datetime.now()
        date = args.date or now.date().isoformat()
        clock = now.strftime("%H:%M:%S")
        if args.time:
            parts = args.time.split(":")
            clock = f"{int(parts[0]):02d}:{int(parts[1]):02d}:00"

        # ── 이미지 옮기고 경로 고치기 ──────────────────
        img_dir = ROOT / "assets" / "img" / slug
        index = build_file_index(src)
        moved, missing, counter = [], [], 0

        def replace(m):
            nonlocal counter
            alt, path = m.group(1), m.group(2)
            if path.startswith(("http://", "https://", "/")):
                return m.group(0)
            decoded = norm(urllib.parse.unquote(path))
            real = index.get(decoded) or index.get(norm(os.path.basename(decoded)))
            if real is None:
                missing.append(path)
                return m.group(0)
            counter += 1
            ext = real.suffix.lower() or ".png"
            new_name = f"{counter:02d}{ext}"
            img_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(real, img_dir / new_name)
            moved.append(new_name)
            return f"![{alt}](/assets/img/{slug}/{new_name})"

        body = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, body)

        cats = [c.strip() for c in args.categories.split(",") if c.strip()]
        cats_yaml = "[" + ", ".join(cats) + "]"

        front = (
            "---\n"
            f'title: "{title}"\n'
            f"date: {date} {clock} +0900\n"
            f"categories: {cats_yaml}\n"
            f'summary: "{args.summary}"\n'
            "---\n\n"
        )

        out_path = ROOT / "_posts" / f"{date}-{slug}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(front + body + "\n", encoding="utf-8")

        print(f"글      : {out_path.relative_to(ROOT)}")
        print(f"제목    : {title}")
        print(f"카테고리: {cats_yaml}")
        print(f"이미지  : {len(moved)}장 → assets/img/{slug}/")
        print(f"제목단계: 최상위가 h{top} 이라 " +
              ("한 단계 내렸습니다" if shifted else "그대로 뒀습니다"))
        if missing:
            print(f"⚠ 경로를 못 찾은 이미지 {len(missing)}개: {missing}")
        if not args.summary:
            print("⚠ summary 가 비어 있습니다. 목록에 요약이 안 나오니 채워주세요.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
