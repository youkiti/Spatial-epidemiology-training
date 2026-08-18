#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_meibo.py — 感染症専門医名簿PDF(data/raw/meibo_260701.pdf)から
都道府県別・施設別の専門医数を抽出する(issue #7・#8)。

## PDFの構造(2026-08-18 実測)

- 1ページ目: 「都道府県別認定者数(名簿非掲載者含む)」の表。10行×10列で
  (都道府県名, 認定者数) のペアが5組ずつ並ぶ。47都道府県+「海外」の
  48エントリ、合計1,903名。
- 1ページ目の残り〜40ページ目: 施設名の行 → 直下に氏名の行(同一施設の
  複数名は横並び、最大6名/行)という構造の繰り返し。住所は無い。

## 抽出方式(ハイブリッド)

都道府県名は左端(x0が30.0〜39.0pt、定数 `PREF_MARKER_X0_LO`〜`PREF_MARKER_X0_HI`)
に各都道府県の最初の施設が始まる行にのみ1回出現する。この列は
`pdfplumber.Page.find_tables()` では表の列として安定して検出できない
(ページによって列がまるごと消える・別の列と誤結合する)。一方で
`extract_words()` は都道府県名をヨコの位置(x0)だけで確実に拾える。
この窓からわずかに外れたマーカーが1件でもあると、そのブロックの氏名が
直前の都道府県に黙って合流してしまう。これは下記の検算
(都道府県マーカーの個数・集合チェック)で検出する。

施設行と氏名行の区別(「行の構造」)は逆に find_tables() の行分割のほうが
安定している。ただし **列インデックス(ncols)は信用できない** —
同じ「施設名1列+氏名6列」の構造でも、ページによって検出列数が7列だったり
8列だったりする(都道府県列の有無だけが原因ではなく、氏名が少ない行が
続くページでは意味のない空列が氏名列の途中に挿入されることがある。
2026-08-18 実測: 8ページ目)。列インデックスの固定オフセットでは
施設名と氏名を正しく切り分けられない。

そこで本スクリプトは **列インデックスを一切使わず、セルの座標(bbox の x0)**
で分類する。実測したx座標の帯(全ページ共通、ページ間でぶれない):

  - x0 <  60pt:  都道府県名の帯(表の列としては検出されないことがあるため
                 直接は使わない。都道府県の割り当ては extract_words() 由来の
                 マーカーで行う)
  - 60 <= x0 < 78pt: 施設名の帯(施設行ではここにテキスト、氏名行では空)
  - x0 >= 78pt:  氏名の帯(最大6列、38pt刻みではなく約78pt刻みで並ぶ)

都道府県の割り当ては、ページごとに「x0が30〜39ptの単語」を上から順に集めた
マーカー列と、表の行の bbox(top/bottom)を突き合わせ、マーカーの top が
その行の bbox の中に収まった時点で「現在の都道府県」を更新するかたちで行う
(forward-fill)。現在の都道府県・現在の施設名はページをまたいで保持する
(ページごとにリセットすると、ページの先頭から次の都道府県マーカーが
現れるまでの間の氏名がすべて誤った都道府県に割り当てられる。実装時に
実際に踏んだバグ)。

## 「海外」の扱い

「海外」は地図化の対象外(国内の都道府県ではないため)だが、CSVには
行として残す。**この行だけ `pref_code` を "99" にする**ことで、
後続処理が pref_code の数値範囲(01〜47が国内)だけを見て機械的に
地図対象を判定できるようにしている。

## 1ページ目の集計とのつき合わせ(reconciliation)

1ページ目の集計は「名簿非掲載者含む」ため、名簿本体(2ページ目以降)から
数えた人数はこれを上回らないはずである(本体は1ページ目の部分集合)。
しかし実際にPDFを処理すると、複数の都道府県で `diff`(1ページ目の集計 −
本体から数えた人数)が **負**になる(本体のほうが1ページ目の集計より多い)。
2026-08-18 時点の実測: 青森県・栃木県・千葉県・神奈川県・新潟県・石川県・
京都府・兵庫県・山口県の9都道府県で発生し、合計では本体1,894名に対し
1ページ目1,903名(全体としては本体が9名少ない=非負)。個別の該当都道府県を
名寄せ検証まで手作業で追った限り、抽出コード側の重複カウント・取りこぼしは
確認できなかった(例: 青森県は施設6件・氏名8名を1件ずつ目視で数え、
コードの抽出結果と一致した)。加えて、都道府県マーカーのforward-fillが
ページ境界でズレているなら神奈川県ブロックは五十音の途中から始まるはずだが、
実際には東京都ブロックが東京の施設「順天堂大学医学部附属練馬病院」で終わり、
神奈川県ブロックは五十音の先頭「あざがみクリニック」から始まっていた
(境界は正しい)。1ページ目の集計基準(会員登録上の都道府県)と名簿本体の
分類基準(所属施設の所在都道府県)が一致しない実務上の理由があるものと
推測されるが**未確認**。抽出バグではないと判断できる根拠が得られたため、
このスクリプトの検算は**全国合計が非負であることのみをハード検算(失敗で
終了コード1)とし、都道府県単位で `diff` が負になる件は警告として stdout に
列挙した上で `specialists_reconciliation.csv` の `note` 列に印を付ける**
(握り潰さない。下記「検算」参照)。

## 生成物

コミットする(data/processed/、氏名を含まない):
  - specialists_prefecture.csv: pref_code, pref_name, n_certified, source,
    retrieved_on, roster_date
  - specialists_facility.csv: pref_name, facility_name, n_specialists
  - specialists_reconciliation.csv: pref_code, pref_name, n_certified_page1,
    n_roster_body, diff, note(diffが負の行のみ "body_exceeds_page1"、
    それ以外は空文字)

コミットしない(data/interim/、.gitignore 済み、氏名を含む):
  - specialists_names.csv: pref_name, facility_name, person_name
    (監査用の中間ファイル。上記の不一致調査に使う)

使い方:
    python scripts/parse_meibo.py
    python scripts/parse_meibo.py --pdf data/raw/meibo_260701.pdf --out data/processed

終了コード: ハード検算すべて満たす=0、いずれか満たさない=1
(満たさない場合もCSVは書き出す。診断のため)。都道府県単位の `diff` が
負になる件は警告(stdout に列挙・CSVの `note` 列に印)であり、終了コードには
影響しない(全国合計の非負性のみハード検算にしている。理由は上記
「1ページ目の集計とのつき合わせ」参照)。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_PDF = Path("data/raw/meibo_260701.pdf")
DEFAULT_OUT = Path("data/processed")
DEFAULT_INTERIM = Path("data/interim")
DEFAULT_SOURCE_URL = "https://www.kansensho.or.jp/uploads/files/senmoni/meibo_260701.pdf"
ROSTER_DATE = "2026-07-01"  # 令和8年7月1日(名簿の版)

# 都道府県名 -> JIS X 0401 の2桁コード。PDF上の表示順序は地方ブロック単位の
# 独自順(JISの数値順ではない)なので、コードは名前引きの固定表として持つ。
# 「海外」は都道府県ではないため 99 を割り当てる(地図対象外の機械的な判定に使う)。
PREF_CODES: Dict[str, str] = {
    "北海道": "01", "青森県": "02", "岩手県": "03", "宮城県": "04", "秋田県": "05",
    "山形県": "06", "福島県": "07", "茨城県": "08", "栃木県": "09", "群馬県": "10",
    "埼玉県": "11", "千葉県": "12", "東京都": "13", "神奈川県": "14", "新潟県": "15",
    "富山県": "16", "石川県": "17", "福井県": "18", "山梨県": "19", "長野県": "20",
    "岐阜県": "21", "静岡県": "22", "愛知県": "23", "三重県": "24", "滋賀県": "25",
    "京都府": "26", "大阪府": "27", "兵庫県": "28", "奈良県": "29", "和歌山県": "30",
    "鳥取県": "31", "島根県": "32", "岡山県": "33", "広島県": "34", "山口県": "35",
    "徳島県": "36", "香川県": "37", "愛媛県": "38", "高知県": "39", "福岡県": "40",
    "佐賀県": "41", "長崎県": "42", "熊本県": "43", "大分県": "44", "宮崎県": "45",
    "鹿児島県": "46", "沖縄県": "47",
    "海外": "99",
}

# 都道府県マーカー・施設名の帯を分ける x0 の閾値(pt)。実測に基づく
# (このモジュールの docstring 冒頭を参照)。
FACILITY_X0_LO = 60.0
FACILITY_X0_HI = 78.0
NAME_X0_LO = 78.0
PREF_MARKER_X0_LO = 30.0
PREF_MARKER_X0_HI = 39.0


def write_csv(path: Path, header: List[str], rows: List[List[object]]) -> None:
    """行の並び順そのままで CSV を書き出す(呼び出し側でソート済みであること)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


# =====================================================================
# 1ページ目: 都道府県別認定者数(公式集計)
# =====================================================================


def parse_summary_page(pdf: "pdfplumber.PDF") -> Dict[str, int]:
    """1ページ目の「都道府県別認定者数」表を読み、name -> count の辞書を返す。"""
    page = pdf.pages[0]
    tables = page.find_tables()
    if not tables:
        raise RuntimeError("1ページ目にテーブルが見つかりません(PDFの構造が変わった可能性)。")
    data = tables[0].extract()

    counts: Dict[str, int] = {}
    for row_index, row in enumerate(data):
        for i in range(0, len(row) - 1, 2):
            name = row[i]
            count_text = row[i + 1]
            if not name:
                continue
            name = name.strip()
            if not name:
                continue
            if name not in PREF_CODES:
                raise RuntimeError(
                    f"1ページ目 行{row_index}: 未知の都道府県名です: {name!r}。"
                    "PREF_CODESに無い名前です(表記ゆれ、またはPDFの構造が変わった可能性)。"
                )
            count_text_stripped = (count_text or "").strip()
            try:
                counts[name] = int(count_text_stripped)
            except ValueError as e:
                raise RuntimeError(
                    f"1ページ目 行{row_index} 都道府県 '{name}': "
                    f"認定者数が数値になりません(実測: {count_text!r})。"
                ) from e
    return counts


# =====================================================================
# 2〜40ページ: 名簿本体(施設 -> 氏名)
# =====================================================================


def collect_pref_markers(page: "pdfplumber.page.Page") -> List[dict]:
    """ページ内の都道府県マーカー(x0が30〜39ptの単語)を top 昇順で返す。"""
    words = page.extract_words()
    markers = [
        w for w in words
        if PREF_MARKER_X0_LO <= w["x0"] <= PREF_MARKER_X0_HI
    ]
    markers.sort(key=lambda w: w["top"])
    return markers


def extract_roster_records(
    pdf: "pdfplumber.PDF",
) -> Tuple[List[Tuple[str, str, str]], List[str]]:
    """名簿本体から (都道府県名, 施設名, 氏名) のタプルの一覧と、
    検出した都道府県マーカーの全文字列(出現順)の一覧を返す。

    都道府県・施設名はページをまたいで保持する(現在の値が次のマーカー/
    施設行が現れるまで有効)。1ページ目は都道府県別集計の表(テーブル0)を
    含むため、テーブル1以降だけを本体とみなす。

    マーカーの全文字列一覧は、都道府県マーカーの取りこぼし検算
    (`run_checks`)のために返す。取りこぼしがあると診断できるのは
    「本来検出されるべきマーカーが検出されなかった」ケースのみであり、
    本関数はその実測値を提供するだけで、判定自体は行わない。
    """
    records: List[Tuple[str, str, str]] = []
    all_marker_texts: List[str] = []
    current_pref: Optional[str] = None
    current_facility: Optional[str] = None

    for page_index, page in enumerate(pdf.pages):
        tables = page.find_tables()
        if page_index == 0:
            tables = tables[1:]

        markers = collect_pref_markers(page)
        all_marker_texts.extend(m["text"].strip() for m in markers)
        marker_idx = 0

        for table in tables:
            data = table.extract()
            rows = table.rows
            for row_index, row_cells in enumerate(data):
                cell_bboxes = rows[row_index].cells
                row_bottom = rows[row_index].bbox[3]

                # このページ内で、行の下端より前に出現したマーカーをすべて消費する。
                while marker_idx < len(markers) and markers[marker_idx]["top"] < row_bottom:
                    current_pref = markers[marker_idx]["text"].strip()
                    marker_idx += 1

                facility_texts: List[str] = []
                name_texts: List[str] = []
                for text, bbox in zip(row_cells, cell_bboxes):
                    if bbox is None or text is None:
                        continue
                    text = text.strip()
                    if not text:
                        continue
                    x0 = bbox[0]
                    if FACILITY_X0_LO <= x0 < FACILITY_X0_HI:
                        facility_texts.append(text)
                    elif x0 >= NAME_X0_LO:
                        name_texts.append(text)
                    # x0 < FACILITY_X0_LO は都道府県マーカーの帯。
                    # 都道府県割り当ては extract_words() 由来のマーカーで
                    # 別途行っているため、ここでは無視する。

                if facility_texts:
                    current_facility = "".join(facility_texts)
                    if name_texts:
                        raise RuntimeError(
                            f"page {page_index + 1} row {row_index}: "
                            f"施設行に氏名らしきテキストが同居しています "
                            f"(facility={facility_texts!r}, names={name_texts!r})。"
                            "座標の閾値がこのページに合っていない可能性があります。"
                        )
                    continue

                if not name_texts:
                    continue  # 空行(区切り)

                if current_pref is None or current_facility is None:
                    raise RuntimeError(
                        f"page {page_index + 1} row {row_index}: "
                        f"都道府県または施設名が未確定のまま氏名行に到達しました "
                        f"(pref={current_pref!r}, facility={current_facility!r})。"
                    )
                for name in name_texts:
                    records.append((current_pref, current_facility, name))

        if marker_idx < len(markers):
            raise RuntimeError(
                f"page {page_index + 1}: 消費されなかった都道府県マーカーがあります: "
                f"{[m['text'] for m in markers[marker_idx:]]}"
            )

    return records, all_marker_texts


# =====================================================================
# 集計・出力
# =====================================================================


def build_prefecture_rows(
    summary: Dict[str, int], retrieved_on: str
) -> List[List[object]]:
    rows: List[List[object]] = []
    for name, code in sorted(PREF_CODES.items(), key=lambda kv: kv[1]):
        n_certified = summary.get(name)
        if n_certified is None:
            raise RuntimeError(f"1ページ目の集計に都道府県 '{name}' が見つかりません。")
        rows.append([code, name, n_certified, DEFAULT_SOURCE_URL, retrieved_on, ROSTER_DATE])
    return rows


def build_facility_rows(records: List[Tuple[str, str, str]]) -> List[List[object]]:
    counts: Dict[Tuple[str, str], int] = {}
    for pref, facility, _name in records:
        key = (pref, facility)
        counts[key] = counts.get(key, 0) + 1
    rows = [
        [pref, facility, n]
        for (pref, facility), n in counts.items()
    ]
    rows.sort(key=lambda r: (PREF_CODES.get(r[0], "99"), r[1]))
    return rows


def build_reconciliation_rows(
    summary: Dict[str, int], records: List[Tuple[str, str, str]]
) -> List[List[object]]:
    roster_counts: Dict[str, int] = {}
    for pref, _facility, _name in records:
        roster_counts[pref] = roster_counts.get(pref, 0) + 1

    rows: List[List[object]] = []
    for name, code in sorted(PREF_CODES.items(), key=lambda kv: kv[1]):
        n_certified_page1 = summary.get(name, 0)
        n_roster_body = roster_counts.get(name, 0)
        diff = n_certified_page1 - n_roster_body
        note = "body_exceeds_page1" if diff < 0 else ""
        rows.append([code, name, n_certified_page1, n_roster_body, diff, note])
    return rows


def write_interim_names(path: Path, records: List[Tuple[str, str, str]]) -> None:
    """氏名を含む監査用の中間ファイルを data/interim/ に書く(コミット対象外)。"""
    rows = sorted(records, key=lambda r: (PREF_CODES.get(r[0], "99"), r[1], r[2]))
    write_csv(path, ["pref_name", "facility_name", "person_name"], [list(r) for r in rows])


def read_retrieved_on(pdf_path: Path) -> Optional[str]:
    """fetch_meibo.py が書いたメタJSONから取得日(UTC日付)を読む。

    メタが無い・読めない・取得日時が空の場合は None を返す(呼び出し側で
    エラー扱いにする)。**実行日にフォールバックしない** — 分からない来歴を
    「今日取得した」という誤った事実として CSV に永続化してしまうため
    (`retrieved_on` 列は出典の正本として使う値)。
    """
    meta_path = pdf_path.with_name(pdf_path.name + ".meta.json")
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    retrieved_at = meta.get("retrieved_at_utc")
    if not retrieved_at:
        return None
    return retrieved_at[:10]  # "YYYY-MM-DDT..." -> "YYYY-MM-DD"


# =====================================================================
# 検算(アサート)
# =====================================================================


def run_checks(
    summary: Dict[str, int],
    facility_rows: List[List[object]],
    reconciliation_rows: List[List[object]],
    total_roster_names: int,
    all_markers: List[str],
) -> Tuple[List[str], List[str]]:
    """検算を行い、(ハード検算の失敗説明文リスト, 警告説明文リスト) を返す。

    ハード検算(failures)が1件でもあれば呼び出し側は終了コード1にする。
    警告(warnings)は異常として stdout に出すが、終了コードには影響しない
    (2026-08-18 追加検証で、都道府県単位の diff 負転は抽出バグではないと
    判断できたため。詳細はモジュールdocstring「1ページ目の集計との
    つき合わせ」を参照)。
    """
    failures: List[str] = []
    warnings: List[str] = []

    total = sum(summary.values())
    if total != 1903:
        failures.append(f"1ページ目の合計が1,903ではありません(実測: {total})。")

    if summary.get("東京都") != 380:
        failures.append(f"東京都が380ではありません(実測: {summary.get('東京都')})。")

    if summary.get("山梨県") != 2:
        failures.append(f"山梨県が2ではありません(実測: {summary.get('山梨県')})。")

    if summary.get("海外") != 14:
        failures.append(f"海外が14ではありません(実測: {summary.get('海外')})。")

    if len(summary) != 48:
        failures.append(f"都道府県エントリが48件ちょうどではありません(実測: {len(summary)}件)。")

    facility_total = sum(int(r[2]) for r in facility_rows)
    if facility_total != total_roster_names:
        failures.append(
            "specialists_facility.csv の n_specialists 合計が、名簿本体から抽出した"
            f"氏名の総数と一致しません(facility合計: {facility_total}, 氏名総数: {total_roster_names})。"
        )

    total_diff = sum(int(r[4]) for r in reconciliation_rows)
    if total_diff < 0:
        failures.append(
            "reconciliation の diff 全国合計が負です(1ページ目は名簿非掲載者を含むため"
            f"構造的に非負のはず。実測: {total_diff})。"
        )

    missing_markers = sorted(set(PREF_CODES.keys()) - set(all_markers))
    extra_markers = sorted(set(all_markers) - set(PREF_CODES.keys()))
    if missing_markers or extra_markers or len(all_markers) != 48:
        detail_parts = [f"検出件数: {len(all_markers)}件(期待: 48件)"]
        if missing_markers:
            detail_parts.append(f"欠落した都道府県: {missing_markers}")
        if extra_markers:
            detail_parts.append(f"未知のマーカー文字列: {extra_markers}")
        failures.append(
            "都道府県マーカーの検出に過不足があります"
            "(x0の窓からマーカーが外れて取りこぼされた可能性): " + " / ".join(detail_parts)
        )

    negative_diffs = [r for r in reconciliation_rows if int(r[4]) < 0]
    if negative_diffs:
        detail = ", ".join(f"{r[1]}(diff={r[4]}, page1={r[2]}, body={r[3]})" for r in negative_diffs)
        warnings.append(
            f"diff が負の都道府県が{len(negative_diffs)}件あります"
            f"(本体が1ページ目集計を上回っています。抽出バグではないと判断済み。"
            f"詳細は data/processed/README.md 参照): {detail}"
        )

    return failures, warnings


# =====================================================================
# CLI
# =====================================================================


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="感染症専門医名簿PDFから都道府県別・施設別の専門医数を抽出する")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="入力PDFのパス")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="コミット対象CSVの出力先ディレクトリ")
    parser.add_argument("--interim", type=Path, default=DEFAULT_INTERIM, help="氏名を含む中間ファイルの出力先ディレクトリ")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    if not args.pdf.exists():
        print(f"エラー: PDFが見つかりません: {args.pdf}", file=sys.stderr)
        print("先に python scripts/fetch_meibo.py を実行してください。", file=sys.stderr)
        return 1

    retrieved_on = read_retrieved_on(args.pdf)
    if retrieved_on is None:
        print(
            f"エラー: 取得メタ情報({args.pdf.name}.meta.json)が無いか読めないため、"
            "retrieved_on を決定できません。",
            file=sys.stderr,
        )
        print("先に python scripts/fetch_meibo.py を実行してください。", file=sys.stderr)
        return 1

    with pdfplumber.open(args.pdf) as pdf:
        summary = parse_summary_page(pdf)
        records, all_markers = extract_roster_records(pdf)

    prefecture_rows = build_prefecture_rows(summary, retrieved_on)
    facility_rows = build_facility_rows(records)
    reconciliation_rows = build_reconciliation_rows(summary, records)

    write_csv(
        args.out / "specialists_prefecture.csv",
        ["pref_code", "pref_name", "n_certified", "source", "retrieved_on", "roster_date"],
        prefecture_rows,
    )
    write_csv(
        args.out / "specialists_facility.csv",
        ["pref_name", "facility_name", "n_specialists"],
        facility_rows,
    )
    write_csv(
        args.out / "specialists_reconciliation.csv",
        ["pref_code", "pref_name", "n_certified_page1", "n_roster_body", "diff", "note"],
        reconciliation_rows,
    )
    write_interim_names(args.interim / "specialists_names.csv", records)

    print("生成完了:")
    print(f"  {args.out / 'specialists_prefecture.csv'}({len(prefecture_rows)}件)")
    print(f"  {args.out / 'specialists_facility.csv'}({len(facility_rows)}件、施設)")
    print(f"  {args.out / 'specialists_reconciliation.csv'}({len(reconciliation_rows)}件)")
    print(f"  {args.interim / 'specialists_names.csv'}({len(records)}件、氏名。data/interim/なのでコミット対象外)")
    print(f"  名簿本体から抽出した氏名の総数: {len(records)}")
    total_diff = sum(int(r[4]) for r in reconciliation_rows)
    print(f"  reconciliation の diff 全国合計: {total_diff}")

    failures, warnings = run_checks(summary, facility_rows, reconciliation_rows, len(records), all_markers)

    print()
    if warnings:
        for w in warnings:
            print(f"警告: {w}")
        print()

    if failures:
        print(f"検算NG: {len(failures)}件のハード検算に失敗しました。")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("検算OK: すべてのハード検算に合格しました。")
    if warnings:
        print(f"(ただし警告が{len(warnings)}件あります。上記参照)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
