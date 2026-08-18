#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_population.py — 人口(分母)データの整備(issue #5)。

隣リポジトリ(visualize-regional-medical-care-for-2040)が既に厚生労働省
「2040年に向けた地域医療構想」の公表資料(R7/001723349.xlsx=②構想区域の
病床数等・R7/001722915.xlsx=①都道府県の病床数等)から抽出済みの
`data/processed/area_basic.csv`(339構想区域)・`data/processed/prefecture_basic.csv`
(47都道府県+「全国」)を入力に、このリポジトリで使う人口CSVを作る。

## やらないこと(推測で作らない)

年齢階級別人口・65歳以上人口は area_basic.csv に無いため、今回は出さない。
出すのは総人口(population_2020、2020年国勢調査)のみ。年齢階級別は e-Stat
からの取得が別途必要で未着手。

`iryoken2_A38-20.geojson`(335圏版、生のA38属性)には `A38b_007`〜`A38b_011`
という人口らしき数値属性があるが、各属性が何を指すか国土数値情報の仕様書で
確認していないため使わない(推測で列名を付けない。今後の手がかりとして
documents/DATA_SOURCES.md に1行だけ残す)。

## 検算(ハード。失敗したら非ゼロ終了)

1. published_fy=="R7" で絞った区域が339件・都道府県が47件(「全国」行は除く)
2. data/geo/iryoken2.geojson の area_code 集合と、人口CSVの area_code 集合が
   完全一致すること(片方にしか無いコードは全部列挙して失敗させる。
   issue #5「突合できなかったコードは握り潰さず監査表に出す」に対応)

区域人口の合計・都道府県人口の合計・prefecture_basic.csv の「全国」行
(pref_code="00")との差は、差があること自体は許容し、数値で報告するのみ
(ハード検算にはしない)。

使い方:
    python scripts/build_population.py
    python scripts/build_population.py --area-basic <path> --prefecture-basic <path> \\
        --iryoken2-geojson data/geo/iryoken2.geojson --out-dir data/processed

終了コード: 成功=0、入力ファイル不在・検算失敗などは非ゼロ。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import List

import pandas as pd

DEFAULT_AREA_BASIC = Path(
    "C:/Users/youki/codes/visualize-regional-medical-care-for-2040/data/processed/area_basic.csv"
)
DEFAULT_PREFECTURE_BASIC = Path(
    "C:/Users/youki/codes/visualize-regional-medical-care-for-2040/data/processed/prefecture_basic.csv"
)
DEFAULT_IRYOKEN2_GEOJSON = Path("data/geo/iryoken2.geojson")
DEFAULT_OUT_DIR = Path("data/processed")

# 元データの最終出典は 2020年国勢調査人口だが、直接取得したのは厚生労働省
# 「2040年に向けた地域医療構想」の公表資料(area_basic.csv/prefecture_basic.csv
# の元になった R7/001723349.xlsx・R7/001722915.xlsx)。取得日は隣リポジトリの
# doc/DATA_SOURCES.md に記録されている実際の取得日(2026-08-04)をそのまま使う
# (このスクリプトを実行した日ではなく、原典を取得した日を記録する)。
SOURCE_URL = "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000080850_00014.html"
RETRIEVED_ON = "2026-08-04"


def write_csv(path: Path, header: List[str], rows: List[List[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="area_basic.csv/prefecture_basic.csvから人口CSVを作る")
    parser.add_argument("--area-basic", type=Path, default=DEFAULT_AREA_BASIC, help="area_basic.csvのパス")
    parser.add_argument(
        "--prefecture-basic", type=Path, default=DEFAULT_PREFECTURE_BASIC, help="prefecture_basic.csvのパス"
    )
    parser.add_argument(
        "--iryoken2-geojson",
        type=Path,
        default=DEFAULT_IRYOKEN2_GEOJSON,
        help="area_code突合に使うiryoken2.geojson(scripts/build_geo.Rの出力)のパス",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="出力先ディレクトリ")
    return parser.parse_args(argv)


def load_geojson_area_codes(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [str(feat["properties"]["area_code"]) for feat in data["features"]]


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    if not args.area_basic.exists():
        print(f"エラー: area_basic.csvが見つかりません: {args.area_basic}", file=sys.stderr)
        print(
            "隣リポジトリ visualize-regional-medical-care-for-2040 の\n"
            "  data/processed/area_basic.csv\n"
            "を --area-basic <path> で指定してください。",
            file=sys.stderr,
        )
        return 1
    if not args.prefecture_basic.exists():
        print(f"エラー: prefecture_basic.csvが見つかりません: {args.prefecture_basic}", file=sys.stderr)
        print(
            "隣リポジトリ visualize-regional-medical-care-for-2040 の\n"
            "  data/processed/prefecture_basic.csv\n"
            "を --prefecture-basic <path> で指定してください。",
            file=sys.stderr,
        )
        return 1
    if not args.iryoken2_geojson.exists():
        print(f"エラー: iryoken2.geojsonが見つかりません: {args.iryoken2_geojson}", file=sys.stderr)
        print(
            "先に Rscript scripts/build_geo.R を実行して data/geo/iryoken2.geojson を"
            "生成するか、--iryoken2-geojson <path> で既存のファイルを指定してください。",
            file=sys.stderr,
        )
        return 1

    # area_code・pref_code はゼロ埋め文字列のまま扱う(issue #4/#5共通の既知の罠)。
    # dtype=str で読むことで先頭ゼロの欠落を防ぐ。
    area_basic = pd.read_csv(args.area_basic, dtype=str)
    prefecture_basic = pd.read_csv(args.prefecture_basic, dtype=str)

    area_r7 = area_basic[area_basic["published_fy"] == "R7"].copy()
    pref_r7_all = prefecture_basic[prefecture_basic["published_fy"] == "R7"].copy()
    # 「全国」行(pref_code="00")は都道府県の出力に含めない(合計検算にのみ使う)。
    pref_r7 = pref_r7_all[pref_r7_all["pref_code"] != "00"].copy()
    national_row = pref_r7_all[pref_r7_all["pref_code"] == "00"]

    if len(area_r7) != 339:
        print(
            f"エラー: published_fy=='R7' の区域が339件ちょうどではありません(実測 {len(area_r7)} 件)。",
            file=sys.stderr,
        )
        return 1
    if len(pref_r7) != 47:
        print(
            f"エラー: published_fy=='R7' かつ「全国」を除いた都道府県が47件ちょうどではありません"
            f"(実測 {len(pref_r7)} 件)。",
            file=sys.stderr,
        )
        return 1
    if len(national_row) != 1:
        print(
            f"エラー: prefecture_basic.csv の「全国」行(pref_code='00', published_fy='R7')が"
            f"ちょうど1件見つかりません(実測 {len(national_row)} 件)。",
            file=sys.stderr,
        )
        return 1

    # --- population_iryoken2.csv -------------------------------------------
    area_r7 = area_r7.sort_values("area_code")
    area_rows = [
        [
            row["area_code"],
            row["area_name"],
            row["pref_code"],
            row["pref_name"],
            int(row["population_2020"]),
            SOURCE_URL,
            RETRIEVED_ON,
        ]
        for _, row in area_r7.iterrows()
    ]
    area_out_path = args.out_dir / "population_iryoken2.csv"
    write_csv(
        area_out_path,
        ["area_code", "area_name", "pref_code", "pref_name", "population_2020", "source", "retrieved_on"],
        area_rows,
    )

    # --- population_prefecture.csv ------------------------------------------
    pref_r7 = pref_r7.sort_values("pref_code")
    pref_rows = [
        [
            row["pref_code"],
            row["pref_name"],
            int(row["population_2020"]),
            SOURCE_URL,
            RETRIEVED_ON,
        ]
        for _, row in pref_r7.iterrows()
    ]
    pref_out_path = args.out_dir / "population_prefecture.csv"
    write_csv(
        pref_out_path,
        ["pref_code", "pref_name", "population_2020", "source", "retrieved_on"],
        pref_rows,
    )

    print("生成完了:")
    print(f"  {area_out_path}({len(area_rows)}件)")
    print(f"  {pref_out_path}({len(pref_rows)}件)")
    print()

    # --- ハード検算: area_code集合の突合 ------------------------------------
    geo_codes = set(load_geojson_area_codes(args.iryoken2_geojson))
    csv_codes = set(area_r7["area_code"])

    only_in_geo = sorted(geo_codes - csv_codes)
    only_in_csv = sorted(csv_codes - geo_codes)

    print(f"area_code突合: geojson {len(geo_codes)}件 / 人口CSV {len(csv_codes)}件")
    ok = True
    if only_in_geo:
        ok = False
        print(f"エラー: {args.iryoken2_geojson} にのみ存在する area_code({len(only_in_geo)}件): {only_in_geo}")
    if only_in_csv:
        ok = False
        print(f"エラー: 人口CSVにのみ存在する area_code({len(only_in_csv)}件): {only_in_csv}")
    if not only_in_geo and not only_in_csv:
        print("area_code突合: 完全一致(片方にしか無いコードは無し)。")
    print()

    # --- 監査(ハードではない。差があれば数値で報告するのみ) --------------------
    area_total = sum(r[4] for r in area_rows)
    pref_total = sum(r[2] for r in pref_rows)
    national_pop = int(national_row.iloc[0]["population_2020"])

    print("人口合計の監査:")
    print(f"  区域(population_iryoken2.csv)の合計: {area_total}")
    print(f"  都道府県(population_prefecture.csv)の合計: {pref_total}")
    print(f"  prefecture_basic.csv の「全国」行(pref_code=00): {national_pop}")
    print(f"  差(区域合計 - 都道府県合計): {area_total - pref_total}")
    print(f"  差(都道府県合計 - 全国行): {pref_total - national_pop}")
    print(f"  差(区域合計 - 全国行): {area_total - national_pop}")

    if not ok:
        print()
        print("検算NG: area_code の突合に失敗しました。")
        return 1

    print()
    print("検算OK: すべてのハード検算に合格しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
