#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
link_facilities.py — 感染症専門医名簿の施設名を参照点(`scripts/build_facility_reference.py`
が作った `data/interim/facility_reference.csv`)に突合し、二次医療圏に割り付ける
(issue #9 の名寄せ本体チャンク)。

## 何をするか

`data/processed/specialists_facility.csv`(名簿本体から集計した1,059行、
延べ1,894名)の各行を、参照点テーブルの施設名(正規化済み)に突合する。
突合できた行だけを二次医療圏で合計し、`data/processed/specialists_iryoken2.csv`
を作る。全1,059行(突合の成否を問わず)は `data/processed/facility_geo_audit.csv`
に監査表として書き出す(黙って落とさない)。

## care_setting(診療の場かどうか)と2系列の出力

突合できた行は「診療の場かどうか」を示す `care_setting`(`care`/`non_care`)を
必ず持つ(自動突合は構造的に常に `care`。crosswalk経由は `facility_crosswalk.csv`
の `care_setting` 列に従う)。感染症研究所・保健所・製薬企業等は専門医では
あるが、その医療圏の住民が受診できる先ではないため、`specialists_iryoken2.csv`
は2系列を出す: `n_specialists_care`(`care` のみ。**主系列**)と
`n_specialists_all`(`care` + `non_care`)。教材はこの2つの分布を並べて見せ、
症例定義(何を数えるか)を変えると地図が変わることを示す。

## 突合の順序(先に決まったら以降は試さない)

1. **crosswalk による上書き** — `data/curated/facility_crosswalk.csv`
   (無ければ空として続行)に `(pref_name, facility_name)` の完全一致があれば
   それに従う。`basis=unassignable` の行は割付せず `match_status=unassignable`
   として監査表に出す。`basis=non_care_workplace` で所在の参照点が
   決まっていない行も同様に `match_status=unassignable`
   (`reason_code=no_location_for_non_care`)にする。
2. tier1 / 医療情報ネット — 正規化名が県内で完全一致し、候補がちょうど1件
3. tier2 / 医療情報ネット — 接尾一致(`a.endswith(b) or b.endswith(a)`)が
   県内でちょうど1件。かつ短い方の正規化名が5文字以上、かつ短い方が
   `lib_facility_name.is_type_word_only()` で真でないこと
   (「中央病院」のような汎用語1つが偶然共通するだけの誤結合を防ぐガード。
   割付率を上げる目的でここを緩めてはいけない)
4. tier1 / P04 — 2と同じ条件をP04の参照点に対して
5. tier2 / P04 — 3と同じ条件をP04の参照点に対して
6. 決まらなければ `match_status=unmatched`

都道府県コードは、参照点側は `pref_code_declared`(無ければ `pref_code_pip`)、
名簿側は `pref_name` を `data/geo/prefecture.geojson` で引く。名簿には
`海外` という `pref_name` が1行(13名)あり、47都道府県に無いため
`match_status=unassignable`(`reason_code=pref_not_in_japan`)として扱う
(落とさず監査表に出す)。

## 一対一制約について(隣リポジトリ`visualize-regional-medical-care-for-2040`と
意図的に違う設計にする)

隣リポジトリは「同じ参照点を複数の施設が取り合ったら両方とも不採用」にしている。
**このリポジトリでは不採用にしない。** 理由:

- 向こうの入力は施設マスタなので、2つの別施設が同じ点を取り合うのは
  どちらかが誤りを意味する。
- こちらの入力は名簿の施設名を集約した行なので、2行が同じ参照点に当たるのは
  「同じ病院が2通りの表記で名簿に載っていた」ことを意味することが多く、
  統合するのが正しい。両方落とすと専門医数が消える。

したがって、複数の名簿行が同一参照点(tier1/tier2の自動突合による。crosswalk
経由の割付は特定の参照点を経由しないため対象外)に当たった場合は**採用した
うえで**、監査表の `contested` 列を1にし、標準出力にも該当する名簿行の組を
全件列挙する(commander が目視で本当に同一施設かを確認するため)。

## 出力

- `data/processed/facility_geo_audit.csv` — 名簿の全1,059行(列は
  `OUTPUT_HEADER` 参照。`reason_code` は未割付の理由、`contested` は
  「複数の名簿行が同じ参照点に当たった」ことを示す採用行への補助フラグで、
  採用/不採用の別(`match_status`/`reason_code`)とは別列にして混ざらないように
  している)
- `data/processed/specialists_iryoken2.csv` — 割り付いた行を二次医療圏で
  合計したもの。`n_specialists_care`(主系列)・`n_specialists_all` の2系列。
  専門医0人の医療圏も339件すべて出す(0行だと「データが無い」のか「0人」
  なのか区別できず、地図で欠測と0を取り違えるため)

必要環境: Python 3.9+(追加依存なし。標準ライブラリのみ)

使い方:
    PYTHONUTF8=1 python scripts/link_facilities.py

