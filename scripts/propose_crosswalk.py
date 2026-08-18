#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
propose_crosswalk.py — `scripts/link_facilities.py` で自動割付できなかった行
(`match_status=unmatched`)について、`data/curated/facility_crosswalk.csv` を
手で埋めるための候補を提案する(issue #9 の名寄せチャンク)。

**crosswalk本体はこのスクリプトでは作らない。** あくまで候補の提案までで、
crosswalkに何を書くかの判断は commander が行う。

## 何をするか

1. `data/processed/facility_geo_audit.csv`(`link_facilities.py`の出力)から
   `match_status=unmatched` の行を集める。
2. 各行について、`data/interim/facility_reference.csv` の参照点のうち、
   同じ都道府県(名簿側の`pref_name`を`data/geo/prefecture.geojson`で引く)の
   ものだけを対象に、以下の順で最大3件の候補を探す:
     a. **前方一致**: 名簿の正規化名が4文字以上で、参照点の正規化名が
        それで始まるもの(かつ完全一致でない)。正規化名の**短い順**に並べる。
        大学名にこれが効く(例:「長崎大学」→「長崎大学病院」)。
     b. 前方一致が0件なら `difflib.get_close_matches`(cutoff=0.68)で
        最大3件。`method`列に類似度(SequenceMatcher比)を入れる。
3. `data/interim/crosswalk_proposals.csv`(gitignore済みの`data/interim/`配下。
   個人名は含まないが加工中間物として扱う)に、専門医数の多い順に書き出す。

## 前方一致の最短候補が正解とは限らない(注意)

前方一致は「短い順」に並べているが、**最短候補が必ずしも正解ではない**。
実測で確認した例: `大阪大学` の最短候補は歯学部附属病院(`大阪大学歯学部附属病院`)
になる(医学部附属病院より先に来る)。長崎大学のように最短候補がそのまま
正解になる例もあれば、大阪大学のように紛らわしい例もあるため、**自動採用は
せず、あくまで人が選ぶための提案に留める**。

必要環境: Python 3.9+(追加依存なし。標準ライブラリのみ。`difflib`は標準ライブラリ)

使い方:
    PYTHONUTF8=1 python scripts/propose_crosswalk.py

終了コード: 正常終了0、入力が見つからない等のエラー1
"""

from __future__ import annotations

import argparse
import csv
import difflib
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# scripts/lib_facility_name.py・scripts/link_facilities.py は同じ scripts/ ディレクトリにある。
# 実行時のカレントディレクトリに依存させないよう明示的にパスを追加してから import する。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_facility_name  # noqa: E402 (パス追加の後に import する必要がある)
import link_facilities  # noqa: E402 (同上。プレフィックス→都道府県コードの読み込み等を再利用する)

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_AUDIT_CSV = REPO_ROOT / "data" / "processed" / "facility_geo_audit.csv"
DEFAULT_FACILITY_REFERENCE_CSV = REPO_ROOT / "data" / "interim" / "facility_reference.csv"
DEFAULT_PREFECTURE_GEOJSON = REPO_ROOT / "data" / "geo" / "prefecture.geojson"
DEFAULT_IRYOKEN2_GEOJSON = REPO_ROOT / "data" / "geo" / "iryoken2.geojson"
DEFAULT_OUT_CSV = REPO_ROOT / "data" / "interim" / "crosswalk_proposals.csv"

PREFIX_MIN_LEN = 4  # 名簿側の正規化名がこの文字数未満なら前方一致を試さない
DIFFLIB_CUTOFF = 0.68
MAX_CANDIDATES = 3

OUT_HEADER = [
    "n_specialists",
    "pref_name",
    "facility_name",
    "rank",
    "candidate_facility_name",
    "candidate_iryoken2_code",
    "candidate_iryoken2_name",
    "candidate_source",
    "method",
]


def read_unmatched_rows(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {"pref_name": r["pref_name"], "facility_name": r["facility_name"], "n_specialists": int(r["n_specialists"])}
            for r in reader
            if r["match_status"] == "unmatched"
        ]


def build_pref_pool(refs: List[dict]) -> Dict[str, List[dict]]:
    """`pref_code -> 参照点のリスト` の索引(医療情報ネット・P04を区別せず全ソース)。"""
    pool: Dict[str, List[dict]] = defaultdict(list)
    for ref in refs:
        pref_code = link_facilities.ref_pref_code(ref)
        if pref_code:
            pool[pref_code].append(ref)
    return pool


def find_prefix_candidates(normalized: str, pool: List[dict]) -> List[dict]:
    """名簿の正規化名が4文字以上で、参照点の正規化名がそれで始まるもの
    (完全一致は除く)を、参照点の正規化名が短い順に返す。
    """
    if len(normalized) < PREFIX_MIN_LEN:
        return []
    matches = [ref for ref in pool if ref["facility_name_normalized"] != normalized and ref["facility_name_normalized"].startswith(normalized)]
    matches.sort(key=lambda ref: len(ref["facility_name_normalized"]))
    return matches[:MAX_CANDIDATES]


def find_difflib_candidates(normalized: str, pool: List[dict]) -> List[tuple]:
    """`difflib.get_close_matches`(cutoff=0.68)による候補を返す。
    戻り値は `(ref, ratio)` のタプルのリスト(類似度が高い順、最大3件)。
    """
    normalized_to_refs: Dict[str, List[dict]] = defaultdict(list)
    for ref in pool:
        if ref["facility_name_normalized"]:
            normalized_to_refs[ref["facility_name_normalized"]].append(ref)
    close = difflib.get_close_matches(normalized, list(normalized_to_refs.keys()), n=MAX_CANDIDATES, cutoff=DIFFLIB_CUTOFF)
    out = []
    for name in close:
        ratio = difflib.SequenceMatcher(None, normalized, name).ratio()
        # 同じ正規化名を持つ参照点が複数あっても、提案は代表1件でよい(候補提示が目的で自動採用ではないため)。
        out.append((normalized_to_refs[name][0], ratio))
    return out


def build_proposals(unmatched: List[dict], pref_name_to_code: Dict[str, str], pref_pool: Dict[str, List[dict]], area_code_to_name: Dict[str, str]) -> List[dict]:
    proposals: List[dict] = []
    for row in unmatched:
        pref_code = pref_name_to_code.get(row["pref_name"])
        pool = pref_pool.get(pref_code, []) if pref_code else []
        normalized = lib_facility_name.normalize_facility_name(row["facility_name"])

        prefix_matches = find_prefix_candidates(normalized, pool)
        if prefix_matches:
            for rank, ref in enumerate(prefix_matches, start=1):
                proposals.append(
                    {
                        "n_specialists": row["n_specialists"],
                        "pref_name": row["pref_name"],
                        "facility_name": row["facility_name"],
                        "rank": rank,
                        "candidate_facility_name": ref["facility_name"],
                        "candidate_iryoken2_code": ref["iryoken2_code"],
                        "candidate_iryoken2_name": area_code_to_name.get(ref["iryoken2_code"], ""),
                        "candidate_source": ref["source"],
                        "method": "prefix",
                    }
                )
        else:
            for rank, (ref, ratio) in enumerate(find_difflib_candidates(normalized, pool), start=1):
                proposals.append(
                    {
                        "n_specialists": row["n_specialists"],
                        "pref_name": row["pref_name"],
                        "facility_name": row["facility_name"],
                        "rank": rank,
                        "candidate_facility_name": ref["facility_name"],
                        "candidate_iryoken2_code": ref["iryoken2_code"],
                        "candidate_iryoken2_name": area_code_to_name.get(ref["iryoken2_code"], ""),
                        "candidate_source": ref["source"],
                        "method": f"difflib:{ratio:.2f}",
                    }
                )
    return proposals


def write_proposals_csv(path: Path, proposals: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(OUT_HEADER)
        for p in proposals:
            writer.writerow([p[col] for col in OUT_HEADER])


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="未割付の名簿行について crosswalk 候補を提案する(crosswalk本体は作らない)")
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT_CSV)
    parser.add_argument("--facility-reference", type=Path, default=DEFAULT_FACILITY_REFERENCE_CSV)
    parser.add_argument("--prefecture-geojson", type=Path, default=DEFAULT_PREFECTURE_GEOJSON)
    parser.add_argument("--iryoken2-geojson", type=Path, default=DEFAULT_IRYOKEN2_GEOJSON)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_CSV)
    args = parser.parse_args(argv)

    required = [args.audit, args.facility_reference, args.prefecture_geojson, args.iryoken2_geojson]
    missing = [p for p in required if not p.exists()]
    if missing:
        for p in missing:
            print(f"エラー: {p} が見つかりません。先に build_facility_reference.py / link_facilities.py を実行してください。")
        return 1

    unmatched = read_unmatched_rows(args.audit)
    unmatched.sort(key=lambda r: -r["n_specialists"])
    refs = link_facilities.load_facility_reference(args.facility_reference)
    pref_name_to_code = link_facilities.load_prefecture_geojson(args.prefecture_geojson)
    area_code_to_name, _area_code_to_pref_name = link_facilities.load_iryoken2_geojson(args.iryoken2_geojson)
    pref_pool = build_pref_pool(refs)

    print(f"未割付: {len(unmatched)}行 / {sum(r['n_specialists'] for r in unmatched)}名")

    proposals = build_proposals(unmatched, pref_name_to_code, pref_pool, area_code_to_name)
    write_proposals_csv(args.out, proposals)

    with_candidates = len({(p["pref_name"], p["facility_name"]) for p in proposals})
    print(f"候補あり: {with_candidates}/{len(unmatched)}行")
    prefix_count = len({(p["pref_name"], p["facility_name"]) for p in proposals if p["method"] == "prefix"})
    print(f"  うち前方一致で候補が出た行: {prefix_count}行")
    print(f"出力: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
