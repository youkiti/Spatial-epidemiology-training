# data/simulated/

実データ(感染症専門医名簿PDF・二次医療圏の境界データ)が無くても教材全体が
走るようにするための合成データ。`scripts/simulate_spatial_data.py` の出力を
そのままコミットしている(個人情報を含まない合成データなのでコミット対象。
`.gitignore` が除外しているのは `data/raw/` と `data/interim/` のみ)。

再生成するには:

```bash
python scripts/simulate_spatial_data.py --out data/simulated
```

既定のシード(`--seed 20260818`)であれば、何度実行してもバイト単位で同一の
CSVが生成される(`random.Random(seed)` の専用インスタンスのみを使い、
グローバルな `random` モジュールの状態には依存しない)。

検証は `scripts/verify_simulation.py`(標準ライブラリのみ)と、その再確認用の
`scripts/verify_simulation.R`(spdep使用。**この開発環境にはRが無いため未実行**)
で行う。

## ファイル一覧

### (a) toy10 — 概念導入用の架空10市町村データ

- `toy10_areas.csv`: `area_id, area_name, population, cases, rate_per_100k, x, y`
  - 10地域(A市〜J市、明らかに架空と分かる名前)。2行×5列の格子(x: 列0〜4, y: 行0〜1)。
  - 乱数に依存しない固定値。**章1で「患者数(count)の地図」と「率(rate)の地図」で
    順位が入れ替わる例**として設計している: A市は人口18万・患者180人と患者数トップ
    だが人口10万対100(中位の率)。B市は人口2.5万・患者75人しかいないが人口10万対300で
    率としては最も高い。「数の地図」だけを見るとB市の深刻さが見えない、という
    落とし穴(要件定義書 §1.3 原則6)をこのデータだけで再現できる。
- `toy10_neighbors.csv`: `area_id, neighbor_id`
  - rook隣接(上下左右のみ、斜めは含まない)。両方向を書き出している
    (例: `1,2` と `2,1` の両方が存在する)。

### (b) lattice — 二次医療圏スケールの合成データ

- `lattice_areas.csv`: `area_id, row, col, population, expected_cases, observed_cases, rate_per_100k, sir, truth_label`
  - 既定18行×19列=342地域(日本の二次医療圏数のオーダー)。
  - `population`: 対数正規分布でばらつかせた人口。17区画に1つの割合で
    意図的にごく小さい人口(500〜3,000人)の地域を混ぜており、
    小地域の少数例による率の不安定さ(章6の落とし穴)を再現できる。
  - `expected_cases`: 期待数(人口 / 100,000 × 基準率)。
  - `observed_cases`: 期待数 × 相対リスク を平均とする自前実装のPoisson乱数
    (numpyが無い環境向け。小さい平均はKnuthの乗算法、大きい平均は正規近似に
    自動で切り替える。`simulate_spatial_data.py` の `poisson_random()` を参照)。
  - `rate_per_100k` / `sir`: それぞれ `observed_cases` から計算した人口10万対率と
    標準化発生比(観察数/期待数)。
  - `truth_label`: 埋め込んだ「正解」パターン。
    - `HH`: High-Highクラスタ(3×3、周囲も高いことを保証するため実際には
      5×5の範囲で相対リスクを上げている。中心の3×3のみラベル付け)。
    - `LL`: Low-Lowクラスタ(同様に5×5で下げ、中心3×3のみラベル付け)。
    - `HL`: 単独高値の空間的アウトライヤー(1セルだけ相対リスク10倍、
      その8近傍は相対リスクを大きく下げてあり、周囲が低いことを保証している。
      HH・LLクラスタから十分離れた位置に配置)。
    - `background`: 上記以外。平滑化した潜在変数(`--smooth-passes` 回の
      近傍移動平均)から作った、緩やかな空間自己相関を持つ相対リスク。
  - **空間自己相関の強さは `--smooth-passes` で仕込んである。** 回数を増やすほど
    Global Moran's I が大きくなる。`python scripts/verify_simulation.py --sweep` で
    smooth-passes=1/2/3 のデータを一時ディレクトリに生成し直し、単調増加していることを
    コマンド1回で自動検証できる(実測値: passes 1/2/3 → I = 0.2870 / 0.3474 / 0.3921。
    seed=20260818、rows=18・cols=19の既定値の場合)。
- `lattice_neighbors.csv`: `area_id, neighbor_id`
  - queen隣接(縦・横・斜め)。格子から機械的に導出したもので、実際の
    ポリゴンから作った隣接関係ではない(下記「実ポリゴンとの関係」参照)。
    両方向を書き出している。

## R から読む方法

```r
areas <- read.csv("data/simulated/lattice_areas.csv")
nb_edges <- read.csv("data/simulated/lattice_neighbors.csv")

n <- nrow(areas)
areas <- areas[order(areas$area_id), ]
id_to_index <- setNames(seq_len(n), areas$area_id)

adj_mat <- matrix(0L, n, n)
for (i in seq_len(nrow(nb_edges))) {
  a <- id_to_index[[as.character(nb_edges$area_id[i])]]
  b <- id_to_index[[as.character(nb_edges$neighbor_id[i])]]
  adj_mat[a, b] <- 1L
}

library(spdep)
listw <- mat2listw(adj_mat, style = "W")  # 行標準化
moran.test(areas$rate_per_100k, listw)
```

`scripts/verify_simulation.R` に同じ手順をまとめたスクリプトがある
(spdepの`moran.test` / `localmoran` / `localG` を使う。**この開発環境には
Rが入っておらず未実行・動作未確認**。R環境で最初に使う際は必ず一度
動かして確認すること)。

## 実ポリゴンとの関係(issue #4 が完了したら)

`lattice_neighbors.csv` の隣接関係は、規則格子(lattice)上で機械的に定義した
queen隣接であり、**実際の二次医療圏ポリゴンの隣接関係ではない**。
国土数値情報の医療圏データ(A38)が整備され、queen contiguityが実ポリゴンから
計算できるようになったら(issue #4)、本データセットの `lattice_*.csv` は
実ポリゴンベースのデータに差し替える想定。それまでの間、章2〜4の
「空間重み行列を先に決める」「Global/Local Moran's I」「Gi*」の実演・検証は
本データセットで代替する。

`toy10` は概念導入用の最小データという位置づけのため、実ポリゴンが入っても
差し替える必要はない(架空データを使い続ける設計。要件定義書 §4.1)。

## 生成器・検証器の再実行例

```bash
# 生成(既定パラメータ)
python scripts/simulate_spatial_data.py --out data/simulated

# 検証(受け入れ条件1〜3を出力・判定)
python scripts/verify_simulation.py --data-dir data/simulated

# 空間自己相関の強さ(--smooth-passes)と Global Moran's I の対応(単調性)を
# コマンド1回で確認する。一時ディレクトリに生成するだけで data/simulated/ は書き換えない。
python scripts/verify_simulation.py --sweep
python scripts/verify_simulation.py --sweep --sweep-passes 1,2,3,5   # 試す passes を変える場合
```
