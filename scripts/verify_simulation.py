#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_simulation.py — simulate_spatial_data.py が生成した合成データの受け入れ条件検査ツール。

lattice_areas.csv / lattice_neighbors.csv(二次医療圏スケールの合成データ)を読み込み、
Global Moran's I・Local Moran's I(LISA)・Getis-Ord Gi* を自前で計算して、以下を確認する。

  条件1: Global Moran's I が有意に正(permutation test の疑似p値 < 0.05)。
         「空間自己相関を仕込んだ」ことがデータに反映されていることの確認。
         (--smooth-passes を変えると I が単調に大きくなる、という「仕込んだ強さとの
          整合」そのものは --sweep オプションで確認する。下記参照)
  条件2: truth_label が "HH" のセルが LISA で High-High、"LL" のセルが
         Low-Low として、それぞれ多数派で検出される。
  条件3: truth_label が "HL"(単独高値の空間的アウトライヤー)のセルが、
         LISA では High-Low として検出され、かつ Gi* では
         hot spot(z >= 1.96)として検出されないこと。
         教材の山場(章4: 「値が高い」≠「hot spot」)そのものの検証。

いずれも標準ライブラリのみで計算する(spdep 等の R パッケージは使わない。
R 側での再確認用に scripts/verify_simulation.R を別途用意している)。

--sweep オプション: 「仕込んだ強さに整合する値が出る」こと(issue #6 の受け入れ条件の
核心)は、人が --smooth-passes を変えて2回生成・2回検証して数値を目で比べるだけでは
リポジトリに何も残らない。--sweep を付けると、simulate_spatial_data.py を import して
--sweep-passes(既定 "1,2,3")の smooth-passes で一時ディレクトリに格子データを
生成し直し、それぞれの Global Moran's I を計算して単調増加しているかをコマンド1回で
自動判定する(data/simulated/ のコミット済みCSVは一切書き換えない)。

使い方:
    python scripts/verify_simulation.py
    python scripts/verify_simulation.py --data-dir data/simulated --permutations 999
    python scripts/verify_simulation.py --sweep
    python scripts/verify_simulation.py --sweep --sweep-passes 1,2,3,5

終了コード: 受け入れ条件すべて満たす=0、いずれか満たさない=1
標準ライブラリのみを使用(pip依存なし)。Python 3.9+。
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

# simulate_spatial_data.py は同じ scripts/ ディレクトリにある。
# python scripts/verify_simulation.py のようにスクリプトとして実行された場合、
# そのディレクトリは既に sys.path[0] に入っているはずだが、実行時のカレント
# ディレクトリに依存させないよう明示的にも追加しておく。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulate_spatial_data as sim_data  # noqa: E402 (パス追加の後に import する必要がある)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

HOTSPOT_Z_THRESHOLD = 1.96  # Gi* が hot spot とみなす z スコアの閾値(両側5%相当)
ALPHA = 0.05


# =====================================================================
# 入出力
# =====================================================================


def read_areas(path: Path) -> Dict[int, dict]:
    areas: Dict[int, dict] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            area_id = int(row["area_id"])
            areas[area_id] = {
                "population": int(row["population"]),
                "rate_per_100k": float(row["rate_per_100k"]),
                "sir": float(row["sir"]),
                "truth_label": row["truth_label"],
            }
    return areas


