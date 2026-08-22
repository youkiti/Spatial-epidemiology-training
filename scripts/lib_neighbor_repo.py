#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lib_neighbor_repo.py — 隣リポジトリの置き場所の解決(issue #51)。

このリポジトリのデータ整備スクリプトは、一部の入力を隣リポジトリ
visualize-regional-medical-care-for-2040(同一著者)の出力に依存している。
置き場所は利用者ごとに違うので既定値は持たせず、環境変数 NEIGHBOR_REPO で
受け取る。個別のパス引数(--area-basic など)が指定されていればそちらを優先する。

**どちらも無いときに個人環境の絶対パスへフォールバックしないこと**が
このモジュールの要点。以前は開発機のホームディレクトリ配下の絶対パスが
既定値だったため、クリーンクローンした利用者には「存在しないパスが
見つかりません」としか出ず、どこから入手すればよいかが分からなかった。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

ENV_VAR = "NEIGHBOR_REPO"

REPO_URL = "https://github.com/youkiti/visualize-regional-medical-care-for-2040"


class NeighborRepoNotConfigured(RuntimeError):
    """NEIGHBOR_REPO も個別のパス引数も指定されていないときに送出する。"""


def guidance(relative: str, option: str) -> str:
    """入手手順を案内するエラーメッセージを組み立てる。"""
    return (
        "隣リポジトリ visualize-regional-medical-care-for-2040 の\n"
        f"  {relative}\n"
        "が必要です。次のどちらかで場所を指定してください。\n"
        f"  1. 環境変数 {ENV_VAR} に隣リポジトリのルートを設定する\n"
        f"     (例: {ENV_VAR}=../visualize-regional-medical-care-for-2040)\n"
        f"  2. {option} <path> でファイルを直接指定する\n"
        f"隣リポジトリの入手元と、この入力の生成手順は\n"
        f"  {REPO_URL}\n"
        "および documents/DATA_SOURCES.md を参照。"
    )


def resolve(cli_value: Optional[Union[str, Path]], relative: str, option: str) -> Path:
    """個別指定 → 環境変数 NEIGHBOR_REPO の順にパスを解決する。

    どちらも無ければ ``NeighborRepoNotConfigured`` を送出する(既定値として
    特定の開発機の絶対パスを返さない)。
    """
    if cli_value is not None:
        return Path(cli_value)
    root = os.environ.get(ENV_VAR)
    if root:
        return Path(root) / relative
    raise NeighborRepoNotConfigured(guidance(relative, option))
