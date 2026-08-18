#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_census_age.py — 令和2年国勢調査 人口等基本集計 表2-7(年齢5歳階級)を取得する(issue #28の前段)。

e-Stat の匿名ダウンロードエンドポイントから直接xlsxを取得する(要ログイン不要)。
`fileKind=1` はHTTP 404のHTMLを返すため使わない(`fileKind=0` のみ検証済み)。

`scripts/fetch_meibo.py` と同じ設計方針を踏襲する:

- 冪等性: 既に `data/raw/` に同名ファイルがあり、かつそのSHA-256がメタJSON
  (`*.meta.json`)に記録済みのSHA-256と**一致するときだけ**再ダウンロードを
  スキップする。存在するだけでは信用しない。
- 一過性のネットワーク失敗を「取得できないファイル」として握り潰さない。
  失敗時は非ゼロ終了するだけで、失敗を記録した状態を `data/raw/` に残さない
  (メタJSONは成功時のみ書く)。
- リクエストURL自体はログに出さない(このURLにAPIキーは無いが習慣として踏襲)。

**HTTPステータスだけでは検証しない**(CLAUDE.md 全般方針: 200でもHTMLの
エラーページが返ることがある)。ダウンロード後に実際に openpyxl で開けるか
(=本物のxlsx/zipであるか)を確認し、開けなければ失敗として扱う
(メタJSONを書かず、非ゼロ終了)。

使い方:
    python scripts/fetch_census_age.py
    python scripts/fetch_census_age.py --url <別URL> --out data/raw/census_age_2020.xlsx

終了コード: 取得成功(または既存ファイルの再利用)=0、失敗=非ゼロ。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import requests

# Windows のコンソールでも日本語出力が文字化けしないようにする(fetch_meibo.pyに合わせる)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 令和2年国勢調査 人口等基本集計 表2-7(統計表ID 000032142410、fileKind=0=xlsx)。
# fileKind=1 はHTTP 404のHTMLを返すため使わない(issue #28で検証済み)。
DEFAULT_URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032142410&fileKind=0"
DEFAULT_OUT = Path("data/raw/census_age_2020_table2-7.xlsx")


def sha256_of(path: Path) -> str:
    """ファイルのSHA-256を計算する(大きいファイルでもメモリに全展開しない)。"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def meta_path_for(out_path: Path) -> Path:
    return out_path.with_name(out_path.name + ".meta.json")


def is_valid_xlsx(path: Path) -> bool:
    """openpyxlで実際に開けるかどうかで、本物のxlsxかを確認する。

    HTTP 200でもHTMLのエラーページが返ることがある(issue #28で
    fileKind=1が実際にそうだった)ため、ステータスコードだけでは
    判定しない。
    """
    try:
        wb = openpyxl.load_workbook(path, read_only=True)
        wb.close()
        return True
    except Exception:
        return False


def download(url: str, out_path: Path) -> None:
    """URLからxlsxを取得し、out_path に書き出す。

    ネットワークエラー・非2xxはここで例外として送出し、呼び出し側で
    非ゼロ終了に変換する(握り潰さない)。
    """
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # 中断時に不完全なファイルを本来のパスに残さないよう、一時ファイル経由で書く。
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    with tmp_path.open("wb") as f:
        f.write(response.content)
    tmp_path.replace(out_path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="令和2年国勢調査 表2-7(年齢5歳階級)のxlsxを取得する")
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
        print(f"エラー: xlsxの取得に失敗しました({type(e).__name__})。", file=sys.stderr)
        print("一時的な障害の可能性があるため、失敗をメタ情報として記録せず終了します。", file=sys.stderr)
        return 1

    if not is_valid_xlsx(out_path):
        print(
            f"エラー: 取得したファイルが本物のxlsxとして開けません(HTTP 200でもHTMLの"
            f"エラーページ等が返っている可能性): {out_path}",
            file=sys.stderr,
        )
        print("失敗をメタ情報として記録せず終了します。", file=sys.stderr)
        # 壊れたファイルが次回実行で「既存ファイル」として誤って再利用されないよう削除する。
        out_path.unlink(missing_ok=True)
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
