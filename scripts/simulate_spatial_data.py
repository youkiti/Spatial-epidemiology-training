#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulate_spatial_data.py — 実データ非依存で教材を完走させるための合成空間データ生成器。

感染症専門医名簿PDF(未取得)・境界データ(issue #4 未着手)のいずれも無い状態で、
概念パート・Rハンズオンの全章がシミュレーションデータのみで動くようにするための
データを2種類生成する(要件定義書 §1.3 原則7、§4.1)。

生成するデータセット:

  (a) toy10 — 架空の10市町村データ(概念導入用)。
      章1で「患者数(count)の地図」と「率(rate)の地図」で順位が入れ替わることを
      見せるための最小データ。2行×5列の格子上に配置し、隣接は rook(上下左右)。
      -> toy10_areas.csv / toy10_neighbors.csv

  (b) lattice — 二次医療圏スケール(既定18行×19列=342地域)の合成データ。
      規則格子(lattice)の上に自前で定義した queen 隣接(縦・横・斜め)を使う。
      本物の二次医療圏ポリゴンはまだリポジトリに無いため、隣接関係を
      「地図から」導くのではなく、格子として直接定義している(CLAUDE.md
      「環境の制約」節を参照。実ポリゴンが入ったら本データセットは差し替える)。
      章3〜4(Global Moran's I・LISA・Gi*)の検証用に、空間自己相関を
      既知の強さで仕込み(--smooth-passes で強さを制御)、かつ
      High-High クラスタ・Low-Low クラスタ・単独高値の空間的アウトライヤー
      (High-Low)を意図的に埋め込む。
      -> lattice_areas.csv / lattice_neighbors.csv

乱数はすべて random.Random(seed) の専用インスタンス経由で消費し、グローバルな
random モジュールの状態は変更しない。同じ --seed であれば何度実行しても
バイト単位で同一の CSV が出力される(検証は verify_simulation.py で行う)。

使い方:
    python scripts/simulate_spatial_data.py --out data/simulated
    python scripts/simulate_spatial_data.py --out data/simulated --seed 1 --rows 12 --cols 12 --smooth-passes 1

終了コード: 生成成功=0、引数不正・格子が小さすぎる等の失敗=1
標準ライブラリのみを使用(pip依存なし)。Python 3.9+。
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Windows のコンソールでも日本語出力が文字化けしないようにする(quiz_lint.py に合わせる)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# =====================================================================
# 共通ユーティリティ
# =====================================================================


def clamp(value: int, lo: int, hi: int) -> int:
    """value を [lo, hi] に収める。"""
    return max(lo, min(hi, value))


def poisson_random(rng: random.Random, lam: float) -> int:
    """自前実装のPoisson乱数生成(numpyが無い環境向け)。

    平均(lam)が小さい場合は Knuth の乗算法(一様乱数を exp(-lam) を下回るまで
    掛け続け、掛けた回数を数える)を使う。この方法は理論的には正確だが、
    lam が大きくなると exp(-lam) が 0 に近づき(浮動小数点のアンダーフロー)、
    かつ平均 lam 回のループが必要になるため実用上遅くなる。
    そのため lam が一定以上(ここでは30)の場合は中心極限定理に基づく
    正規近似 Normal(lam, sqrt(lam)) に切り替え、四捨五入して非負に丸める。
    教材の合成データという用途では、この近似で十分な精度が得られる。
    """
    if lam <= 0:
        return 0
    if lam < 30:
        limit = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= rng.random()
            if p <= limit:
                break
        return k - 1
    # 正規近似(lam が大きいとき)
    value = rng.gauss(lam, math.sqrt(lam))
    return max(0, round(value))


def write_csv(path: Path, header: List[str], rows: List[List[object]]) -> None:
    """行の並び順そのままで CSV を書き出す(呼び出し側で順序を確定させておくこと)。

    改行コードは環境に依らず '\\n' に固定し、同一シードでの再実行時に
    バイト単位で同一の出力になるようにする。
    """
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


# =====================================================================
# (a) toy10 — 架空の10市町村データ
# =====================================================================

# 「人口が大きい市ほど患者数(count)は多いが、率(rate)では上位にならない」を
# 章1で見せるために手で設計した固定値(乱数には依存させない)。
# A市は人口18万・患者180人で人口10万対100(率としては中位)なのに対し、
# B市は人口2.5万・患者75人しかいないが人口10万対300で最も率が高い。
# 「count の地図」と「rate の地図」で1位が入れ替わる例になっている。
_TOY10_NAMES = ["A市", "B市", "C市", "D市", "E市", "F市", "G市", "H市", "I市", "J市"]
_TOY10_POPULATION = [180_000, 25_000, 60_000, 45_000, 90_000, 15_000, 120_000, 35_000, 70_000, 50_000]
_TOY10_CASES = [180, 75, 90, 45, 135, 15, 120, 70, 105, 50]
# 2行×5列の格子座標(x: 列 0-4, y: 行 0-1)。A〜Eが1行目、F〜Jが2行目。
_TOY10_XY = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1)]