終了コード: 正常終了0、入力が見つからない・crosswalkの検証エラー等1
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# scripts/lib_facility_name.py は同じ scripts/ ディレクトリにある。実行時の
# カレントディレクトリに依存させないよう明示的にパスを追加してから import する。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_facility_name  # noqa: E402 (パス追加の後に import する必要がある)

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SPECIALISTS_CSV = REPO_ROOT / "data" / "processed" / "specialists_facility.csv"
DEFAULT_FACILITY_REFERENCE_CSV = REPO_ROOT / "data" / "interim" / "facility_reference.csv"
DEFAULT_PREFECTURE_GEOJSON = REPO_ROOT / "data" / "geo" / "prefecture.geojson"
DEFAULT_IRYOKEN2_GEOJSON = REPO_ROOT / "data" / "geo" / "iryoken2.geojson"
DEFAULT_CROSSWALK_CSV = REPO_ROOT / "data" / "curated" / "facility_crosswalk.csv"
DEFAULT_AUDIT_OUT_CSV = REPO_ROOT / "data" / "processed" / "facility_geo_audit.csv"
DEFAULT_IRYOKEN2_OUT_CSV = REPO_ROOT / "data" / "processed" / "specialists_iryoken2.csv"

IRYOJOHO_SOURCES = ("iryojoho_hospital", "iryojoho_clinic")
P04_SOURCE = "ksj_p04"

TIER2_MIN_SHORTER_LEN = 5

ALLOWED_BASIS = {
    "university_hospital",
    "research_institute",
    "renamed",
    "non_care_workplace",
    "unassignable",
}
# unassignable だけが「座標を持たせようがない(match_statusを専用の値にする)」
# basis。non_care_workplace は診療の場ではないが所在は持ちうるため、
# excluded_non_care のときと違って一律 match_status を差し替えない
# (load_crosswalk / match_roster 側で care_setting・resolved_facility_name の
# 有無を見て matched か unassignable かを個別に決める)。
BASIS_TO_MATCH_STATUS = {
    "unassignable": "unassignable",
}

ALLOWED_CARE_SETTING = {"care", "non_care"}

AUDIT_HEADER = [
    "pref_name",
    "facility_name",
    "n_specialists",
    "match_status",
    "match_method",
    "coordinate_source",
    "assignment_basis",
    "care_setting",
    "ref_facility_name",
    "iryoken2_code",
    "iryoken2_name",
    "lon",
    "lat",
    "reason_code",
    "contested",
]

IRYOKEN2_OUT_HEADER = [
    "iryoken2_code",
    "iryoken2_name",
    "pref_name",
    "n_specialists_care",
    "n_specialists_all",
]


# ===========================================================================
# 1. 入力の読み込み
# ===========================================================================


def load_specialists_facility(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {
                "pref_name": row["pref_name"],
                "facility_name": row["facility_name"],
                "n_specialists": int(row["n_specialists"]),
            }
            for row in reader
        ]


