#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_facility_reference.py — 感染症専門医名簿の施設名に座標を与えるための
「参照点テーブル」を作る(issue #9 の第1チャンク。名寄せ本体は次のチャンクで行う)。

## 何をするか

医療情報ネット(医療機能情報提供制度)の病院票・診療所票(`data/raw/*.zip`、
それぞれ2025-06-01時点のスナップショット)を読み、使える座標を持つ施設に
都道府県と二次医療圏を割り付けて `data/interim/facility_reference.csv` に書く。
既定では国土数値情報「医療機関データ」P04-20(令和2年度・点データ)も同じ表に
追加する。`--skip-p04` を付けたときだけ P04 を読まない。

P04 は既定で読む(2026-08-18、issue #9 名寄せチャンクでの実測に基づく決定。
`--include-p04` を既定オフから反転した)。理由: 医療情報ネットの一括公開ファイルは
都道府県ごとの網羅性が大きく違う(実測で沖縄県は診療所91件、京都府は626件しか
無い)。`島根県立中央病院`・`京都市立病院`・`自治医科大学附属病院`・
`国立病院機構東京医療センター` はいずれも医療情報ネット側に存在せず P04 にのみ
存在する。P04 を足すと専門医名簿の突合(自動割付)が専門医数ベースで
52.9% → 59.1% に上がることを確認済み。

このスクリプトは施設名の名寄せ(専門医名簿の施設名とここで作る参照点との突合)は
行わない。`facility_name_normalized`(`scripts/lib_facility_name.py` による正規化
結果)まで出力し、名寄せ自体は次のチャンクに委ねる。

## 座標の扱い

医療情報ネットの座標欠測センチネルは空欄ではなく `0.0`/`0.0`(実測で全体の
約5.4%が該当)。空欄判定だけでは検出できないため、必ず日本の範囲
(緯度20〜46度・経度122〜154度)で判定する。空欄・数値でない・センチネル・
その他の範囲外は、それぞれ別カウントとして標準出力に内訳を出す(黙って
まとめて捨てない)。

## 点-多角形判定

`data/geo/prefecture.geojson`(47件)と `data/geo/iryoken2.geojson`(339件)
に対し、0.5度グリッドで候補ポリゴンを絞ってからレイキャスティングで判定する
(`AreaIndex` / `point_in_geometry` ほか)。都道府県・二次医療圏のどのポリゴンにも
属さない点は必ず一定数出るが、理由は一様ではない: `iryoken2.geojson` が1km²未満の
離島リングを除去済み(`data/geo/README.md`)であることに加え、原典(医療情報ネット/
P04)側の座標そのものが丸められている行が実際に混在する(例: 経度が小数第1位までしか
無い)。原因を混同しないよう、件数だけでなく該当点(ソース・施設名・住所・座標)を
全件、標準出力に列挙する。

## 出典(逐語移植した箇所)

隣リポジトリ visualize-regional-medical-care-for-2040
(同一著者。https://github.com/youkiti/visualize-regional-medical-care-for-2040)
の以下を移植している。各関数のdocstringにも個別に
出典コメントを付けている:

- `tools/build_facility_geo_audit.py` の `_read_single_member_csv()`
- `tools/build_facility_geo_linkage.py` の `point_in_geometry()` /
  `_point_in_polygon_coords()` / `_point_in_ring()` / `_geometry_bbox()` /
  `AreaIndex`(区域コードのプロパティ名を引数で選べるよう最小限変更) /
  `iter_p04_raw_features()`

施設名の正規化(`normalize_facility_name()`)は `scripts/lib_facility_name.py`
に移植済みのものをそのまま使う。

## 入力

- `data/raw/01-1_hospital_facility_info_20250601.zip`(医療情報ネット 病院)
- `data/raw/02-1_clinic_facility_info_20250601.zip`(医療情報ネット 診療所)
- `data/raw/P04-20_GML.zip`(国土数値情報 医療機関データ、`--skip-p04`指定時は読まない)
- `data/geo/prefecture.geojson` / `data/geo/iryoken2.geojson`

## 出力

`data/interim/facility_reference.csv`(列: source, ref_id, facility_name,
facility_name_normalized, pref_code_declared, pref_code_pip, iryoken2_code,
lon, lat, address)

必要環境: Python 3.9+(追加依存なし。標準ライブラリのみ)

使い方:
    PYTHONUTF8=1 python scripts/build_facility_reference.py
    PYTHONUTF8=1 python scripts/build_facility_reference.py --skip-p04

終了コード: 正常終了0、入力が見つからない等のエラー1
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# scripts/lib_facility_name.py は同じ scripts/ ディレクトリにある。実行時の
# カレントディレクトリに依存させないよう明示的にパスを追加してから import する。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_facility_name  # noqa: E402 (パス追加の後に import する必要がある)

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
GEO_DIR = REPO_ROOT / "data" / "geo"
INTERIM_DIR = REPO_ROOT / "data" / "interim"

HOSPITAL_ZIP = RAW_DIR / "01-1_hospital_facility_info_20250601.zip"
CLINIC_ZIP = RAW_DIR / "02-1_clinic_facility_info_20250601.zip"
P04_ZIP = RAW_DIR / "P04-20_GML.zip"
P04_MEMBER_NAME = "P04-20_GML/P04-20.geojson"

PREFECTURE_GEOJSON = GEO_DIR / "prefecture.geojson"
IRYOKEN2_GEOJSON = GEO_DIR / "iryoken2.geojson"

DEFAULT_OUT_CSV = INTERIM_DIR / "facility_reference.csv"

# --- 医療情報ネット側の列名(定義書 data/raw/001306376.xlsx の見出しそのまま) ---
COL_ID = "ID"
COL_NAME = "正式名称"
COL_PREF_CODE = "都道府県コード"
COL_ADDRESS = "所在地"
COL_LAT = "所在地座標（緯度）"
COL_LON = "所在地座標（経度）"

# --- P04(国土数値情報 医療機関データ)側の列定数 ---
P04_CATEGORY = "P04_001"  # 1=病院 / 2=診療所 / 3=歯科診療所(対象外)
P04_NAME = "P04_002"
P04_ADDRESS = "P04_003"

CATEGORY_HOSPITAL = 1
CATEGORY_CLINIC = 2
CATEGORY_DENTAL = 3

SOURCE_HOSPITAL = "iryojoho_hospital"
SOURCE_CLINIC = "iryojoho_clinic"
SOURCE_P04 = "ksj_p04"

# 日本の領域。医療情報ネットの座標欠測センチネルは空欄ではなく `0.0`/`0.0` で、
# 実測5.4%が該当する。範囲判定にしないと静かにギニア湾沖の点を採ってしまう。
LAT_MIN, LAT_MAX = 20.0, 46.0
LON_MIN, LON_MAX = 122.0, 154.0

OUTPUT_HEADER = [
    "source",
    "ref_id",
    "facility_name",
    "facility_name_normalized",
    "pref_code_declared",
    "pref_code_pip",
    "iryoken2_code",
    "lon",
    "lat",
    "address",
]

# 点-多角形判定の候補ポリゴンを絞るグリッドのセルサイズ(度)。
GRID_CELL_DEG = 0.5


# ===========================================================================
# 1. zip内CSVの読み込み(医療情報ネット)
# ===========================================================================


def _read_single_member_csv(zip_path: Path) -> list:
    """zip内のCSV1本をUTF-8(BOM付き)として読む。

    出典: visualize-regional-medical-care-for-2040
          tools/build_facility_geo_audit.py の `_read_single_member_csv()` を移植。
          同一著者のリポジトリ。移植日 2026-08-18。

    zipのエントリ名は言語エンコーディングフラグ(0x800)を見て復号を分岐する
    必要がある(無条件にcp437→cp932変換するとUTF-8フラグ付きの名前が壊れる)。
    `zipfile.ZipInfo`(`ZipFile.infolist()`が返す)はこのフラグを標準ライブラリ
    側で既に見ており、`i.filename`はそれに従って正しく復号済みの文字列に
    なっている。この関数はその`i.filename`をそのまま使うだけでよく、
    `ZipFile.namelist()`相当の文字列を独自にcp437/cp932変換する実装に
    置き換えてはいけない(この分岐を落とさないこと、というbrief指示の対象)。
    """
    with zipfile.ZipFile(zip_path) as z:
        members = [i for i in z.infolist() if not i.is_dir()]
        if len(members) != 1:
            raise SystemExit(f"{zip_path.name}: zip内のファイルが1本ではありません({len(members)}本)")
        raw = z.read(members[0].filename)
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def _classify_coordinate(lat_val, lon_val):
    """緯度経度を分類する。

    使えれば `((lon, lat), "ok")`、使えなければ `(None, reason)` を返す。
    `reason` は次のいずれか:
      - "missing": 空欄(またはNone)
      - "unparseable": 数値としてパースできない
      - "sentinel": 緯度経度がともに`0.0`(医療情報ネットの座標欠測センチネル。
        空欄ではないため空欄判定では検出できない。実測5.4%が該当)
      - "out_of_range": 上記以外で日本の範囲(緯度20〜46度・経度122〜154度)外

    センチネルとそれ以外の範囲外を別カウントにしているのは、brief(標準出力の
    内訳要件)がセンチネル/範囲外/欠測/パース不能を区別して報告することを
    求めているため。
    """
    if lat_val is None or lon_val is None:
        return None, "missing"
    lat_s = str(lat_val).strip()
    lon_s = str(lon_val).strip()
    if not lat_s or not lon_s:
        return None, "missing"
    try:
        lat = float(lat_s)
        lon = float(lon_s)
    except ValueError:
        return None, "unparseable"
    if lat == 0.0 and lon == 0.0:
        return None, "sentinel"
    if not (LAT_MIN < lat < LAT_MAX and LON_MIN < lon < LON_MAX):
        return None, "out_of_range"
    return (lon, lat), "ok"


# ===========================================================================
# 2. 点-多角形判定(純Python、追加依存なし)
#
# 出典: visualize-regional-medical-care-for-2040
#       tools/build_facility_geo_linkage.py の `point_in_geometry()` /
#       `_point_in_polygon_coords()` / `_point_in_ring()` / `_geometry_bbox()` /
#       `AreaIndex` を移植。同一著者のリポジトリ。移植日 2026-08-18。
#       `AreaIndex` のみ、区域コードのプロパティ名(`pref_code`/`area_code`)を
#       呼び出し側で選べるよう`code_property`引数を追加している(元は
#       `area_code`固定)。判定ロジック自体は変更していない。
# ===========================================================================


def _geometry_bbox(geometry: dict):
    """Polygon/MultiPolygonのbbox `(minx, miny, maxx, maxy)` を求める。"""
    gtype = geometry["type"]
    depth = {"Polygon": 2, "MultiPolygon": 3}.get(gtype)
    if depth is None:
        raise ValueError(f"Polygon/MultiPolygon以外のジオメトリです: {gtype!r}")
    xs, ys = [], []

    def walk(coords, d):
        if d == 0:
            xs.append(coords[0])
            ys.append(coords[1])
        else:
            for c in coords:
                walk(c, d - 1)

    walk(geometry["coordinates"], depth)
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_ring(x: float, y: float, ring) -> bool:
    """標準的なレイキャスティング(交差数の偶奇判定)による点-環内判定。"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _point_in_polygon_coords(x: float, y: float, polygon_coords) -> bool:
    """`polygon_coords`(`[外環, 内環(穴)1, 内環2, ...]`)に対する点-多角形判定。"""
    if not polygon_coords:
        return False
    if not _point_in_ring(x, y, polygon_coords[0]):
        return False
    for hole in polygon_coords[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True


def point_in_geometry(x: float, y: float, geometry: dict) -> bool:
    """GeoJSON geometry(Polygon/MultiPolygon)に対する点-多角形判定。"""
    gtype = geometry["type"]
    if gtype == "Polygon":
        return _point_in_polygon_coords(x, y, geometry["coordinates"])
    if gtype == "MultiPolygon":
        return any(_point_in_polygon_coords(x, y, poly) for poly in geometry["coordinates"])
    raise ValueError(f"Polygon/MultiPolygon以外のジオメトリです: {gtype!r}")


class AreaIndex:
    """ポリゴン集合(都道府県 または 二次医療圏)に対する点-多角形判定を、
    グリッドで候補ポリゴンを絞ってから行う索引。全点×全ポリゴンの総当たりを
    避けるためのもの。`code_property`で区域コードのプロパティ名を指定する
    (都道府県なら`pref_code`、二次医療圏なら`area_code`)。
    """

    def __init__(self, boundaries_geojson: dict, code_property: str, *, cell_deg: float = GRID_CELL_DEG):
        self._cell_deg = cell_deg
        self._areas = []
        for feat in boundaries_geojson["features"]:
            bbox = _geometry_bbox(feat["geometry"])
            self._areas.append(
                {"code": feat["properties"][code_property], "bbox": bbox, "geometry": feat["geometry"]}
            )
        self._grid = defaultdict(list)
        for area in self._areas:
            minx, miny, maxx, maxy = area["bbox"]
            for gx in range(self._cell(minx), self._cell(maxx) + 1):
                for gy in range(self._cell(miny), self._cell(maxy) + 1):
                    self._grid[(gx, gy)].append(area)

    def _cell(self, v: float) -> int:
        return int(v // self._cell_deg)

    @property
    def area_count(self) -> int:
        return len(self._areas)

    def find_code(self, lon: float, lat: float):
        """`(lon, lat)`を含むポリゴンの区域コードを返す。どのポリゴンにも
        属さなければ`None`(境界簡略化時の離島除去のほか、原典側の座標が
        丸められている等の理由で実際に発生する)。
        """
        key = (self._cell(lon), self._cell(lat))
        for area in self._grid.get(key, ()):
            minx, miny, maxx, maxy = area["bbox"]
            if not (minx <= lon <= maxx and miny <= lat <= maxy):
                continue
            if point_in_geometry(lon, lat, area["geometry"]):
                return area["code"]
        return None


# ===========================================================================
# 3. P04-20.geojson のストリーム読み込み
#
# 出典: visualize-regional-medical-care-for-2040
#       tools/build_facility_geo_linkage.py の `iter_p04_raw_features()` を移植。
#       同一著者のリポジトリ。移植日 2026-08-18。
# ===========================================================================


def iter_p04_raw_features(zip_path: Path, member_name: str = P04_MEMBER_NAME, chunk_size: int = 1 << 20):
    """P04-20.geojsonの`features`配列を、ファイル全体を一度に読み切らずに
    1フィーチャずつ返すジェネレータ。

    「1フィーチャ1行」という改行レイアウトには依存しない(`json.JSONDecoder()
    .raw_decode`をバッファ上で逐次適用し、1オブジェクト読むたびに消費済みの
    先頭を捨てる)。将来mapshaper等の出力形式(改行位置)が変わっても壊れない。
    """
    decoder = json.JSONDecoder()
    marker = '"features"'
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member_name) as raw:
            text_stream = io.TextIOWrapper(raw, encoding="utf-8")
            buf = ""
            # --- "features" キーの直後の "[" までスキップ ---
            while True:
                idx = buf.find(marker)
                if idx != -1:
                    bracket_idx = buf.find("[", idx)
                    if bracket_idx != -1:
                        buf = buf[bracket_idx + 1:]
                        break
                chunk = text_stream.read(chunk_size)
                if not chunk:
                    raise ValueError(f"{member_name}: \"features\"配列の開始が見つかりません")
                buf += chunk

            # --- 1オブジェクトずつ取り出す ---
            pos = 0
            while True:
                while pos < len(buf) and buf[pos] in " \t\r\n,":
                    pos += 1
                while pos >= len(buf):
                    chunk = text_stream.read(chunk_size)
                    if not chunk:
                        raise ValueError(f"{member_name}: features配列の終端']'が見つかりません")
                    buf += chunk
                if buf[pos] == "]":
                    break
                while True:
                    try:
                        obj, end = decoder.raw_decode(buf, pos)
                        break
                    except json.JSONDecodeError:
                        chunk = text_stream.read(chunk_size)
                        if not chunk:
                            raise
                        buf += chunk
                yield obj
                pos = end
                # 消費済みの先頭を捨ててバッファを縮める(メモリを増やし続けない)。
                if pos > chunk_size:
                    buf = buf[pos:]
                    pos = 0


# ===========================================================================
# 4. 参照点テーブルの生成
# ===========================================================================


def process_iryojoho(zip_path: Path, source: str, pref_index: AreaIndex, iryoken2_index: AreaIndex, writer, stats: dict) -> None:
    """医療情報ネットの1本(病院 or 診療所)を読み、座標が使える行を`writer`に
    書き出しながら`stats`に集計する。

    `stats["read_counts"][source]` は読み込んだ全行数(座標の可否を問わない)、
    `stats["written_counts"][source]` はそのうち実際にCSVへ書き出した件数
    (座標が使えた行のみ)。意味が異なる2つの数を同じキーに混ぜない。
    """
    rows = _read_single_member_csv(zip_path)
    if rows:
        for col in (COL_ID, COL_NAME, COL_PREF_CODE, COL_ADDRESS, COL_LAT, COL_LON):
            if col not in rows[0]:
                raise SystemExit(f"{zip_path.name}: 期待した列 {col!r} がありません(原典のレイアウト変更)")
    stats["read_counts"][source] = len(rows)
    exclude = stats["exclude_counts"][source]
    written = 0

    for row in rows:
        coord, reason = _classify_coordinate(row.get(COL_LAT), row.get(COL_LON))
        if coord is None:
            exclude[reason] += 1
            continue
        lon, lat = coord
        pref_code_pip = pref_index.find_code(lon, lat)
        iryoken2_code = iryoken2_index.find_code(lon, lat)
        name = row.get(COL_NAME) or ""
        address = row.get(COL_ADDRESS) or ""
        if pref_code_pip is None:
            stats["outside_pref"][source] += 1
            stats["outside_pref_points"].append(
                {"source": source, "facility_name": name, "address": address, "lon": lon, "lat": lat}
            )
        if iryoken2_code is None:
            stats["outside_iryoken2"][source] += 1
            stats["outside_iryoken2_points"].append(
                {"source": source, "facility_name": name, "address": address, "lon": lon, "lat": lat}
            )

        pref_raw = (row.get(COL_PREF_CODE) or "").strip()
        pref_code_declared = pref_raw.zfill(2) if pref_raw else ""
        if pref_code_declared and pref_code_pip and pref_code_declared != pref_code_pip:
            stats["pref_mismatch"][source] += 1

        writer.writerow(
            [
                source,
                (row.get(COL_ID) or "").strip(),
                name,
                lib_facility_name.normalize_facility_name(name),
                pref_code_declared,
                pref_code_pip or "",
                iryoken2_code or "",
                lon,
                lat,
                address,
            ]
        )
        written += 1

    stats["written_counts"][source] = written


def process_p04(zip_path: Path, pref_index: AreaIndex, iryoken2_index: AreaIndex, writer, stats: dict) -> None:
    """P04(国土数値情報 医療機関データ)を読み、歯科診療所(P04_001==3)を除いた
    座標が使える行を`writer`に書き出しながら`stats`に集計する。

    P04の住所は原則として都道府県名を含まない(=都道府県の自己申告が無い)ため、
    `pref_code_declared`は常に空にし、点-多角形判定による`pref_code_pip`だけを
    持たせる。

    `stats["read_counts"][SOURCE_P04]` は対象カテゴリ(病院+診療所、歯科除く)の
    フィーチャ数(座標の可否を問わない)。`stats["written_counts"][SOURCE_P04]`
    はそのうち実際にCSVへ書き出した件数(座標が使えた行のみ)。医療情報ネット側の
    `read_counts`(=全行読み込み数)と表の意味を揃えるため、書き込み数を
    `read_counts`に紛れ込ませない(除外が0件のときだけ両者が一致して見えるが、
    除外が出た瞬間にズレる)。
    """
    category_counts = Counter()
    target_read = 0
    written = 0
    exclude = stats["exclude_counts"][SOURCE_P04]

    for idx, feat in enumerate(iter_p04_raw_features(zip_path)):
        props = feat["properties"]
        category = props.get(P04_CATEGORY)
        category_counts[category] += 1
        if category not in (CATEGORY_HOSPITAL, CATEGORY_CLINIC):
            continue
        target_read += 1

        coords = (feat.get("geometry") or {}).get("coordinates") or []
        lon_raw = coords[0] if len(coords) > 0 else None
        lat_raw = coords[1] if len(coords) > 1 else None
        coord, reason = _classify_coordinate(lat_raw, lon_raw)
        if coord is None:
            exclude[reason] += 1
            continue
        lon, lat = coord
        pref_code_pip = pref_index.find_code(lon, lat)
        iryoken2_code = iryoken2_index.find_code(lon, lat)
        name = props.get(P04_NAME) or ""
        address = props.get(P04_ADDRESS) or ""
        if pref_code_pip is None:
            stats["outside_pref"][SOURCE_P04] += 1
            stats["outside_pref_points"].append(
                {"source": SOURCE_P04, "facility_name": name, "address": address, "lon": lon, "lat": lat}
            )
        if iryoken2_code is None:
            stats["outside_iryoken2"][SOURCE_P04] += 1
            stats["outside_iryoken2_points"].append(
                {"source": SOURCE_P04, "facility_name": name, "address": address, "lon": lon, "lat": lat}
            )

        writer.writerow(
            [
                SOURCE_P04,
                str(idx),
                name,
                lib_facility_name.normalize_facility_name(name),
                "",  # pref_code_declared: P04は住所に都道府県名を持たないため空
                pref_code_pip or "",
                iryoken2_code or "",
                lon,
                lat,
                address,
            ]
        )
        written += 1

    stats["read_counts"][SOURCE_P04] = target_read
    stats["written_counts"][SOURCE_P04] = written
    stats["p04_category_counts"] = category_counts


# ===========================================================================
# 5. main
# ===========================================================================


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        description="専門医名簿の施設名に座標を与えるための参照点テーブルを作る(名寄せ本体は次のチャンク)"
    )
    parser.add_argument(
        "--skip-p04",
        action="store_true",
        help="国土数値情報P04(医療機関データ、令和2年度)を読み込まない(既定では読む。"
        "医療情報ネットの一括公開ファイルは都道府県ごとの網羅性が大きく違い、P04にしか"
        "無い施設が実在するため既定でオンにしている。詳細はモジュールdocstring参照)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_CSV,
        help=f"出力CSVのパス(既定: {DEFAULT_OUT_CSV})",
    )
    args = parser.parse_args(argv)

    required = [HOSPITAL_ZIP, CLINIC_ZIP, PREFECTURE_GEOJSON, IRYOKEN2_GEOJSON]
    if not args.skip_p04:
        required.append(P04_ZIP)
    missing = [p for p in required if not p.exists()]
    if missing:
        for p in missing:
            print(f"エラー: {p} が見つかりません。")
        return 1

    with PREFECTURE_GEOJSON.open(encoding="utf-8") as f:
        pref_geojson = json.load(f)
    with IRYOKEN2_GEOJSON.open(encoding="utf-8") as f:
        iryoken2_geojson = json.load(f)
    pref_index = AreaIndex(pref_geojson, "pref_code")
    iryoken2_index = AreaIndex(iryoken2_geojson, "area_code")
    print(f"都道府県ポリゴン: {pref_index.area_count}件 / 二次医療圏ポリゴン: {iryoken2_index.area_count}件")
    print()

    stats = {
        "read_counts": {},
        "written_counts": {},
        "exclude_counts": defaultdict(Counter),
        "outside_pref": Counter(),
        "outside_iryoken2": Counter(),
        "pref_mismatch": Counter(),
        "outside_pref_points": [],
        "outside_iryoken2_points": [],
        "p04_category_counts": Counter(),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(OUTPUT_HEADER)

        process_iryojoho(HOSPITAL_ZIP, SOURCE_HOSPITAL, pref_index, iryoken2_index, writer, stats)
        process_iryojoho(CLINIC_ZIP, SOURCE_CLINIC, pref_index, iryoken2_index, writer, stats)

        if not args.skip_p04:
            process_p04(P04_ZIP, pref_index, iryoken2_index, writer, stats)

    # --- 標準出力へのレポート ---
    print("== ソース別の読み込み行数(座標の可否を問わない) ==")
    total_read = 0
    for source, count in stats["read_counts"].items():
        print(f"  {source}: {count}件")
        total_read += count
    print(f"  合計: {total_read}件")
    print()

    print("== ソース別の書き込み件数(座標が使えた行のみ) ==")
    total_written = 0
    for source, count in stats["written_counts"].items():
        print(f"  {source}: {count}件")
        total_written += count
    print(f"  合計: {total_written}件")
    print()

    print("== 座標が使えず除外した件数(内訳: 欠測/パース不能/センチネル/範囲外) ==")
    total_excluded = 0
    for source, counter in stats["exclude_counts"].items():
        sub_total = sum(counter.values())
        total_excluded += sub_total
        print(
            f"  {source}: 計{sub_total}件"
            f"(欠測{counter['missing']}・パース不能{counter['unparseable']}・"
            f"センチネル{counter['sentinel']}・範囲外{counter['out_of_range']})"
        )
    print(f"  合計: {total_excluded}件")
    print()

    print("== 都道府県ポリゴンのどれにも属さなかった点(ソース別) ==")
    total_outside_pref = 0
    for source in stats["written_counts"]:
        count = stats["outside_pref"].get(source, 0)
        print(f"  {source}: {count}件")
        total_outside_pref += count
    print(f"  合計: {total_outside_pref}件")
    print()

    print(
        "== 二次医療圏ポリゴンのどれにも属さなかった点(ソース別。"
        "iryoken2.geojsonの離島リング除去に加え、原典側の座標が丸められている等の"
        "行も混在する。原因は下記の内訳一覧で個別に確認すること) =="
    )
    total_outside_iryoken2 = 0
    for source in stats["written_counts"]:
        count = stats["outside_iryoken2"].get(source, 0)
        print(f"  {source}: {count}件")
        total_outside_iryoken2 += count
    print(f"  合計: {total_outside_iryoken2}件")
    print()

    print("== pref_code_declared と pref_code_pip が食い違った件数(ソース別。医療情報ネットのみ該当) ==")
    total_pref_mismatch = 0
    for source in stats["written_counts"]:
        count = stats["pref_mismatch"].get(source, 0)
        print(f"  {source}: {count}件")
        total_pref_mismatch += count
    print(f"  合計: {total_pref_mismatch}件")
    print()

    print(f"== 都道府県ポリゴンのどれにも属さなかった点の内訳(全{len(stats['outside_pref_points'])}件) ==")
    for p in stats["outside_pref_points"]:
        print(f"  [{p['source']}] {p['facility_name']} / {p['address']} / lon={p['lon']} lat={p['lat']}")
    print()

    print(f"== 二次医療圏ポリゴンのどれにも属さなかった点の内訳(全{len(stats['outside_iryoken2_points'])}件) ==")
    for p in stats["outside_iryoken2_points"]:
        print(f"  [{p['source']}] {p['facility_name']} / {p['address']} / lon={p['lon']} lat={p['lat']}")
    print()

    if not args.skip_p04:
        print("== P04 医療機関分類の内訳(全フィーチャ、歯科含む) ==")
        labels = {CATEGORY_HOSPITAL: "病院", CATEGORY_CLINIC: "診療所", CATEGORY_DENTAL: "歯科診療所(対象外)"}
        for category, count in sorted(stats["p04_category_counts"].items(), key=lambda kv: (kv[0] is None, kv[0])):
            print(f"  {labels.get(category, f'不明({category})')}: {count}件")
        print()

    print(f"出力: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