def generate_toy10(out_dir: Path) -> None:
    """toy10_areas.csv と toy10_neighbors.csv を書き出す。"""
    n = len(_TOY10_NAMES)
    area_rows: List[List[object]] = []
    for idx in range(n):
        area_id = idx + 1
        population = _TOY10_POPULATION[idx]
        cases = _TOY10_CASES[idx]
        rate_per_100k = cases / population * 100_000
        x, y = _TOY10_XY[idx]
        area_rows.append([
            area_id,
            _TOY10_NAMES[idx],
            population,
            cases,
            f"{rate_per_100k:.1f}",
            x,
            y,
        ])
    write_csv(
        out_dir / "toy10_areas.csv",
        ["area_id", "area_name", "population", "cases", "rate_per_100k", "x", "y"],
        area_rows,
    )

    # rook 隣接(上下左右のみ、斜めは含まない)を 2行×5列の格子から機械的に導出する。
    id_by_xy: Dict[Tuple[int, int], int] = {xy: idx + 1 for idx, xy in enumerate(_TOY10_XY)}
    neighbor_rows: List[List[object]] = []
    for idx in range(n):
        area_id = idx + 1
        x, y = _TOY10_XY[idx]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = id_by_xy.get((x + dx, y + dy))
            if nb is not None:
                neighbor_rows.append([area_id, nb])
    write_csv(out_dir / "toy10_neighbors.csv", ["area_id", "neighbor_id"], neighbor_rows)


# =====================================================================
# (b) lattice — 二次医療圏スケールの合成データ
# =====================================================================

# 埋め込むパターンの強さ(相対リスクとして直接上書きする)。
# 背景の空間自己相関(--smooth-passes で強さを制御)とは独立に、
# 常に検出できる強さで埋め込む。
_HH_RR = 3.0        # High-High クラスタの相対リスク
_LL_RR = 0.3        # Low-Low クラスタの相対リスク
_HL_CENTER_RR = 10.0  # 単独高値の空間的アウトライヤー(中心)の相対リスク
_HL_RING_RR = 0.2     # ↑の8近傍(低いことを保証するための縁)の相対リスク
_FEATURE_POPULATION = 40_000  # 上記の埋め込みセルの人口(乱数任せにせず固定する)

# 背景(埋め込み以外)の相対リスクを作るための係数。
# 平滑化ずみの潜在変数(平均0・分散1に標準化)を exp(k * z) で相対リスクに変換する。
_BACKGROUND_K = 0.4
_BASE_RATE_PER_100K = 80.0  # 期待数 = 人口 / 100,000 * この値


def build_queen_neighbors(rows: int, cols: int) -> Dict[int, List[int]]:
    """queen 隣接(縦・横・斜め)を格子から機械的に構築する(自分自身は含まない)。"""

    def rc_to_id(r: int, c: int) -> int:
        return r * cols + c + 1

    neighbors: Dict[int, List[int]] = {}
    for r in range(rows):
        for c in range(cols):
            area_id = rc_to_id(r, c)
            lst: List[int] = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        lst.append(rc_to_id(nr, nc))
            neighbors[area_id] = lst
    return neighbors


def smooth_field(values: Dict[int, float], neighbors: Dict[int, List[int]], passes: int) -> Dict[int, float]:
    """自分自身を含む近傍平均を passes 回繰り返す移動平均平滑化。

    繰り返すほど隣接セル同士の値が似てくる、つまり空間自己相関が強くなる。
    これが「仕込んだ強さ」の正体であり、verify_simulation.py の受け入れ条件1
    (--smooth-passes を増やすと Global Moran's I が大きくなる)で確認する。
    """
    current = dict(values)
    for _ in range(passes):
        new_field: Dict[int, float] = {}
        for area_id, _v in current.items():
            neigh = neighbors[area_id]
            total = current[area_id] + sum(current[j] for j in neigh)
            new_field[area_id] = total / (1 + len(neigh))
        current = new_field
    return current


