#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_facility_linkage.py — `scripts/link_facilities.py` が行った施設名寄せ・
二次医療圏割付(issue #9)の受け入れ条件検査ツール。

`data/processed/facility_geo_audit.csv`(名簿本体1,059行の監査表)・
`data/processed/specialists_iryoken2.csv`(二次医療圏集計)・
`data/curated/facility_crosswalk.csv`(人手の対応づけ)が、互いに整合し、
かつ人数を消したり作ったりしていないことを、以下の8条件で検査する。

  条件1: 監査表の網羅性。`facility_geo_audit.csv` の (pref_name, facility_name)
         の集合が `specialists_facility.csv` と完全一致し、行数も一致する。
  条件2: 人数の保存。監査表の n_specialists 合計が名簿(specialists_facility.csv)
         と一致し、かつ matched + unmatched + excluded + unassignable の
         人数合計が監査表の合計と一致する(想定外の match_status が無いことも
         この時点で検出される)。
  条件3: 医療圏集計の整合。`specialists_iryoken2.csv` の合計 + (matched だが
         iryoken2_code が空の行の人数) = matched の人数合計であること。
         かつ、監査表から医療圏ごとに再集計した値が `specialists_iryoken2.csv`
         と1件残らず一致すること。
  条件4: 医療圏の件数。`specialists_iryoken2.csv` が `iryoken2.geojson` の
         339区域を過不足なく含む(0人の区域も行として存在する)。
  条件5: 県の整合。割付済み行の iryoken2_code の先頭2桁が、名簿の pref_name に
         対応する都道府県コードと一致する。
  条件6: 都道府県レベルとの関係。監査表を都道府県に畳んだ人数(全match_status
         込み。「名簿本体の人数」そのもの)が `specialists_reconciliation.csv`
         の n_roster_body と1件残らず一致する。ずれたら名寄せが人数を
         作ったか消したかのどちらか。
  条件7: 欠測の偏り。県別の割付率と、人口10万対専門医数(分子=名簿本体の
         県別人数、分母= population_prefecture.csv の population_2020)の
         Spearman順位相関を計算する。|ρ| >= RHO_THRESHOLD なら条件を
         満たさないと判定する。「海外」は分母データが無いため除外する。

         割付率の分子は「match_status=="matched" かつ iryoken2_code が
         非空」の専門医数(全体は名簿本体の県別人数)。この条件が検査したいのは
         「地図に載らなかったこと」が結果と相関していないかであり、matched
         であっても iryoken2_code が空の行(実例: 長崎県 サン・レモ
         リハビリ病院、2名。参照点の座標がどの医療圏ポリゴンにも入らない)は
         地図には載らない。よって分子から除く(matched全体を分子にすると、
         検査したい対象と計算対象がわずかにずれる)。

         閾値 RHO_THRESHOLD=0.3 の根拠: 教材が戒めているのは「欠測パターンが
         地図の模様を作ってしまう」ことそのものである(CLAUDE.md 「教材が
         最重要視している論点」)。割付率(=欠測の起きやすさ)と専門医密度
         (=地図が見せたい量)のあいだに強い相関があれば、密度地図の模様の
         少なくとも一部は「割付できたかどうか」を映しているにすぎず、
         実際の偏在を表しているとは言えなくなる。0.3 は相関係数の解釈で
         広く使われる「弱い相関」の上限の目安(それ未満は無視できる程度と
         扱われることが多い)であり、これを跨いだら教材の主張の前提が
         崩れるため、検算のしきい値として採用した。
  条件8: crosswalkの健全性。`data/curated/facility_crosswalk.csv` の全行が
         監査表で意図どおりに反映されている(basis と assignment_basis が
         一致し、excluded_non_care/unassignable の行が matched になっていない)。

条件7のSpearman順位相関は、閾値判定とは別に値そのものを必ず標準出力に出す。

依存関係の扱い: このスクリプトは標準ライブラリのみを使う(pytest はこの
リポジトリに無く、CIも `mkdocs build --strict` しか回していないため、検算は
「自己完結して終了コードで判定するスクリプト」にする方針。requirements.txt は
変更しない)。ただし `scripts/link_facilities.py` の一部関数(GeoJSONの読み込みや
basis→match_status の対応表)は import して再利用する
(`scripts/verify_simulation.py` が `simulate_spatial_data.py` を import する
のと同じ作法。link_facilities.py 自体は変更しない)。

使い方:
    PYTHONUTF8=1 python scripts/verify_facility_linkage.py

終了コード: 受け入れ条件1〜8すべて満たす=0、いずれか満たさない=1
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

# link_facilities.py は同じ scripts/ ディレクトリにある。python
# scripts/verify_facility_linkage.py のようにスクリプトとして実行された場合、
# そのディレクトリは既に sys.path[0] に入っているはずだが、実行時のカレント
# ディレクトリに依存させないよう明示的にも追加しておく。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import link_facilities as link  # noqa: E402 (パス追加の後に import する必要がある)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_AUDIT_CSV = REPO_ROOT / "data" / "processed" / "facility_geo_audit.csv"
DEFAULT_SPECIALISTS_FACILITY_CSV = REPO_ROOT / "data" / "processed" / "specialists_facility.csv"
DEFAULT_IRYOKEN2_CSV = REPO_ROOT / "data" / "processed" / "specialists_iryoken2.csv"
DEFAULT_RECONCILIATION_CSV = REPO_ROOT / "data" / "processed" / "specialists_reconciliation.csv"
DEFAULT_POPULATION_PREFECTURE_CSV = REPO_ROOT / "data" / "processed" / "population_prefecture.csv"
DEFAULT_PREFECTURE_GEOJSON = REPO_ROOT / "data" / "geo" / "prefecture.geojson"
DEFAULT_IRYOKEN2_GEOJSON = REPO_ROOT / "data" / "geo" / "iryoken2.geojson"
DEFAULT_CROSSWALK_CSV = REPO_ROOT / "data" / "curated" / "facility_crosswalk.csv"

RHO_THRESHOLD = 0.3  # 条件7のしきい値。根拠はモジュールdocstring参照
MAX_LISTED = 20  # 不一致等を列挙するときの表示上限(標準出力が肥大化しないように)


# ===========================================================================
# 入出力
# ===========================================================================


def read_csv_rows(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ===========================================================================
# 相関係数(標準ライブラリのみでSpearman順位相関を計算する)
# ===========================================================================


def _rank(values: List[float]) -> List[float]:
    """タイは平均順位にする(scipy.stats.spearmanr の既定と同じ扱い)。"""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _pearson(a: List[float], b: List[float]) -> float:
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((x - mb) ** 2 for x in b))
    if da == 0.0 or db == 0.0:
        return 0.0
    return num / (da * db)


def spearman(a: List[float], b: List[float]) -> float:
    """Spearman順位相関(タイは平均順位で処理し、順位に対するPearson相関を返す)。"""
    return _pearson(_rank(a), _rank(b))


# ===========================================================================
# 条件1〜8
# ===========================================================================


def check_condition1(audit_rows: List[dict], roster_rows: List[dict]) -> bool:
    audit_keys = [(r["pref_name"], r["facility_name"]) for r in audit_rows]
    roster_keys = [(r["pref_name"], r["facility_name"]) for r in roster_rows]
    same_len = len(audit_rows) == len(roster_rows)
    same_set = set(audit_keys) == set(roster_keys)

    print(f"  監査表(facility_geo_audit.csv): {len(audit_rows)}行")
    print(f"  名簿(specialists_facility.csv): {len(roster_rows)}行")
    print(f"  行数が一致: {'○' if same_len else '■ 不一致'}")
    print(f"  (pref_name, facility_name)の集合が完全一致: {'○' if same_set else '■ 不一致'}")
    if not same_set:
        only_audit = sorted(set(audit_keys) - set(roster_keys))
        only_roster = sorted(set(roster_keys) - set(audit_keys))
        if only_audit:
            print(f"    監査表のみに存在({len(only_audit)}件、先頭{MAX_LISTED}件): {only_audit[:MAX_LISTED]}")
        if only_roster:
            print(f"    名簿のみに存在({len(only_roster)}件、先頭{MAX_LISTED}件): {only_roster[:MAX_LISTED]}")

    ok = same_len and same_set
    print(f"  判定: {'○ 条件を満たす' if ok else '■ 条件を満たさない'}")
    return ok


def check_condition2(audit_rows: List[dict], roster_rows: List[dict]) -> bool:
    audit_total = sum(int(r["n_specialists"]) for r in audit_rows)
    roster_total = sum(int(r["n_specialists"]) for r in roster_rows)

    known_statuses = ("matched", "unmatched", "excluded", "unassignable")
    status_totals: Counter = Counter()
    for r in audit_rows:
        status_totals[r["match_status"]] += int(r["n_specialists"])
    unknown_statuses = sorted(set(status_totals) - set(known_statuses))
    partition_sum = sum(status_totals[s] for s in known_statuses)

    mapped_n = sum(
        int(r["n_specialists"]) for r in audit_rows if r["match_status"] == "matched" and r["iryoken2_code"]
    )

    print(f"  監査表のn_specialists合計: {audit_total}名 / 名簿(specialists_facility.csv)合計: {roster_total}名")
    for s in known_statuses:
        print(f"    {s}: {status_totals.get(s, 0)}名")
        if s == "matched":
            # 条件3で検査する値と突き合わせやすいように、matchedのうち実際に
            # 二次医療圏の地図に載る人数(iryoken2_codeが非空)も併記する。
            print(f"      うち医療圏に載る(iryoken2_codeが非空): {mapped_n}名")
    if unknown_statuses:
        print(f"    想定外のmatch_status: {unknown_statuses}")
    print(f"  matched+unmatched+excluded+unassignable = {partition_sum}名")

    totals_match = audit_total == roster_total
    partition_ok = partition_sum == audit_total and not unknown_statuses
    print(f"  監査表合計と名簿合計が一致: {'○' if totals_match else '■ 不一致'}")
    print(f"  match_statusの内訳が監査表合計を過不足なく分割: {'○' if partition_ok else '■ 不一致'}")

    ok = totals_match and partition_ok
    print(f"  判定: {'○ 条件を満たす' if ok else '■ 条件を満たさない'}")
    return ok


def check_condition3(audit_rows: List[dict], iryoken2_rows: List[dict]) -> bool:
    matched_rows = [r for r in audit_rows if r["match_status"] == "matched"]
    matched_total = sum(int(r["n_specialists"]) for r in matched_rows)
    empty_code_total = sum(int(r["n_specialists"]) for r in matched_rows if not r["iryoken2_code"])
    iryoken2_total = sum(int(r["n_specialists"]) for r in iryoken2_rows)

    print(f"  matched合計: {matched_total}名(うちiryoken2_codeが空: {empty_code_total}名)")
    print(f"  specialists_iryoken2.csv合計: {iryoken2_total}名")
    balance_ok = (iryoken2_total + empty_code_total) == matched_total
    print(
        f"  iryoken2合計 + 空コード分 = matched合計 か: "
        f"{iryoken2_total} + {empty_code_total} = {iryoken2_total + empty_code_total}"
        f"({'○ matched合計と一致' if balance_ok else '■ matched合計と不一致'})"
    )

    recomputed: Counter = Counter()
    for r in matched_rows:
        if r["iryoken2_code"]:
            recomputed[r["iryoken2_code"]] += int(r["n_specialists"])
    mismatches = []
    for r in iryoken2_rows:
        code = r["iryoken2_code"]
        expected = recomputed.get(code, 0)
        actual = int(r["n_specialists"])
        if expected != actual:
            mismatches.append((code, r["iryoken2_name"], expected, actual))
    print(f"  監査表からの再集計と specialists_iryoken2.csv の突合: 不一致 {len(mismatches)}件")
    for code, name, expected, actual in mismatches[:MAX_LISTED]:
        print(f"    {code} {name}: 監査表からの再集計={expected} / ファイル記載={actual}")

    ok = balance_ok and not mismatches
    print(f"  判定: {'○ 条件を満たす' if ok else '■ 条件を満たさない'}")
    return ok


def check_condition4(iryoken2_rows: List[dict], area_code_to_name: Dict[str, str]) -> bool:
    iry_codes = {r["iryoken2_code"] for r in iryoken2_rows}
    geo_codes = set(area_code_to_name)
    only_iry = sorted(iry_codes - geo_codes)
    only_geo = sorted(geo_codes - iry_codes)
    same_len = len(iryoken2_rows) == len(geo_codes)

    print(f"  specialists_iryoken2.csv: {len(iryoken2_rows)}行 / iryoken2.geojson: {len(geo_codes)}区域")
    print(f"  行数が339区域と一致: {'○' if same_len else '■ 不一致'}")
    if only_iry:
        print(f"    specialists_iryoken2.csvのみに存在するコード: {only_iry}")
    if only_geo:
        print(f"    iryoken2.geojsonのみに存在する(specialists_iryoken2.csvに欠落した)コード: {only_geo}")

    ok = same_len and not only_iry and not only_geo
    print(f"  判定: {'○ 条件を満たす' if ok else '■ 条件を満たさない'}")
    return ok


def check_condition5(audit_rows: List[dict], pref_name_to_code: Dict[str, str]) -> bool:
    mismatches = []
    checked = 0
    for r in audit_rows:
        if r["match_status"] != "matched" or not r["iryoken2_code"]:
            continue
        checked += 1
        expected_pref_code = pref_name_to_code.get(r["pref_name"])
        actual_prefix = r["iryoken2_code"][:2]
        if expected_pref_code is None or actual_prefix != expected_pref_code:
            mismatches.append((r["pref_name"], r["facility_name"], r["iryoken2_code"], expected_pref_code))

    print(f"  割付済み(matched かつ iryoken2_code非空)行: {checked}件を検査")
    print(f"  不一致: {len(mismatches)}件")
    for pref_name, facility_name, code, expected in mismatches[:MAX_LISTED]:
        print(
            f"    {pref_name} / {facility_name}: iryoken2_code={code}(先頭2桁={code[:2]})"
            f" / 名簿pref_nameが期待するpref_code={expected}"
        )

    ok = not mismatches
    print(f"  判定: {'○ 条件を満たす' if ok else '■ 条件を満たさない'}")
    return ok


def check_condition6(audit_rows: List[dict], reconciliation_rows: List[dict]) -> bool:
    pref_totals: Counter = Counter()
    for r in audit_rows:
        pref_totals[r["pref_name"]] += int(r["n_specialists"])

    mismatches = []
    for r in reconciliation_rows:
        pref_name = r["pref_name"]
        expected = int(r["n_roster_body"])
        actual = pref_totals.get(pref_name, 0)
        if expected != actual:
            mismatches.append((pref_name, actual, expected))

    print(f"  specialists_reconciliation.csv: {len(reconciliation_rows)}都道府県(「海外」含む)を検査")
    print(f"  不一致: {len(mismatches)}件")
    for pref_name, actual, expected in mismatches[:MAX_LISTED]:
        print(f"    {pref_name}: 監査表を畳んだ人数={actual} / n_roster_body={expected}")

    ok = not mismatches
    print(f"  判定: {'○ 条件を満たす' if ok else '■ 条件を満たさない'}")
    return ok


def check_condition7(audit_rows: List[dict], population_rows: List[dict]) -> bool:
    pop_map = {r["pref_name"]: int(r["population_2020"]) for r in population_rows}

    total: Counter = Counter()
    mapped: Counter = Counter()  # 分子: matched かつ iryoken2_code が非空(=実際に地図に載る人数)
    for r in audit_rows:
        if r["pref_name"] == "海外":
            continue
        total[r["pref_name"]] += int(r["n_specialists"])
        if r["match_status"] == "matched" and r["iryoken2_code"]:
            mapped[r["pref_name"]] += int(r["n_specialists"])

    prefs = sorted(total)
    missing_pop = [p for p in prefs if p not in pop_map]
    if missing_pop:
        print(f"  エラー: population_prefecture.csvに存在しない都道府県があります: {missing_pop}")
        print("  判定: ■ 条件を満たさない(相関を計算できない)")
        return False

    rate = [mapped[p] / total[p] for p in prefs]
    density = [total[p] / pop_map[p] * 100000 for p in prefs]
    rho = spearman(rate, density)

    print(f"  対象: {len(prefs)}都道府県(「海外」は分母データが無いため除外)")
    print(
        "  割付率(matched かつ iryoken2_code非空、つまり実際に地図に載る人数/名簿本体人数)"
        " と 人口10万対専門医数(名簿本体ベース) の Spearman順位相関:"
    )
    print(f"    ρ = {rho:.4f}")
    print(f"  しきい値: |ρ| < {RHO_THRESHOLD}(欠測が地図の模様を作っていないことの確認。根拠はdocstring参照)")

    ok = abs(rho) < RHO_THRESHOLD
    print(f"  判定: {'○ 条件を満たす(欠測パターンとの相関は弱い)' if ok else '■ 条件を満たさない(|ρ|がしきい値以上)'}")
    return ok


def check_condition8(audit_rows: List[dict], crosswalk_rows: List[dict]) -> bool:
    audit_index = {(r["pref_name"], r["facility_name"]): r for r in audit_rows}
    problems: List[str] = []

    for row in crosswalk_rows:
        pref_name = (row.get("pref_name") or "").strip()
        facility_name = (row.get("facility_name") or "").strip()
        basis = (row.get("basis") or "").strip()
        key = (pref_name, facility_name)

        audit_row = audit_index.get(key)
        if audit_row is None:
            problems.append(f"{key}: crosswalkにあるが監査表に存在しない")
            continue

        if audit_row["assignment_basis"] != basis:
            problems.append(
                f"{key}: crosswalkのbasis={basis!r} と監査表のassignment_basis="
                f"{audit_row['assignment_basis']!r} が食い違う"
            )
            continue

        expected_status = link.BASIS_TO_MATCH_STATUS.get(basis)
        if expected_status is not None:
            # excluded_non_care / unassignable は、その専用のmatch_statusになって
            # いなければならない(誤ってmatchedのままになっていないかを検査)。
            if audit_row["match_status"] != expected_status:
                problems.append(
                    f"{key}: basis={basis!r} は match_status={expected_status!r} のはずが、"
                    f"監査表では{audit_row['match_status']!r}になっている"
                )
        else:
            if audit_row["match_status"] != "matched":
                problems.append(
                    f"{key}: basis={basis!r} は matched のはずが、"
                    f"監査表では{audit_row['match_status']!r}になっている"
                )

    print(f"  data/curated/facility_crosswalk.csv: {len(crosswalk_rows)}行を検査")
    print(f"  問題: {len(problems)}件")
    for p in problems[:MAX_LISTED]:
        print(f"    {p}")

    ok = not problems
    print(f"  判定: {'○ 条件を満たす' if ok else '■ 条件を満たさない'}")
    return ok


# ===========================================================================
# main
# ===========================================================================


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="施設名寄せ・二次医療圏割付(issue #9)の受け入れ条件検査")
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT_CSV)
    parser.add_argument("--specialists-facility", type=Path, default=DEFAULT_SPECIALISTS_FACILITY_CSV)
    parser.add_argument("--iryoken2", type=Path, default=DEFAULT_IRYOKEN2_CSV)
    parser.add_argument("--reconciliation", type=Path, default=DEFAULT_RECONCILIATION_CSV)
    parser.add_argument("--population-prefecture", type=Path, default=DEFAULT_POPULATION_PREFECTURE_CSV)
    parser.add_argument("--prefecture-geojson", type=Path, default=DEFAULT_PREFECTURE_GEOJSON)
    parser.add_argument("--iryoken2-geojson", type=Path, default=DEFAULT_IRYOKEN2_GEOJSON)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK_CSV)
    args = parser.parse_args(argv)

    required = [
        args.audit,
        args.specialists_facility,
        args.iryoken2,
        args.reconciliation,
        args.population_prefecture,
        args.prefecture_geojson,
        args.iryoken2_geojson,
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        for p in missing:
            print(f"エラー: {p} が見つかりません。")
        return 1

    audit_rows = read_csv_rows(args.audit)
    roster_rows = read_csv_rows(args.specialists_facility)
    iryoken2_rows = read_csv_rows(args.iryoken2)
    reconciliation_rows = read_csv_rows(args.reconciliation)
    population_rows = read_csv_rows(args.population_prefecture)
    pref_name_to_code = link.load_prefecture_geojson(args.prefecture_geojson)
    area_code_to_name, _area_code_to_pref_name = link.load_iryoken2_geojson(args.iryoken2_geojson)

    if args.crosswalk.exists():
        crosswalk_rows = read_csv_rows(args.crosswalk)
    else:
        crosswalk_rows = []
        print(f"(注) {args.crosswalk} が見つからないため、条件8は0行として扱います")
        print()

    print(f"■ 対象: {args.audit}")
    print()

    overall_ok = True

    print("== 条件1: 監査表の網羅性 ==")
    cond1_ok = check_condition1(audit_rows, roster_rows)
    print()
    overall_ok = overall_ok and cond1_ok

    print("== 条件2: 人数の保存 ==")
    cond2_ok = check_condition2(audit_rows, roster_rows)
    print()
    overall_ok = overall_ok and cond2_ok

    print("== 条件3: 医療圏集計の整合 ==")
    cond3_ok = check_condition3(audit_rows, iryoken2_rows)
    print()
    overall_ok = overall_ok and cond3_ok

    print("== 条件4: 医療圏の件数 ==")
    cond4_ok = check_condition4(iryoken2_rows, area_code_to_name)
    print()
    overall_ok = overall_ok and cond4_ok

    print("== 条件5: 県の整合 ==")
    cond5_ok = check_condition5(audit_rows, pref_name_to_code)
    print()
    overall_ok = overall_ok and cond5_ok

    print("== 条件6: 都道府県レベルとの関係 ==")
    cond6_ok = check_condition6(audit_rows, reconciliation_rows)
    print()
    overall_ok = overall_ok and cond6_ok

    print("== 条件7: 欠測の偏り ==")
    cond7_ok = check_condition7(audit_rows, population_rows)
    print()
    overall_ok = overall_ok and cond7_ok

    print("== 条件8: crosswalkの健全性 ==")
    cond8_ok = check_condition8(audit_rows, crosswalk_rows)
    print()
    overall_ok = overall_ok and cond8_ok

    print("=" * 60)
    if overall_ok:
        print("結果: 受け入れ条件1〜8をすべて満たしました。")
    else:
        print("結果: 受け入れ条件を満たさない項目があります。")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
