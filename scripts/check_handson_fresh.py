#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_handson_fresh.py — Rハンズオンの生成物の鮮度チェック(issue #17)。

analysis/render_manifest.json (scripts/render_handson.R が書く) を読み、
docs/handson/ 配下の md・図・配布用 .Rmd コピーのハッシュを **R を実行せずに**
再計算して照合する。CI に R を入れない方針(リポジトリ直下の CLAUDE.md)のため、
「Rmd を変えたのに md を再生成していない」「生成された md を手で書き換えた」を
CI だけで検出できるようにするのがこのスクリプトの役割。

標準ライブラリのみで書く(CI に追加の pip 依存を入れないため)。

検出すること:
  1. マニフェストに記録されたハッシュと、実ファイルから再計算したハッシュが
     食い違う場合(Rmd 変更のし忘れ・生成物の手編集の両方を検出する)
  2. マニフェストが参照しているファイルが存在しない場合
  3. docs/handson/figures/ 配下に、マニフェストに載っていない PNG がある場合
     (削除し忘れの孤児ファイル)
  4. analysis/handson/*.Rmd のうち、マニフェストの 'handson' にエントリが無い
     ものがある場合(新規に置いた Rmd をレンダリングし忘れている)
  5. docs/handson/rmd/*.Rmd のうち、どの handson エントリの distributed_rmd にも
     該当しないものがある場合(削除し忘れの孤児 .Rmd コピー)

【注意】docs/handson/*.md 全体をこのスクリプトの対象にしてはいけない。
01-map-moran-lisa-gi.md 〜 04-case-study.md は Rmd 由来ではない手書きの
プレースホルダページであり、マニフェストに載らないのが正しい状態。

【改行コードの正規化について】
.gitattributes は "* text=auto eol=lf" で全テキストファイルの改行を LF に
固定しているが、作業コピーの改行コードは環境によっては CRLF になりうる
(このリポジトリの CLAUDE.md に既知の罠として記載)。テキストファイル
(.Rmd / .md)は改行を LF に正規化してからハッシュする。PNG はバイナリなので
そのままハッシュする。この正規化ルールは scripts/render_handson.R(R側)と
必ず揃えること — ここが食い違うと、正しく最新の生成物でも CI が恒久的に
赤くなる。

使い方:
    python scripts/check_handson_fresh.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "analysis" / "render_manifest.json"
FIGURES_DIR = REPO_ROOT / "docs" / "handson" / "figures"
HANDSON_SRC_DIR = REPO_ROOT / "analysis" / "handson"
RMD_COPY_DIR = REPO_ROOT / "docs" / "handson" / "rmd"

REMEDIATION = (
    "対処: リポジトリのルートで `Rscript scripts/render_handson.R` を実行して"
    "生成物を作り直し、docs/handson/ 以下と analysis/render_manifest.json を"
    "コミットし直してください。"
)


def _reconfigure_stdout_utf8() -> None:
    # Windows のコンソールは既定でシステムのコードページ(例: cp932)を使うため、
    # Japanese メッセージの print が環境によっては UnicodeEncodeError になりうる。
    # CI (ubuntu-latest, UTF-8 locale) では何もしない。
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def normalize_newlines(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_text_file(path: Path) -> str:
    return hashlib.sha256(normalize_newlines(path.read_bytes())).hexdigest()


def sha256_binary_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_entry(name: str, key: str, info: dict | None, problems: list[str]) -> None:
    if info is None:
        problems.append(f"[{name}] マニフェストに '{key}' のエントリがありません。")
        return
    rel_path = info.get("path")
    expected = info.get("sha256")
    if not rel_path or not expected:
        problems.append(f"[{name}] '{key}' のエントリが不完全です(path/sha256 が欠けています)。")
        return
    path = REPO_ROOT / rel_path
    if not path.exists():
        problems.append(f"[{name}] {rel_path} が存在しません(削除された、または未生成です)。")
        return
    actual = sha256_text_file(path)
    if actual != expected:
        problems.append(
            f"[{name}] {rel_path} のハッシュが一致しません "
            f"(マニフェスト: {expected[:12]}…, 実ファイル: {actual[:12]}…)。"
            "ソース Rmd を変更した後にレンダリングし直していないか、"
            "生成物を直接手で編集していないか確認してください。"
        )


def main() -> int:
    _reconfigure_stdout_utf8()

    if not MANIFEST_PATH.exists():
        print(f"NG: {MANIFEST_PATH.relative_to(REPO_ROOT)} が見つかりません。")
        print(REMEDIATION)
        return 1

    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"NG: {MANIFEST_PATH.relative_to(REPO_ROOT)} が正しいJSONではありません: {exc}")
        print(REMEDIATION)
        return 1

    handson = manifest.get("handson", {})
    if not handson:
        print(f"NG: {MANIFEST_PATH.relative_to(REPO_ROOT)} の 'handson' が空です。")
        print(REMEDIATION)
        return 1

    problems: list[str] = []
    known_figure_paths: set[Path] = set()

    for name, entry in handson.items():
        for key in ("source_rmd", "output_md", "distributed_rmd"):
            check_entry(name, key, entry.get(key), problems)

        figures = entry.get("figures", [])
        for fig in figures:
            rel_path = fig.get("path")
            expected = fig.get("sha256")
            if not rel_path or not expected:
                problems.append(f"[{name}] figures のエントリが不完全です(path/sha256 が欠けています)。")
                continue
            path = REPO_ROOT / rel_path
            known_figure_paths.add(path.resolve())
            if not path.exists():
                problems.append(f"[{name}] {rel_path} が存在しません(削除された、または未生成です)。")
                continue
            actual = sha256_binary_file(path)
            if actual != expected:
                problems.append(
                    f"[{name}] {rel_path} のハッシュが一致しません "
                    f"(マニフェスト: {expected[:12]}…, 実ファイル: {actual[:12]}…)。"
                )

    # 孤児図の検出: docs/handson/figures/ にあるがどの handson エントリの
    # マニフェストにも載っていない PNG(チャンクを消した後の消し忘れ等)。
    if FIGURES_DIR.exists():
        for png_path in sorted(FIGURES_DIR.glob("*.png")):
            if png_path.resolve() not in known_figure_paths:
                problems.append(
                    f"孤児ファイル: {png_path.relative_to(REPO_ROOT)} が"
                    "どの handson エントリのマニフェストにも載っていません"
                    "(削除し忘れた古い図の可能性があります)。"
                )

    # 未レンダリングの Rmd の検出: analysis/handson/*.Rmd のうち、マニフェストの
    # 'handson' にエントリが無いもの(Rmd を新規に置いたのにレンダリングし忘れた)。
    if HANDSON_SRC_DIR.exists():
        for rmd_path in sorted(HANDSON_SRC_DIR.glob("*.Rmd")):
            name = rmd_path.stem
            if name not in handson:
                problems.append(
                    f"未レンダリングの Rmd: {rmd_path.relative_to(REPO_ROOT)} が"
                    "analysis/render_manifest.json の 'handson' に載っていません"
                    "(Rscript scripts/render_handson.R でレンダリングし忘れている可能性があります)。"
                )

    # 孤児 .Rmd コピーの検出: docs/handson/rmd/*.Rmd のうち、どの handson エントリの
    # distributed_rmd にも該当しないもの(ソース Rmd を消した後の消し忘れ等)。
    known_distributed_rmd_paths: set[Path] = set()
    for entry in handson.values():
        distributed_rmd = entry.get("distributed_rmd") or {}
        rel_path = distributed_rmd.get("path")
        if rel_path:
            known_distributed_rmd_paths.add((REPO_ROOT / rel_path).resolve())

    if RMD_COPY_DIR.exists():
        for rmd_path in sorted(RMD_COPY_DIR.glob("*.Rmd")):
            if rmd_path.resolve() not in known_distributed_rmd_paths:
                problems.append(
                    f"孤児ファイル: {rmd_path.relative_to(REPO_ROOT)} が"
                    "どの handson エントリの distributed_rmd にも該当しません"
                    "(削除し忘れた古い .Rmd コピーの可能性があります)。"
                )

    if problems:
        print("NG: docs/handson/ の生成物が analysis/render_manifest.json と一致していません:")
        for p in problems:
            print(f"  - {p}")
        print()
        print(REMEDIATION)
        return 1

    print(f"OK: {len(handson)} 本のハンズオンの生成物は analysis/render_manifest.json と一致しています。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