def standardize(values: Dict[int, float]) -> Dict[int, float]:
    """平均0・(母)標準偏差1に標準化する。

    平滑化(smooth_field)を繰り返すと値そのものの分散は縮む(移動平均は縮小写像)。
    ここで標準化し直すことで、--smooth-passes の値によらず相対リスクへの
    変換スケールをそろえ、「空間的なまとまり方」だけが変わるようにしている。
    """
    n = len(values)
    mean_v = sum(values.values()) / n
    var = sum((v - mean_v) ** 2 for v in values.values()) / n
    std = math.sqrt(var)
    if std == 0:
        return {k: 0.0 for k in values}
    return {k: (v - mean_v) / std for k, v in values.items()}


def compute_feature_positions(rows: int, cols: int) -> Dict[str, Tuple[int, int]]:
    """HH/LL/HL クラスタの中心座標(row, col)を決める。

    HH・LL は 5x5(内側3x3を教師ラベルとし、外側1マスを「周囲も高い/低い」を
    保証する縁として使う)、HL は本体1マス+8近傍の縁が必要なので、
    それぞれ格子の端から十分な余白を取る。既定の18行×19列を主対象とし、
    小さすぎる格子(各特徴が収まらない・互いに重なる)は呼び出し側でエラーにする。
    """
    hh = (clamp(rows // 4, 2, rows - 3), clamp(cols // 4, 2, cols - 3))
    ll = (clamp(rows * 3 // 4, 2, rows - 3), clamp(cols * 3 // 4, 2, cols - 3))
    hl = (clamp(rows * 4 // 5, 1, rows - 2), clamp(max(2, cols // 10), 1, cols - 2))
    return {"hh": hh, "ll": ll, "hl": hl}


def _block_cells(center: Tuple[int, int], half_width: int, rows: int, cols: int) -> List[Tuple[int, int]]:
    """center を中心とする一辺 (2*half_width+1) の正方形に含まれる (row, col) 一覧。"""
    cr, cc = center
    cells = []
    for r in range(cr - half_width, cr + half_width + 1):
        for c in range(cc - half_width, cc + half_width + 1):
            if 0 <= r < rows and 0 <= c < cols:
                cells.append((r, c))
    return cells


def _rects_overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    """(r0, r1, c0, c1) 形式の矩形2つが重なるか。"""
    ar0, ar1, ac0, ac1 = a
    br0, br1, bc0, bc1 = b
    return not (ar1 < br0 or br1 < ar0 or ac1 < bc0 or bc1 < ac0)


def generate_lattice(out_dir: Path, rows: int, cols: int, smooth_passes: int, rng: random.Random) -> None:
    """lattice_areas.csv と lattice_neighbors.csv を書き出す。"""
    if rows < 12 or cols < 12:
        raise ValueError(
            f"--rows/--cols が小さすぎます(rows={rows}, cols={cols})。"
            "HH/LL/HL の3特徴が重ならずに収まるには各12以上を推奨します。"
        )

    n = rows * cols
    neighbors = build_queen_neighbors(rows, cols)

    positions = compute_feature_positions(rows, cols)
    hh_cells = _block_cells(positions["hh"], 2, rows, cols)  # 5x5(縁込み)
    hh_core = set(_block_cells(positions["hh"], 1, rows, cols))  # 内側3x3のみ HH ラベル
    ll_cells = _block_cells(positions["ll"], 2, rows, cols)
    ll_core = set(_block_cells(positions["ll"], 1, rows, cols))
    hl_center = positions["hl"]
    hl_ring = [c for c in _block_cells(hl_center, 1, rows, cols) if c != hl_center]

    def bbox(cells: List[Tuple[int, int]]) -> Tuple[int, int, int, int]:
        rs = [r for r, _ in cells]
        cs = [c for _, c in cells]
        return (min(rs), max(rs), min(cs), max(cs))

    hh_box = bbox(hh_cells)
    ll_box = bbox(ll_cells)
    hl_box = bbox([hl_center] + hl_ring)
    if _rects_overlap(hh_box, ll_box) or _rects_overlap(hh_box, hl_box) or _rects_overlap(ll_box, hl_box):
        raise ValueError(
            "HH/LL/HL の埋め込み領域が重なりました。--rows/--cols をもっと大きくしてください。"
        )

    def rc_to_id(r: int, c: int) -> int:
        return r * cols + c + 1

    hh_core_ids = {rc_to_id(r, c) for r, c in hh_core}
    ll_core_ids = {rc_to_id(r, c) for r, c in ll_core}
    hh_all_ids = {rc_to_id(r, c) for r, c in hh_cells}
    ll_all_ids = {rc_to_id(r, c) for r, c in ll_cells}
    hl_center_id = rc_to_id(*hl_center)
    hl_ring_ids = {rc_to_id(r, c) for r, c in hl_ring}
    feature_ids = hh_all_ids | ll_all_ids | {hl_center_id} | hl_ring_ids

    # --- 背景の潜在変数(空間自己相関の仕込み) -----------------------------
    noise = {area_id: rng.gauss(0.0, 1.0) for area_id in range(1, n + 1)}
    smoothed = smooth_field(noise, neighbors, smooth_passes)
    z_background = standardize(smoothed)

    area_rows: List[List[object]] = []
    for area_id in range(1, n + 1):
        r, c = divmod(area_id - 1, cols)

        if area_id in feature_ids:
            population = _FEATURE_POPULATION
        else:
            # 対数正規分布で人口にばらつきを持たせる(小地域の少数例の不安定さを
            # 見せられるよう、中央値を低めに・裾を長めに取っている)。
            raw = rng.lognormvariate(math.log(25_000), 0.8)
            population = int(clamp(round(raw), 800, 300_000))
            # 17区画に1つの割合で、意図的にごく小さい人口の地域を混ぜる
            # (対数正規分布の裾だけに頼らず、小地域を確実に含めるため)。
            if area_id % 17 == 0:
                population = rng.randint(500, 3000)

        expected_cases = population / 100_000 * _BASE_RATE_PER_100K

        if area_id in hh_core_ids:
            truth_label = "HH"
            rr = _HH_RR
        elif area_id in ll_core_ids:
            truth_label = "LL"
            rr = _LL_RR
        elif area_id == hl_center_id:
            truth_label = "HL"
            rr = _HL_CENTER_RR
        elif area_id in hl_ring_ids:
            truth_label = "background"
            rr = _HL_RING_RR
        elif area_id in hh_all_ids:
            # HH の内側3x3を「周囲も高い」にするための縁(ラベルは background)
            truth_label = "background"
            rr = _HH_RR
        elif area_id in ll_all_ids:
            truth_label = "background"
            rr = _LL_RR
        else:
            truth_label = "background"
            rr = math.exp(_BACKGROUND_K * z_background[area_id])

        observed_cases = poisson_random(rng, expected_cases * rr)
        rate_per_100k = observed_cases / population * 100_000
        sir = observed_cases / expected_cases if expected_cases > 0 else 0.0

        area_rows.append([
            area_id,
            r,
            c,
            population,
            f"{expected_cases:.3f}",
            observed_cases,
            f"{rate_per_100k:.2f}",
            f"{sir:.3f}",
            truth_label,
        ])

    write_csv(
        out_dir / "lattice_areas.csv",
        ["area_id", "row", "col", "population", "expected_cases", "observed_cases", "rate_per_100k", "sir", "truth_label"],
        area_rows,
    )

    neighbor_rows: List[List[object]] = []
    for area_id in range(1, n + 1):
        for nb in neighbors[area_id]:
            neighbor_rows.append([area_id, nb])
    write_csv(out_dir / "lattice_neighbors.csv", ["area_id", "neighbor_id"], neighbor_rows)


# =====================================================================
# CLI
# =====================================================================


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="空間疫学教材用の合成データ生成器")
    parser.add_argument("--out", type=Path, default=Path("data/simulated"), help="出力先ディレクトリ")
    parser.add_argument("--seed", type=int, default=20260818, help="乱数シード(既定: 20260818)")
    parser.add_argument("--rows", type=int, default=18, help="lattice の行数(既定: 18)")
    parser.add_argument("--cols", type=int, default=19, help="lattice の列数(既定: 19)")
    parser.add_argument("--smooth-passes", type=int, default=3, help="空間自己相関を仕込む平滑化の回数(既定: 3)")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    if args.smooth_passes < 0:
        print("エラー: --smooth-passes は0以上を指定してください。")
        return 1

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)

    generate_toy10(out_dir)
    try:
        generate_lattice(out_dir, args.rows, args.cols, args.smooth_passes, rng)
    except ValueError as e:
        print(f"エラー: {e}")
        return 1

    print("生成完了:")
    print(f"  {out_dir / 'toy10_areas.csv'}(10地域)")
    print(f"  {out_dir / 'toy10_neighbors.csv'}")
    print(f"  {out_dir / 'lattice_areas.csv'}({args.rows * args.cols}地域、smooth-passes={args.smooth_passes})")
    print(f"  {out_dir / 'lattice_neighbors.csv'}")
    print(f"  乱数シード: {args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