def load_facility_reference(path: Path) -> List[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_prefecture_geojson(path: Path) -> Dict[str, str]:
    """`pref_name -> pref_code` の対応を返す。"""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return {feat["properties"]["pref_name"]: feat["properties"]["pref_code"] for feat in data["features"]}


def load_iryoken2_geojson(path: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """`area_code -> area_name` と `area_code -> pref_name` の対応を返す。"""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    area_code_to_name = {}
    area_code_to_pref_name = {}
    for feat in data["features"]:
        props = feat["properties"]
        area_code_to_name[props["area_code"]] = props["area_name"]
        area_code_to_pref_name[props["area_code"]] = props["pref_name"]
    return area_code_to_name, area_code_to_pref_name


def build_refs_by_pref_normalized(refs: List[dict]) -> Dict[str, Dict[str, List[dict]]]:
    """`pref_code -> facility_name_normalized -> 参照点のリスト` の索引を作る。
    医療情報ネット/P04のソースを区別せず、県内の全参照点をまとめて引けるようにする
    (`load_crosswalk` の `resolved_facility_name` 解決に使う。`build_ref_index` の
    `(group, pref_code)` 索引とは目的が異なるため別に持つ)。
    """
    index: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    for ref in refs:
        pref_code = ref_pref_code(ref)
        if not pref_code:
            continue
        index[pref_code][ref["facility_name_normalized"]].append(ref)
    return index


def _resolve_iryoken2_code_from_name(
    resolved_facility_name: str, pref_code: str, refs_by_pref_normalized: Dict[str, Dict[str, List[dict]]]
) -> Tuple[str, str]:
    """`resolved_facility_name` を正規化して県内の参照点テーブルから完全一致で
    引き当て、`(iryoken2_code, coordinate_source)` を返す。見つからない・
    一意に決まらない・医療圏が空、のいずれかならSystemExitで落とす。

    「一意に決まらない」の判定は参照点の行数ではなく**医療圏コードの種類数**で行う。
    同じ施設が医療情報ネットとP04の両方に(ほぼ同じ座標・同じ正規化名で)重複して
    載っているのは日常的にあり、その場合は行数としては複数でも医療圏コードは
    一致するので誤りではない。逆に、県内に同名の別施設が実在し医療圏コードが
    食い違う場合(実例: 神奈川県の「佐藤病院」が2施設ある)は、行数によらず
    エラーにする必要がある。
    """
    normalized = lib_facility_name.normalize_facility_name(resolved_facility_name)
    candidates = refs_by_pref_normalized.get(pref_code, {}).get(normalized, [])
    if not candidates:
        raise SystemExit(
            f"resolved_facility_name {resolved_facility_name!r} が県内の参照点テーブル"
            f"(data/interim/facility_reference.csv)に見つかりません"
        )
    candidates_with_code = [c for c in candidates if c["iryoken2_code"]]
    if not candidates_with_code:
        raise SystemExit(
            f"resolved_facility_name {resolved_facility_name!r} は参照点テーブルに見つかりましたが、"
            f"二次医療圏ポリゴンに属さない点(iryoken2_codeが空)しか無いため医療圏を決定できません"
        )
    distinct_codes = {c["iryoken2_code"] for c in candidates_with_code}
    if len(distinct_codes) > 1:
        raise SystemExit(
            f"resolved_facility_name {resolved_facility_name!r} は県内に複数の医療圏コードに"
            f"またがる同名の参照点があり、一意に決まりません(候補: {sorted(distinct_codes)})"
        )
    derived_code = next(iter(distinct_codes))
    representative = next(c for c in candidates_with_code if c["iryoken2_code"] == derived_code)
    return derived_code, representative["source"]


def load_crosswalk(
    path: Path,
    roster_keys: set,
    valid_area_codes: set,
    pref_name_to_code: Dict[str, str],
    refs_by_pref_normalized: Dict[str, Dict[str, List[dict]]],
) -> Dict[Tuple[str, str], dict]:
    """`data/curated/facility_crosswalk.csv` を読み込み、
    `(pref_name, facility_name) -> {basis, care_setting, iryoken2_code,
    coordinate_source, resolved_facility_name, note}` の辞書を返す。ファイルが
    無ければ空辞書のまま続行する(commander が後で作る)。

    ## なぜ `resolved_facility_name` から `iryoken2_code` を導出するのか

    このcrosswalkは commander が60行以上を手で埋め、さらに**ユーザーが目視で
    監査する**表になる。`iryoken2_code` を手打ちの正本として素通しすると、
    「`長崎大学病院` と書いてあるのにコードは隣の医療圏」という転記ミスが
    エラーにならずそのまま地図に乗る。目視監査は施設**名**を見て正しさを
    判断するので、名前とコードがずれていても気づけない。そこで
    `resolved_facility_name` が埋まっている行は、そちらを正本として県内の
    参照点テーブル(`data/interim/facility_reference.csv`)から
    `iryoken2_code` を導出し、`iryoken2_code` 列が併記されていれば
    導出値と一致するかを検査する(二重チェック。食い違えばエラー)。
    `resolved_facility_name` が空の行(参照点テーブルに存在しない施設を
    人手で医療圏だけ決めたい場合の逃げ道)だけ、従来どおり `iryoken2_code`
    の手入力を正本として扱う。

    検証(いずれも違反時はSystemExitで落とす。黙って無視しない):
      - `basis` は `ALLOWED_BASIS` のいずれか
      - `(pref_name, facility_name)` は名簿(`roster_keys`)に実在すること
        (名簿改訂で行が消えたのにcrosswalkが残っている状態を検出するため)
      - `care_setting` は、`basis=unassignable` のときは**必ず空**
        (座標を持たせようがない行に診療の場かどうかは判定できないため)、
        それ以外のときは `care`/`non_care` のいずれか(空や他の値はエラー)
      - `basis` が `unassignable` のときは `iryoken2_code` は**必ず空**であること
        (埋まっていたら書き間違いの可能性が高いためエラー)
      - `basis` がそれ以外のとき:
        - `resolved_facility_name` が埋まっていれば、県内の参照点テーブルから
          正規化名の完全一致で引き当てて `iryoken2_code` を導出する
          (見つからない・一意に決まらない・医療圏が空、のいずれもエラー)。
          `iryoken2_code` 列も埋まっていれば導出値と一致するか検査する
        - `resolved_facility_name` が空で `iryoken2_code` も空のとき:
          `basis=non_care_workplace` に限り許容する(診療を行わない勤務先は
          所在の参照点が見つからないことがあるため。この場合は
          `match_roster` 側で `match_status=unassignable`
          (`reason_code=no_location_for_non_care`)として扱う)。
          それ以外の `basis`(`university_hospital`/`research_institute`/
          `renamed`)では所在が必ず特定できるはずなので、両方空はエラー
        - `resolved_facility_name` が空で `iryoken2_code` だけ埋まっていれば、
          従来どおりそれを正本として扱う。`data/geo/iryoken2.geojson` に
          実在するコードであること
      - `(pref_name, facility_name)` の重複行はエラー
    """
    if not path.exists():
        return {}

    result: Dict[Tuple[str, str], dict] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required_cols = {
            "pref_name",
            "facility_name",
            "basis",
            "care_setting",
            "iryoken2_code",
            "resolved_facility_name",
            "note",
        }
        if reader.fieldnames is None or not required_cols.issubset(set(reader.fieldnames)):
            raise SystemExit(f"エラー: {path} に必要な列が揃っていません(期待: {sorted(required_cols)})")

        for line_no, row in enumerate(reader, start=2):  # 1行目はヘッダ
            pref_name = (row.get("pref_name") or "").strip()
            facility_name = (row.get("facility_name") or "").strip()
            basis = (row.get("basis") or "").strip()
            care_setting = (row.get("care_setting") or "").strip()
            code = (row.get("iryoken2_code") or "").strip()
            resolved_facility_name = (row.get("resolved_facility_name") or "").strip()
            key = (pref_name, facility_name)

            if basis not in ALLOWED_BASIS:
                raise SystemExit(f"エラー: {path}:{line_no}行目: 不正な basis {basis!r}(許可値: {sorted(ALLOWED_BASIS)})")
            if key not in roster_keys:
                raise SystemExit(
                    f"エラー: {path}:{line_no}行目: 名簿(data/processed/specialists_facility.csv)に"
                    f"存在しない (pref_name, facility_name) です: {key}"
                )
            if key in result:
                raise SystemExit(f"エラー: {path}:{line_no}行目: (pref_name, facility_name) が重複しています: {key}")

            if basis == "unassignable":
                if care_setting:
                    raise SystemExit(
                        f"エラー: {path}:{line_no}行目: basis=unassignable では care_setting は空である"
                        f"必要があります(値: {care_setting!r}。座標を持たせようがない行に診療の場かどうかは"
                        f"判定できないため)"
                    )
            elif care_setting not in ALLOWED_CARE_SETTING:
                raise SystemExit(
                    f"エラー: {path}:{line_no}行目: basis={basis!r} では care_setting は"
                    f" {sorted(ALLOWED_CARE_SETTING)} のいずれかである必要があります(値: {care_setting!r})"
                )

            coordinate_source = "crosswalk"

            if basis in BASIS_TO_MATCH_STATUS:
                # unassignable は iryoken2_code を空にする(埋まっていたら書き間違い)
                if code:
                    raise SystemExit(
                        f"エラー: {path}:{line_no}行目: basis={basis!r} では iryoken2_code は空である"
                        f"必要があります(値: {code!r}。unassignableにコードが入っているのは書き間違いの疑いが強いため)"
                    )
            elif resolved_facility_name:
                pref_code = pref_name_to_code.get(pref_name)
                if pref_code is None:
                    raise SystemExit(
                        f"エラー: {path}:{line_no}行目: pref_name {pref_name!r} の都道府県コードが判定できません"
                        f"(resolved_facility_name からの導出には都道府県が必要です)"
                    )
                try:
                    derived_code, coordinate_source = _resolve_iryoken2_code_from_name(
                        resolved_facility_name, pref_code, refs_by_pref_normalized
                    )
                except SystemExit as e:
                    raise SystemExit(f"エラー: {path}:{line_no}行目: {e}")
                if code and code != derived_code:
                    raise SystemExit(
                        f"エラー: {path}:{line_no}行目: 手入力の iryoken2_code {code!r} が、"
                        f"resolved_facility_name {resolved_facility_name!r} からの導出値 {derived_code!r} と"
                        f"食い違います"
                    )
                code = derived_code
            elif code:
                if code not in valid_area_codes:
                    raise SystemExit(
                        f"エラー: {path}:{line_no}行目: iryoken2_code {code!r} は"
                        f" data/geo/iryoken2.geojson に存在しません"
                    )
            elif basis != "non_care_workplace":
                # resolved_facility_name も iryoken2_code も空。
                # non_care_workplace(診療を行わない勤務先)だけは所在の参照点が
                # 見つからないことを許容する(match_roster側でunassignable扱いに
                # する)。university_hospital/research_institute/renamed は
                # 施設として必ず所在が特定できるはずなので、両方空はエラーにする。
                raise SystemExit(
                    f"エラー: {path}:{line_no}行目: basis={basis!r} では resolved_facility_name と"
                    f" iryoken2_code の少なくとも一方が必要です(両方とも空になっています)"
                )

            result[key] = {
                "basis": basis,
                "care_setting": care_setting,
                "iryoken2_code": code,
                "coordinate_source": coordinate_source,
                "resolved_facility_name": resolved_facility_name,
                "note": row.get("note") or "",
            }
    return result


# ===========================================================================
# 2. 参照点の索引化・突合ロジック
# ===========================================================================


def ref_pref_code(ref: dict) -> str:
    return ref["pref_code_declared"] or ref["pref_code_pip"]


def build_ref_index(refs: List[dict]) -> Dict[Tuple[str, str], List[dict]]:
    """`(group, pref_code) -> 参照点のリスト` の索引を作る。`group` は
    `"iryojoho"`(医療情報ネット。病院票・診療所票をまとめて扱う)か `"p04"`。
    都道府県が判定できない参照点(`pref_code_declared`・`pref_code_pip` とも空)は
    県内突合の候補になり得ないため索引に含めない。
    """
    index: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for ref in refs:
        pref_code = ref_pref_code(ref)
        if not pref_code:
            continue
        group = "p04" if ref["source"] == P04_SOURCE else "iryojoho"
        index[(group, pref_code)].append(ref)
    return index


def tier1_candidates(pool: List[dict], normalized: str) -> List[dict]:
    """正規化名の完全一致による候補。"""
    return [ref for ref in pool if ref["facility_name_normalized"] == normalized]


def tier2_candidates(pool: List[dict], normalized: str) -> List[dict]:
    """接尾一致(`a.endswith(b) or b.endswith(a)`)による候補。

    短い方の正規化名が5文字未満、または短い方が施設種別語だけ
    (`lib_facility_name.is_type_word_only`)の場合はガードで除外する
    (「中央病院」のような汎用語1つが偶然共通するだけの誤結合を防ぐため。
    このガードは絶対に緩めない)。
    """
    out = []
    for ref in pool:
        other = ref["facility_name_normalized"]
        if not other:
            continue
        if normalized.endswith(other) or other.endswith(normalized):
            shorter = normalized if len(normalized) <= len(other) else other
            if len(shorter) >= TIER2_MIN_SHORTER_LEN and not lib_facility_name.is_type_word_only(shorter):
                out.append(ref)
    return out


TIER_STEPS = [
    ("normalized_exact", "iryojoho", tier1_candidates),
    ("normalized_suffix", "iryojoho", tier2_candidates),
    ("normalized_exact", "p04", tier1_candidates),
    ("normalized_suffix", "p04", tier2_candidates),
]


def make_audit_row(
    pref_name: str,
    facility_name: str,
    n_specialists: int,
    match_status: str,
    match_method: str = "",
    coordinate_source: str = "",
    assignment_basis: str = "",
    care_setting: str = "",
    ref_facility_name: str = "",
    iryoken2_code: str = "",
    iryoken2_name: str = "",
    lon: str = "",
    lat: str = "",
    reason_code: str = "",
) -> dict:
    return {
        "pref_name": pref_name,
        "facility_name": facility_name,
        "n_specialists": n_specialists,
        "match_status": match_status,
        "match_method": match_method,
        "coordinate_source": coordinate_source,
        "assignment_basis": assignment_basis,
        "care_setting": care_setting,
        "ref_facility_name": ref_facility_name,
        "iryoken2_code": iryoken2_code,
        "iryoken2_name": iryoken2_name,
        "lon": lon,
        "lat": lat,
        "reason_code": reason_code,
        "contested": 0,
        "_ref_key": None,  # 内部用。CSV出力前に落とす
    }


def match_roster(
    roster: List[dict],
    ref_index: Dict[Tuple[str, str], List[dict]],
    pref_name_to_code: Dict[str, str],
    crosswalk_map: Dict[Tuple[str, str], dict],
    area_code_to_name: Dict[str, str],
) -> List[dict]:
    """名簿の全行を突合し、監査行のリストを返す(`_ref_key` に自動突合で
    使った参照点のキーを内部保持。contested判定に使ったあと出力前に落とす)。
    """
    results: List[dict] = []

    for row in roster:
        pref_name = row["pref_name"]
        facility_name = row["facility_name"]
        n = row["n_specialists"]
        key = (pref_name, facility_name)

        # --- 1. crosswalk による上書き ---
        if key in crosswalk_map:
            cw = crosswalk_map[key]
            basis = cw["basis"]
            if basis in BASIS_TO_MATCH_STATUS:
                # unassignable: 座標を持たせようがない行
                results.append(
                    make_audit_row(
                        pref_name,
                        facility_name,
                        n,
                        match_status=BASIS_TO_MATCH_STATUS[basis],
                        match_method="crosswalk",
                        coordinate_source="crosswalk",
                        assignment_basis=basis,
                        care_setting=cw["care_setting"],
                        ref_facility_name=cw["resolved_facility_name"],
                    )
                )
            elif not cw["iryoken2_code"]:
                # non_care_workplace で所在の参照点が決まらなかった行。
                # 「除外」ではなく「診療を行わない勤務先だが所在不明」として
                # unassignable にする(load_crosswalkのバリデーションで
                # non_care_workplace以外はここに来ない)。
                results.append(
                    make_audit_row(
                        pref_name,
                        facility_name,
                        n,
                        match_status="unassignable",
                        match_method="crosswalk",
                        coordinate_source="crosswalk",
                        assignment_basis=basis,
                        care_setting=cw["care_setting"],
                        ref_facility_name=cw["resolved_facility_name"],
                        reason_code="no_location_for_non_care",
                    )
                )
            else:
                code = cw["iryoken2_code"]
                results.append(
                    make_audit_row(
                        pref_name,
                        facility_name,
                        n,
                        match_status="matched",
                        match_method="crosswalk",
                        coordinate_source=cw["coordinate_source"],
                        assignment_basis=basis,
                        care_setting=cw["care_setting"],
                        ref_facility_name=cw["resolved_facility_name"],
                        iryoken2_code=code,
                        iryoken2_name=area_code_to_name.get(code, ""),
                    )
                )
            continue

        # --- pref_name が日本の47都道府県に無い(例: "海外") ---
        pref_code = pref_name_to_code.get(pref_name)
        if pref_code is None:
            results.append(
                make_audit_row(
                    pref_name,
                    facility_name,
                    n,
                    match_status="unassignable",
                    assignment_basis="automatic",
                    reason_code="pref_not_in_japan",
                )
            )
            continue

        # --- 2〜5. tier1/tier2 × 医療情報ネット/P04 ---
        normalized = lib_facility_name.normalize_facility_name(facility_name)
        decided_method: Optional[str] = None
        decided_ref: Optional[dict] = None
        saw_multiple = False

        for method, group, candidate_fn in TIER_STEPS:
            pool = ref_index.get((group, pref_code), [])
            candidates = candidate_fn(pool, normalized)
            if len(candidates) == 1:
                decided_method, decided_ref = method, candidates[0]
                break
            if len(candidates) >= 2:
                saw_multiple = True

        if decided_ref is not None:
            code = decided_ref["iryoken2_code"]
            audit_row = make_audit_row(
                pref_name,
                facility_name,
                n,
                match_status="matched",
                match_method=decided_method,
                coordinate_source=decided_ref["source"],
                assignment_basis="automatic",
                # 自動突合は医療情報ネット・P04の病院票/診療所票の参照点にしか
                # 当たらない(build_ref_index / TIER_STEPS 参照)ので、突合できた
                # 時点で構造的に診療の場である。よって一律 "care" を入れる。
                care_setting="care",
                ref_facility_name=decided_ref["facility_name"],
                iryoken2_code=code,
                iryoken2_name=area_code_to_name.get(code, "") if code else "",
                lon=decided_ref["lon"],
                lat=decided_ref["lat"],
            )
            audit_row["_ref_key"] = (decided_ref["source"], decided_ref["ref_id"])
            results.append(audit_row)
        else:
            reason = "multiple_candidates_in_pref" if saw_multiple else "no_name_match"
            results.append(
                make_audit_row(
                    pref_name,
                    facility_name,
                    n,
                    match_status="unmatched",
                    assignment_basis="automatic",
                    reason_code=reason,
                )
            )

    # --- 一対一制約を外した設計に伴う後処理: 同一参照点への競合検出 ---
    # (crosswalk経由の割付には _ref_key が無いため対象外。理由はモジュールdocstring参照)
    ref_key_to_indices: Dict[Tuple[str, str], List[int]] = defaultdict(list)
    for i, r in enumerate(results):
        if r["_ref_key"] is not None:
            ref_key_to_indices[r["_ref_key"]].append(i)
    for ref_key, indices in ref_key_to_indices.items():
        if len(indices) > 1:
            for i in indices:
                results[i]["contested"] = 1

    return results


# ===========================================================================
# 3. 出力
# ===========================================================================


def write_audit_csv(path: Path, results: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(AUDIT_HEADER)
        for r in results:
            writer.writerow([r[col] for col in AUDIT_HEADER])


def write_iryoken2_csv(
    path: Path,
    results: List[dict],
    area_code_to_name: Dict[str, str],
    area_code_to_pref_name: Dict[str, str],
) -> None:
    """割り付いた行(`match_status=="matched"` かつ `iryoken2_code` が非空)を
    二次医療圏で合計する。2系列を出す:

    - `n_specialists_care`(**主系列**): `care_setting=="care"` の行だけを合計。
      教材が扱うのは専門医「による診療」へのアクセスなので、診療の場に
      いる専門医だけを数える。
    - `n_specialists_all`: 上記に `care_setting=="non_care"` の行(勤務地は
      判明しているが診療を行わない: 研究機関・保健所・製薬企業等)を加えた
      合計。名簿の勤務地をすべて数えた場合の分布。

    matched行の`care_setting`は自動突合なら常に"care"、crosswalk経由なら
    常に"care"/"non_care"のいずれかになる(load_crosswalkの検証で保証)ので、
    空になることは無い想定だが、念のため未知の値は両系列から除外する。

    専門医0人の医療圏も339件すべて出す。
    """
    care_sums: Counter = Counter()
    all_sums: Counter = Counter()
    for r in results:
        if r["match_status"] != "matched" or not r["iryoken2_code"]:
            continue
        if r["care_setting"] == "care":
            care_sums[r["iryoken2_code"]] += r["n_specialists"]
            all_sums[r["iryoken2_code"]] += r["n_specialists"]
        elif r["care_setting"] == "non_care":
            all_sums[r["iryoken2_code"]] += r["n_specialists"]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(IRYOKEN2_OUT_HEADER)
        for area_code in sorted(area_code_to_name):
            writer.writerow(
                [
                    area_code,
                    area_code_to_name[area_code],
                    area_code_to_pref_name[area_code],
                    care_sums.get(area_code, 0),
                    all_sums.get(area_code, 0),
                ]
            )


# ===========================================================================
# 4. 標準出力レポート
# ===========================================================================


def stage_of(r: dict) -> str:
    if r["match_status"] == "matched":
        if r["match_method"] == "crosswalk":
            return "crosswalk"
        if r["match_method"] == "normalized_exact" and r["coordinate_source"] in IRYOJOHO_SOURCES:
            return "tier1_iryojoho"
        if r["match_method"] == "normalized_suffix" and r["coordinate_source"] in IRYOJOHO_SOURCES:
            return "tier2_iryojoho"
        if r["match_method"] == "normalized_exact" and r["coordinate_source"] == P04_SOURCE:
            return "tier1_p04"
        if r["match_method"] == "normalized_suffix" and r["coordinate_source"] == P04_SOURCE:
            return "tier2_p04"
    if r["match_status"] == "unassignable":
        return "unassignable"
    if r["match_status"] == "unmatched":
        return "unmatched"
    return "unknown"  # pragma: no cover (partition漏れがあれば気づけるようにしておく)


STAGE_LABELS = {
    "crosswalk": "crosswalk",
    "tier1_iryojoho": "tier1 医療情報ネット",
    "tier2_iryojoho": "tier2 医療情報ネット",
    "tier1_p04": "tier1 P04",
    "tier2_p04": "tier2 P04",
    "unassignable": "割付不可(unassignable)",
    "unmatched": "未割付",
    "unknown": "不明(要調査)",
}
STAGE_ORDER = [
    "crosswalk",
    "tier1_iryojoho",
    "tier2_iryojoho",
    "tier1_p04",
    "tier2_p04",
    "unassignable",
    "unmatched",
    "unknown",
]


def print_report(results: List[dict]) -> None:
    total_rows = len(results)
    total_n = sum(r["n_specialists"] for r in results)

    print(f"■ 対象: 名簿 {total_rows}行 / 延べ{total_n}名")
    print()

    print("== 段階別の内訳(行数・専門医数) ==")
    stage_rows: Counter = Counter()
    stage_n: Counter = Counter()
    for r in results:
        s = stage_of(r)
        stage_rows[s] += 1
        stage_n[s] += r["n_specialists"]
    matched_n = sum(stage_n[s] for s in ("crosswalk", "tier1_iryojoho", "tier2_iryojoho", "tier1_p04", "tier2_p04"))
    for s in STAGE_ORDER:
        if stage_rows[s] == 0 and s not in (
            "crosswalk",
            "tier1_iryojoho",
            "tier2_iryojoho",
            "tier1_p04",
            "tier2_p04",
            "unassignable",
            "unmatched",
        ):
            continue
        print(f"  {STAGE_LABELS[s]}: {stage_rows[s]}行 / {stage_n[s]}名")
    print(f"  自動割付+crosswalk割付 計: {matched_n}名")
    print()

    print("== 人数の内訳(care / non_care の別) ==")
    # matched(施設を特定できた)と、そのうち実際に二次医療圏の地図に載る人数
    # (iryoken2_codeが非空)は別の数。両方とも意味のある数なので、どちらかに
    # 丸めず両方を明示的に出す(matchedでもiryoken2_codeが空の行は、参照点の
    # 座標がどの医療圏ポリゴンにも入らない施設で、地図には反映されない)。
    #
    # さらに、diagnosisの場かどうか(care_setting)で2系列に分ける。
    # care のみ = 「診療の場にいる専門医だけを数える」分布(主系列。
    # specialists_iryoken2.csv の n_specialists_care)。care+non_care =
    # 「名簿の勤務地をすべて数える」分布(specialists_iryoken2.csv の
    # n_specialists_all)。感染症研究所・保健所・製薬企業等は専門医では
    # あるが、その医療圏の住民が受診できる先ではないため care には含めない。
    matched_care_rows = [r for r in results if r["match_status"] == "matched" and r["care_setting"] == "care"]
    matched_noncare_rows = [r for r in results if r["match_status"] == "matched" and r["care_setting"] == "non_care"]
    matched_care_n = sum(r["n_specialists"] for r in matched_care_rows)
    matched_noncare_n = sum(r["n_specialists"] for r in matched_noncare_rows)

    mapped_care_rows = [r for r in matched_care_rows if r["iryoken2_code"]]
    mapped_noncare_rows = [r for r in matched_noncare_rows if r["iryoken2_code"]]
    mapped_care_n = sum(r["n_specialists"] for r in mapped_care_rows)
    mapped_noncare_n = sum(r["n_specialists"] for r in mapped_noncare_rows)
    mapped_all_n = mapped_care_n + mapped_noncare_n

    unmapped_matched_rows = [r for r in results if r["match_status"] == "matched" and not r["iryoken2_code"]]
    unmapped_matched_n = sum(r["n_specialists"] for r in unmapped_matched_rows)

    print(f"  施設を特定できた(matched): {matched_n}名")
    print(f"    うち診療の場(care):          {matched_care_n}名")
    print(f"    うち非診療の勤務先(non_care): {matched_noncare_n}名")
    print(f"  うち二次医療圏に載る:")
    print(f"    診療の場のみ(care、主系列): {mapped_care_n}名 ← specialists_iryoken2.csv の n_specialists_care 合計")
    print(f"    勤務地ベース(care+non_care): {mapped_all_n}名 ← specialists_iryoken2.csv の n_specialists_all 合計")
    if unmapped_matched_rows:
        detail = "、".join(f"{r['pref_name']} {r['facility_name']}" for r in unmapped_matched_rows)
        print(
            f"  差:                        {unmapped_matched_n}名({detail}。参照点の座標が"
            f"どの二次医療圏ポリゴンにも入らない。iryoken2.geojson は1km²未満の離島リングを除去済み)"
        )
    print()

    print("== 割付率(専門医数ベース。2系列) ==")
    care_rate = mapped_care_n / total_n if total_n else 0.0
    all_rate = mapped_all_n / total_n if total_n else 0.0
    matched_rate = matched_n / total_n if total_n else 0.0
    print(f"  地図に載る割合(診療の場のみ・主系列): {mapped_care_n}/{total_n} = {care_rate:.1%}")
    print(f"  地図に載る割合(勤務地ベース)          : {mapped_all_n}/{total_n} = {all_rate:.1%}")
    print(f"  (施設を特定できた割合: {matched_n}/{total_n} = {matched_rate:.1%})")
    print()

    print("== contested_shared_reference(複数の名簿行が同一参照点に当たった採用行) ==")
    groups: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for r in results:
        if r["contested"]:
            groups[(r["coordinate_source"], r["ref_facility_name"], r["lon"], r["lat"])].append(r)
    if not groups:
        print("  該当なし")
    else:
        for (source, ref_name, lon, lat), rows in groups.items():
            print(f"  参照点 [{source}] {ref_name} (lon={lon}, lat={lat}) に {len(rows)}行が競合:")
            for r in rows:
                print(f"    - {r['pref_name']} / {r['facility_name']} / {r['n_specialists']}名 ({r['match_method']})")
    print()

    print("== 都道府県別の割付率(専門医数ベース・care基準=主系列。低い順) ==")
    pref_total: Counter = Counter()
    pref_matched: Counter = Counter()
    for r in results:
        pref_total[r["pref_name"]] += r["n_specialists"]
        # 分子は「診療の場として地図に載る人数」= matched かつ iryoken2_code が
        # 非空 かつ care_setting=="care"(matched でも iryoken2_code が空の行は
        # 地図に載らない。実例: 長崎県サン・レモ リハビリ病院。non_careの行は
        # 主系列の地図には載らない。verify_facility_linkage.py の条件7と同じ
        # 定義に揃えている)。
        if r["match_status"] == "matched" and r["iryoken2_code"] and r["care_setting"] == "care":
            pref_matched[r["pref_name"]] += r["n_specialists"]
    pref_rates = []
    for pref_name, total in pref_total.items():
        matched = pref_matched.get(pref_name, 0)
        rate = matched / total if total else 0.0
        pref_rates.append((rate, pref_name, matched, total))
    pref_rates.sort()
    for rate, pref_name, matched, total in pref_rates:
        print(f"  {pref_name}: {matched}/{total} = {rate:.1%}")
    print()

    print("== 未割付になった行のうち専門医数が多い順(上位30行) ==")
    unmatched = [r for r in results if r["match_status"] == "unmatched"]
    unmatched.sort(key=lambda r: -r["n_specialists"])
    for r in unmatched[:30]:
        print(f"  {r['n_specialists']}名 / {r['pref_name']} / {r['facility_name']} / reason={r['reason_code']}")
    print()


# ===========================================================================
# 5. main
# ===========================================================================


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="専門医名簿の施設名を参照点に突合し、二次医療圏に割り付ける")
    parser.add_argument("--specialists", type=Path, default=DEFAULT_SPECIALISTS_CSV)
    parser.add_argument("--facility-reference", type=Path, default=DEFAULT_FACILITY_REFERENCE_CSV)
    parser.add_argument("--prefecture-geojson", type=Path, default=DEFAULT_PREFECTURE_GEOJSON)
    parser.add_argument("--iryoken2-geojson", type=Path, default=DEFAULT_IRYOKEN2_GEOJSON)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK_CSV)
    parser.add_argument("--audit-out", type=Path, default=DEFAULT_AUDIT_OUT_CSV)
    parser.add_argument("--iryoken2-out", type=Path, default=DEFAULT_IRYOKEN2_OUT_CSV)
    args = parser.parse_args(argv)

    required = [args.specialists, args.facility_reference, args.prefecture_geojson, args.iryoken2_geojson]
    missing = [p for p in required if not p.exists()]
    if missing:
        for p in missing:
            print(f"エラー: {p} が見つかりません。")
        return 1

    roster = load_specialists_facility(args.specialists)
    refs = load_facility_reference(args.facility_reference)
    pref_name_to_code = load_prefecture_geojson(args.prefecture_geojson)
    area_code_to_name, area_code_to_pref_name = load_iryoken2_geojson(args.iryoken2_geojson)

    roster_keys = {(row["pref_name"], row["facility_name"]) for row in roster}
    refs_by_pref_normalized = build_refs_by_pref_normalized(refs)
    try:
        crosswalk_map = load_crosswalk(
            args.crosswalk, roster_keys, set(area_code_to_name), pref_name_to_code, refs_by_pref_normalized
        )
    except SystemExit as e:
        print(str(e))
        return 1
    if args.crosswalk.exists():
        print(f"crosswalk: {args.crosswalk} を読み込みました({len(crosswalk_map)}行)")
    else:
        print(f"crosswalk: {args.crosswalk} が見つからないため、空として続行します")
    print()

    ref_index = build_ref_index(refs)
    results = match_roster(roster, ref_index, pref_name_to_code, crosswalk_map, area_code_to_name)

    write_audit_csv(args.audit_out, results)
    write_iryoken2_csv(args.iryoken2_out, results, area_code_to_name, area_code_to_pref_name)

    print_report(results)

    print(f"出力: {args.audit_out}")
    print(f"出力: {args.iryoken2_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
