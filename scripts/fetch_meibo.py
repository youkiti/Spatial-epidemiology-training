#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_meibo.py — 日本感染症学会 専門医名簿PDFを取得する(issue #7・#8の前段)。

このPDFは個人名と所属を含むため、リポジトリにはコミットしない
(`.gitignore` の `data/raw/` を参照。要件定義書 §4.2)。取得したファイルと
そのメタ情報(SHA-256・バイト数・取得日時)はどちらも `data/raw/` 配下にのみ
書き出し、加工過程のコード(このスクリプトと `parse_meibo.py`)だけをコミット対象とする。

冪等性: 既に `data/raw/` に同名ファイルがあり、かつそのSHA-256が
メタJSON(`*.meta.json`)に記録済みのSHA-256と**一致するときだけ**
再ダウンロードをスキップする。存在するだけでは信用しない
(途中で切れた壊れたファイルがそのまま使われ続ける事故を防ぐため)。
メタが無い・読めない・SHA-256が不一致な場合は再取得し、その旨を
stdoutに出す(サーバ側にETag等の仕組みが無いため、整合性の判定は
ローカルのSHA-256比較で行う)。

一過性のネットワーク失敗を「取得できないファイル」として握り潰さない:
このスクリプトは失敗時に非ゼロ終了するだけで、失敗を記録した状態を
`data/raw/` に残さない(メタJSONは成功時のみ書く)。

使い方:
    python scripts/fetch_meibo.py
    python scripts/fetch_meibo.py --url <別URL> --out data/raw/meibo_260701.pdf

終了コード: 取得成功(または既存ファイルの再利用)=0、失敗=非ゼロ。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# Windows のコンソールでも日本語出力が文字化けしないようにする(simulate_spatial_data.py に合わせる)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_URL = "https://www.kansensho.or.jp/uploads/files/senmoni/meibo_260701.pdf"
DEFAULT_OUT = Path("data/raw/meibo_260701.pdf")


def sha256_of(path: Path) -> str:
    """ファイルのSHA-256を計算する(大きいファイルでもメモリに全展開しない)。"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def meta_path_for(out_path: Path) -> Path:
    return out_path.with_name(out_path.name + ".meta.json")


def download(url: str, out_path: Path) -> None:
    """URLからPDFを取得し、out_path に書き出す。

    リクエストURL自体はログに出さない(CLAUDE.md の全般方針: クエリ文字列に
    APIキーが載る場合の事故を避けるため。このURLに秘密情報は無いが、
    習慣として踏襲する)。ネットワークエラー・非2xxはここで例外として送出し、
    呼び出し側で非ゼロ終了に変換する(握り潰さない)。
    """
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # 中断時に不完全なファイルを本来のパスに残さないよう、一時ファイル経由で書く。
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    with tmp_path.open("wb") as f:
        f.write(response.content)
    tmp_path.replace(out_path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="感染症専門医名簿PDFを取得する")
    parser.add_argument("--url", default=DEFAULT_URL, help="取得元URL")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="保存先パス")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_path: Path = args.out
    meta_path = meta_path_for(out_path)

    if out_path.exists():
        local_digest = sha256_of(out_path)
        recorded_digest = None
        if meta_path.exists():
            try:
                existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
                recorded_digest = existing_meta.get("sha256")
            except (json.JSONDecodeError, OSError):
                recorded_digest = None

        if recorded_digest is not None and recorded_digest == local_digest:
            print(f"既存ファイルを再利用します(メタ情報のSHA-256と一致): {out_path}")
            print(f"  SHA-256: {local_digest}")
            return 0

        if recorded_digest is None:
            print(
                f"既存ファイルのメタ情報(*.meta.json)が無いか読めないため、再取得します: {out_path}"
            )
        else:
            print(
                f"既存ファイルのSHA-256がメタ情報と一致しないため、再取得します: {out_path}"
            )
            print(f"  記録済みSHA-256: {recorded_digest}")
            print(f"  実ファイルSHA-256: {local_digest}")

    try:
        download(args.url, out_path)
    except requests.RequestException as e:
        print(f"エラー: PDFの取得に失敗しました({type(e).__name__})。", file=sys.stderr)
        print("一時的な障害の可能性があるため、失敗をメタ情報として記録せず終了します。", file=sys.stderr)
        return 1

    digest = sha256_of(out_path)
    size = out_path.stat().st_size
    retrieved_at = datetime.now(timezone.utc).isoformat()

    print("取得成功:")
    print(f"  保存先: {out_path}")
    print(f"  SHA-256: {digest}")
    print(f"  バイト数: {size}")
    print(f"  取得日時(UTC): {retrieved_at}")

    meta = {
        "url": args.url,
        "sha256": digest,
        "size_bytes": size,
        "retrieved_at_utc": retrieved_at,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  メタ情報: {meta_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
