#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_links.py — 内部リンクと画像パスの検査。

`mkdocs build --strict` はリンク切れを取りこぼす。このリポジトリの CLAUDE.md が
既知の罠として記録している2つが典型で、どちらもビルドは緑のまま実サイトだけが壊れる。

  (罠1) 生の HTML の `<img src>` / `<a href>` は MkDocs が相対パスを書き換えない。
        ディレクトリURL形式(`docs/handson/00-setup.md` → `site/handson/00-setup/index.html`)
        のため Markdown 記法なら1階層分ずれを補正してくれるが、生 HTML は素通りする。
  (罠2) ディレクトリURL形式のページ間リンク(`../ch2-spatial-weights/`)は MkDocs が
        リンクとして解決できず、`INFO ... unrecognized relative link` が出るだけで
        `--strict` でも落ちない。以後そのリンクは切れても検出されない。

そこでこのスクリプトは2方向から検査する。

  検査A: ビルド済みの `site/` を走査し、すべての `href` / `src` の**内部**リンクが
         実ファイルに解決することを確かめる(罠1をここで捕まえる。生成後のHTMLを
         見るので、Markdown 由来か生 HTML 由来かによらず同じ基準で検査できる)。
  検査B: `docs/` の Markdown を走査し、拡張子の無い相対リンク(ディレクトリURL形式)が
         書かれていないことを確かめる(罠2)。ページ間リンクはソース相対の `.md` で
         書く、というこのリポジトリの規約そのものの検査にあたる。

標準ライブラリのみで書く(CI に追加の pip 依存を入れないため)。

使い方:
    mkdocs build --strict      # 先に site/ を作る
    python scripts/check_links.py
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = REPO_ROOT / "site"
DOCS_DIR = REPO_ROOT / "docs"

# 検査Aの対象にする属性。srcset は複数URL+記述子の構文で、このサイトでは使って
# いないため対象外にする(使い始めたらここに足す)。
URL_ATTRS = {"href", "src"}

# スキーム付き・プロトコル相対・ページ内アンカー・データURIは外部扱いで飛ばす。
EXTERNAL_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|//|#)")

# 検査Bで見る Markdown のインラインリンク `[text](target)`。画像 `![alt](target)` も
# 同じ形なので同時に拾える。target に `(` `)` を含むURLは扱わない(このリポジトリには無い)。
MD_LINK_RE = re.compile(r"(?<!\\)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# 検査Bで「拡張子あり」とみなすもの。ここに無い拡張子(例: `.md`)は正常なリンク。
# ディレクトリURL形式かどうかの判定は「最後のセグメントに `.` が無い」で行うため、
# この集合は使わず、下の判定ロジックで完結している。


class LinkCollector(HTMLParser):
    """HTML から href/src を集める。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in URL_ATTRS and value:
                self.links.append(value)


def _reconfigure_stdout_utf8() -> None:
    # Windows のコンソール(cp932)で日本語の print が UnicodeEncodeError になるのを避ける。
    # check_handson_fresh.py と同じ理由・同じ処理。
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def resolve_target(page: Path, raw: str) -> Path | None:
    """ページ内のリンク文字列を、site/ 配下の実ファイルのパスに解決する。

    解決できない(=リンク切れ)場合は None を返す。外部リンクは呼び出し側で除外済み。
    """
    split = urlsplit(raw)
    path = unquote(split.path)
    if not path:
        # `?query` や `#anchor` だけのリンク。同じページを指すので検査不要。
        return page

    if path.startswith("/"):
        # ルート相対。GitHub Pages は /Spatial-epidemiology-training/ 配下に配信するため、
        # site/ から見るときは先頭のプロジェクト名を1つ剥がす(overrides/404.html がこの形式)。
        parts = [p for p in path.split("/") if p]
        if parts and parts[0] == SITE_BASE_SEGMENT:
            parts = parts[1:]
        candidate = SITE_DIR.joinpath(*parts) if parts else SITE_DIR
    else:
        candidate = (page.parent / path).resolve()

    try:
        candidate.relative_to(SITE_DIR)
    except ValueError:
        # site/ の外に出るリンクは、それ自体がリンク切れ。
        return None

    if candidate.is_dir():
        index = candidate / "index.html"
        return index if index.exists() else None
    if candidate.exists():
        return candidate
    return None


def check_built_site() -> list[str]:
    """検査A: ビルド済み site/ の内部リンクが実ファイルに解決するか。"""
    problems: list[str] = []
    html_files = sorted(SITE_DIR.rglob("*.html"))
    for page in html_files:
        collector = LinkCollector()
        collector.feed(page.read_text(encoding="utf-8", errors="replace"))
        for raw in collector.links:
            if EXTERNAL_RE.match(raw):
                continue
            if resolve_target(page, raw) is None:
                rel = page.relative_to(SITE_DIR)
                problems.append(f"[検査A] site/{rel}: リンク先が存在しません -> {raw}")
    return problems


def check_markdown_sources() -> list[str]:
    """検査B: docs/ の Markdown にディレクトリURL形式のページ間リンクが無いか。"""
    problems: list[str] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        for raw in MD_LINK_RE.findall(text):
            if EXTERNAL_RE.match(raw) or raw.startswith("/"):
                continue
            path = urlsplit(raw).path
            if not path:
                continue
            last = path.rstrip("/").split("/")[-1]
            if last in ("", ".", ".."):
                continue
            if "." not in last:
                rel = md.relative_to(REPO_ROOT)
                problems.append(
                    f"[検査B] {rel}: ディレクトリURL形式のリンク -> {raw} "
                    "(ソース相対の .md で書くこと。この形式は MkDocs がリンクとして解決できず、"
                    "--strict でも落ちないためリンク切れを検出できなくなる)"
                )
    return problems


SITE_BASE_SEGMENT = "Spatial-epidemiology-training"


def main() -> int:
    _reconfigure_stdout_utf8()

    if not SITE_DIR.is_dir():
        print("NG: site/ がありません。先に `mkdocs build --strict` を実行してください。")
        return 1

    problems = check_built_site() + check_markdown_sources()

    if problems:
        print(f"NG: リンクの問題が {len(problems)} 件見つかりました。")
        print()
        for p in problems:
            print(f"  - {p}")
        return 1

    n_pages = len(list(SITE_DIR.rglob("*.html")))
    n_md = len(list(DOCS_DIR.rglob("*.md")))
    print(f"OK: site/ の {n_pages} ページの内部リンクと、docs/ の {n_md} 本の Markdown のリンク形式に問題はありません。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