def read_neighbors(path: Path) -> Dict[int, List[int]]:
    neighbors: Dict[int, List[int]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            a = int(row["area_id"])
            b = int(row["neighbor_id"])
            neighbors.setdefault(a, []).append(b)
    return neighbors


# =====================================================================
# Global Moran's I(行標準化重み)
# =====================================================================


def moran_i_from_z(z: Dict[int, float], neighbors: Dict[int, List[int]]) -> float:
    """標準化済みの値 z から Global Moran's I を計算する(行標準化重み)。"""
    denom = sum(v * v for v in z.values())
    if denom == 0:
        return 0.0
    numerator = 0.0
    for area_id, zi in z.items():
        neigh = neighbors.get(area_id, [])
        if not neigh:
            continue
        lag = sum(z[j] for j in neigh) / len(neigh)
        numerator += zi * lag
    return numerator / denom


def global_moran_with_permutation(
    values: Dict[int, float], neighbors: Dict[int, List[int]], permutations: int, rng: random.Random
) -> Tuple[float, float]:
    """Global Moran's I と、値をシャッフルする permutation test による疑似p値を返す。

    疑似p値は「観測値以上のIが偶然何回出るか」の片側検定(正の空間的自己相関の検定)。
    p = (観測以上のI の回数 + 1) / (permutations + 1)
    """
    ids = list(values.keys())
    n = len(ids)
    xbar = sum(values.values()) / n
    z = {i: values[i] - xbar for i in ids}
    observed = moran_i_from_z(z, neighbors)

    zlist = [z[i] for i in ids]
    count_ge = 0
    for _ in range(permutations):
        shuffled = zlist[:]
        rng.shuffle(shuffled)
        z_perm = dict(zip(ids, shuffled))
        i_perm = moran_i_from_z(z_perm, neighbors)
        if i_perm >= observed:
            count_ge += 1
    p_value = (count_ge + 1) / (permutations + 1)
    return observed, p_value


# =====================================================================
# Local Moran's I(LISA)
# =====================================================================


def local_moran(
    values: Dict[int, float], neighbors: Dict[int, List[int]]
) -> Tuple[Dict[int, float], Dict[int, str], Dict[int, float]]:
    """Local Moran's I・4象限分類・z(標準化値)を計算する(spdep の localmoran と同じ定義)。

    z_i = x_i - xbar
    m2 = mean(z_i^2)  (母分散、nで割る)
    I_i = (z_i / m2) * mean_j(z_j)   (j は i の隣、行標準化重み)

    象限分類は z_i と隣の平均(lag_i)の符号の組み合わせで決める。
    """
    ids = list(values.keys())
    n = len(ids)
    xbar = sum(values.values()) / n
    z = {i: values[i] - xbar for i in ids}
    m2 = sum(v * v for v in z.values()) / n

    local_i: Dict[int, float] = {}
    quadrant: Dict[int, str] = {}
    for area_id in ids:
        neigh = neighbors.get(area_id, [])
        if not neigh or m2 == 0:
            local_i[area_id] = 0.0
            quadrant[area_id] = "NA"
            continue
        lag = sum(z[j] for j in neigh) / len(neigh)
        local_i[area_id] = (z[area_id] / m2) * lag
        zi = z[area_id]
        if zi > 0 and lag > 0:
            quadrant[area_id] = "HH"
        elif zi < 0 and lag < 0:
            quadrant[area_id] = "LL"
        elif zi > 0 and lag < 0:
            quadrant[area_id] = "HL"
        elif zi < 0 and lag > 0:
            quadrant[area_id] = "LH"
        else:
            quadrant[area_id] = "NA"
    return local_i, quadrant, z


def local_moran_permutation_p(
    target_ids: List[int],
    values: Dict[int, float],
    neighbors: Dict[int, List[int]],
    permutations: int,
    rng: random.Random,
) -> Dict[int, float]:
    """指定したセルだけについて、条件付き permutation による疑似p値を計算する。

    全342セル分を計算すると出力が膨大かつ低情報量になるため、検証で実際に
    必要になる(truth_labelが付いた)セルに絞って計算する。
    手順(Anselinの条件付きpermutationに準拠): 自分の値 x_i は固定し、
    残り n-1 個の値から隣接数ぶんを無作為抽出して隣の平均(lag)を作り直し、
    局所Iを再計算する。これをpermutations回繰り返し、|観測I|以上が出た割合を
    疑似p値とする(両側)。
    """
    ids = list(values.keys())
    n = len(ids)
    xbar = sum(values.values()) / n
    z = {i: values[i] - xbar for i in ids}
    m2 = sum(v * v for v in z.values()) / n

    result: Dict[int, float] = {}
    for area_id in target_ids:
        neigh = neighbors.get(area_id, [])
        k = len(neigh)
        if k == 0 or m2 == 0:
            result[area_id] = float("nan")
            continue
        zi = z[area_id]
        others = [z[j] for j in ids if j != area_id]
        lag_obs = sum(z[j] for j in neigh) / k
        i_obs = (zi / m2) * lag_obs

        count_ge = 0
        for _ in range(permutations):
            sampled = rng.sample(others, k)
            lag_perm = sum(sampled) / k
            i_perm = (zi / m2) * lag_perm
            if abs(i_perm) >= abs(i_obs):
                count_ge += 1
        result[area_id] = (count_ge + 1) / (permutations + 1)
    return result


# =====================================================================
# Getis-Ord Gi*(自分を含む近傍)
# =====================================================================


def getis_ord_gstar(values: Dict[int, float], neighbors: Dict[int, List[int]]) -> Dict[int, float]:
    """Getis-Ord Gi* の z スコアを計算する(自分を含む二値の重み)。

    Gi*_i = (Σ_j w_ij x_j - xbar * Σ_j w_ij) / (S * sqrt((n*Σw_ij^2 - (Σw_ij)^2) / (n-1)))
    w_ij は 0/1 の二値(自分自身 j=i も w_ii=1 として含める)。
    xbar・S(母標準偏差)は全セルの値から計算する。
    """
    ids = list(values.keys())
    n = len(ids)
    xbar = sum(values.values()) / n
    var = sum(v * v for v in values.values()) / n - xbar * xbar
    s = math.sqrt(max(var, 0.0))

    result: Dict[int, float] = {}
    for area_id in ids:
        incl = neighbors.get(area_id, []) + [area_id]
        w_sum = len(incl)  # 二値重みなので Σw_ij = 隣接数+自分
        x_sum = sum(values[j] for j in incl)
        numerator = x_sum - xbar * w_sum
        denom_inner = (n * w_sum - w_sum * w_sum) / (n - 1)
        denom = s * math.sqrt(max(denom_inner, 0.0))
        result[area_id] = numerator / denom if denom != 0 else 0.0
    return result


# =====================================================================
# --sweep: 「仕込んだ強さとの整合」をコマンド1回で確認する
# =====================================================================


def run_sweep(rows: int, cols: int, seed: int, passes_list: List[int], permutations: int) -> bool:
    """--smooth-passes を passes_list の順に変えて格子データを一時ディレクトリに
    生成し直し、それぞれの Global Moran's I を計算して一覧表示する。

    simulate_spatial_data.generate_lattice() を直接 import して呼び出す
    (自分自身を subprocess で叩く方式ではなく、関数呼び出しにしている)。
    生成先は tempfile.TemporaryDirectory() の一時ディレクトリのみで、
    data/simulated/ のコミット済み CSV には一切触れない。

    Moran's I が passes の増加に対して単調増加していれば True、
    そうでなければ False を返す(呼び出し側で exit code に反映する)。
    """
    print("== --sweep: 平滑化の強さ(--smooth-passes)と Global Moran's I の対応 ==")
    print(f"  対象: rows={rows}, cols={cols}, smooth-passes={passes_list}, seed={seed}")

    results: List[Tuple[int, float, float]] = []
    with tempfile.TemporaryDirectory(prefix="verify_simulation_sweep_") as tmpdir:
        tmp_path = Path(tmpdir)
        for smooth_passes in passes_list:
            # generate_lattice() は rng を消費しながら書き込むので、
            # 各 smooth-passes の比較が公平になるよう毎回シードから作り直す。
            gen_rng = random.Random(seed)
            sim_data.generate_lattice(tmp_path, rows, cols, smooth_passes, gen_rng)

            areas = read_areas(tmp_path / "lattice_areas.csv")
            neighbors = read_neighbors(tmp_path / "lattice_neighbors.csv")
            x = {area_id: a["rate_per_100k"] for area_id, a in areas.items()}

            perm_rng = random.Random(seed)
            moran_i, moran_p = global_moran_with_permutation(x, neighbors, permutations, perm_rng)
            results.append((smooth_passes, moran_i, moran_p))
            print(
                f"    smooth-passes={smooth_passes}: Global Moran's I = {moran_i:.4f}"
                f"(permutation疑似p値={moran_p:.4f}、反復{permutations}回)"
            )

    monotonic = all(results[i][1] < results[i + 1][1] for i in range(len(results) - 1))
    print(f"  判定: {'○ passesの増加に対してIが単調増加(仕込んだ強さと整合)' if monotonic else '■ 単調増加になっていない'}")
    print()
    return monotonic


# =====================================================================
# 検証本体
# =====================================================================


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="合成データの受け入れ条件検査")
    parser.add_argument("--data-dir", type=Path, default=Path("data/simulated"), help="CSVの置き場所")
    parser.add_argument("--seed", type=int, default=20260818, help="permutation test の乱数シード")
    parser.add_argument("--permutations", type=int, default=999, help="permutation test の反復回数")
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="--smooth-passes を変えたときの Global Moran's I の単調性を一時ディレクトリで確認する(既定では実行しない)",
    )
    parser.add_argument(
        "--sweep-passes",
        type=str,
        default="1,2,3",
        help="--sweep で試す smooth-passes のカンマ区切りリスト(既定: 1,2,3、昇順を推奨)",
    )
    parser.add_argument("--sweep-permutations", type=int, default=99, help="--sweep 時の permutation 回数(既定: 99。単調性の判定にp値の精度は不要なので少なめにしている)")
    parser.add_argument("--sweep-rows", type=int, default=18, help="--sweep で生成する格子の行数(既定: 18、simulate_spatial_data.py の既定値と同じ)")
    parser.add_argument("--sweep-cols", type=int, default=19, help="--sweep で生成する格子の列数(既定: 19、simulate_spatial_data.py の既定値と同じ)")
    args = parser.parse_args(argv)

    areas_path = args.data_dir / "lattice_areas.csv"
    neighbors_path = args.data_dir / "lattice_neighbors.csv"
    if not areas_path.exists() or not neighbors_path.exists():
        print(f"エラー: {areas_path} または {neighbors_path} が見つかりません。先に simulate_spatial_data.py を実行してください。")
        return 1

    areas = read_areas(areas_path)
    neighbors = read_neighbors(neighbors_path)
    rng = random.Random(args.seed)

    x = {area_id: a["rate_per_100k"] for area_id, a in areas.items()}

    print(f"■ 対象: {areas_path}({len(areas)}地域) / 変数: rate_per_100k")
    print()

    overall_ok = True

    # --- 条件1: Global Moran's I が有意に正 ---------------------------------
    print("== 条件1: Global Moran's I(空間自己相関の有意性) ==")
    global_i, global_p = global_moran_with_permutation(x, neighbors, args.permutations, rng)
    cond1_ok = (global_i > 0) and (global_p < ALPHA)
    print(f"  Global Moran's I = {global_i:.4f}")
    print(f"  permutation疑似p値(反復{args.permutations}回) = {global_p:.4f}")
    print(f"  判定: {'○ 有意に正' if cond1_ok else '■ 条件を満たさない'}")
    if not args.sweep:
        print("  (注) --smooth-passes を変えたときの単調性(仕込んだ強さとの整合)は、")
        print("       python scripts/verify_simulation.py --sweep で確認できる。")
    print()
    overall_ok = overall_ok and cond1_ok

    if args.sweep:
        sweep_passes = [int(p.strip()) for p in args.sweep_passes.split(",") if p.strip()]
        sweep_ok = run_sweep(args.sweep_rows, args.sweep_cols, args.seed, sweep_passes, args.sweep_permutations)
        overall_ok = overall_ok and sweep_ok

    # --- LISA(全セルに対して計算し、条件2・3で使う) --------------------------
    local_i, quadrant, _z = local_moran(x, neighbors)

    print("== 条件2: HH / LL クラスタが LISA で多数派検出される ==")
    hh_truth_ids = [i for i, a in areas.items() if a["truth_label"] == "HH"]
    ll_truth_ids = [i for i, a in areas.items() if a["truth_label"] == "LL"]

    hh_detected = [i for i in hh_truth_ids if quadrant[i] == "HH"]
    ll_detected = [i for i in ll_truth_ids if quadrant[i] == "LL"]

    cond2_hh_ok = len(hh_truth_ids) > 0 and len(hh_detected) > len(hh_truth_ids) / 2
    cond2_ll_ok = len(ll_truth_ids) > 0 and len(ll_detected) > len(ll_truth_ids) / 2
    cond2_ok = cond2_hh_ok and cond2_ll_ok

    print(f"  truth_label=HH のセル: {len(hh_truth_ids)}件 中 LISA=High-High と判定: {len(hh_detected)}件")
    print(f"  truth_label=LL のセル: {len(ll_truth_ids)}件 中 LISA=Low-Low と判定: {len(ll_detected)}件")
    print(f"  判定: {'○ 両方とも多数派で検出' if cond2_ok else '■ 条件を満たさない'}")
    print()
    overall_ok = overall_ok and cond2_ok

    print("== 条件3: HL(単独高値の空間的アウトライヤー)は LISA=High-Low、Gi*では hot spot でない ==")
    hl_truth_ids = [i for i, a in areas.items() if a["truth_label"] == "HL"]
    gstar = getis_ord_gstar(x, neighbors)

    hl_lisa_ok_ids = [i for i in hl_truth_ids if quadrant[i] == "HL"]
    hl_not_hotspot_ids = [i for i in hl_truth_ids if gstar[i] < HOTSPOT_Z_THRESHOLD]

    cond3_lisa_ok = len(hl_truth_ids) > 0 and len(hl_lisa_ok_ids) > len(hl_truth_ids) / 2
    cond3_gstar_ok = len(hl_truth_ids) > 0 and len(hl_not_hotspot_ids) > len(hl_truth_ids) / 2
    cond3_ok = cond3_lisa_ok and cond3_gstar_ok

    print(f"  truth_label=HL のセル: {len(hl_truth_ids)}件")
    for area_id in hl_truth_ids:
        print(
            f"    area_id={area_id}: rate={areas[area_id]['rate_per_100k']:.1f}"
            f" / LISA象限={quadrant[area_id]}(local I={local_i[area_id]:.3f})"
            f" / Gi* z={gstar[area_id]:.3f}"
            f"(hot spot閾値{HOTSPOT_Z_THRESHOLD}を{'超過' if gstar[area_id] >= HOTSPOT_Z_THRESHOLD else '超過せず'})"
        )
    print(f"  LISAでHigh-Lowと判定: {len(hl_lisa_ok_ids)}/{len(hl_truth_ids)}件")
    print(f"  Gi*でhot spot(z>={HOTSPOT_Z_THRESHOLD})にならなかった: {len(hl_not_hotspot_ids)}/{len(hl_truth_ids)}件")
    print(f"  判定: {'○ 「値が高い」≠「hot spot」が再現された' if cond3_ok else '■ 条件を満たさない'}")
    print()
    overall_ok = overall_ok and cond3_ok

    # --- 参考情報: truth_label付きセルの permutation 疑似p値 ------------------
    print("== 参考: truth_label付きセルの LISA permutation 疑似p値 ==")
    target_ids = hh_truth_ids + ll_truth_ids + hl_truth_ids
    local_p = local_moran_permutation_p(target_ids, x, neighbors, args.permutations, rng)
    sig_count = sum(1 for i in target_ids if local_p[i] < ALPHA)
    print(f"  対象{len(target_ids)}件のうち、疑似p値<{ALPHA}: {sig_count}件")
    print()

    print("=" * 60)
    if overall_ok:
        suffix = "(--sweep による単調性チェック込み)" if args.sweep else ""
        print(f"結果: 受け入れ条件1〜3をすべて満たしました{suffix}。")
    else:
        print("結果: 受け入れ条件を満たさない項目があります。")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
