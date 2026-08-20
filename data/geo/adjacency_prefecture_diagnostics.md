# 都道府県隣接データ診断(build_adjacency_prefecture.R)

- 実行日(ローカル): 2026-08-20
- 入力: data/geo/prefecture.geojson(このリポジトリにコミット済み。scripts/build_geo.R の既存生成物)

## 1. フィーチャ数

- 都道府県: 47 件(期待値 47)

## 2. ジオメトリ妥当性(st_is_valid)

- 都道府県: 不正なジオメトリ 0 件 / 47 件

## 3. 孤立都道府県(隣接0件)の列挙

- 孤立都道府県: 2 件
  - 北海道(01)
  - 沖縄県(47)
- 陸上で他都道府県と接していない(海で隔てられている)都道府県であれば妥当。

## 4. snap 感度テスト

- snap=0(頂点完全一致のみ): 有向隣接ペア 174 件
- snap=0.0001(座標丸め幅と同程度、約11m): 有向隣接ペア 174 件
- snap=0.001(座標丸め幅の10倍、約111m): 有向隣接ペア 174 件
- snap=0 と snap=0.0001 の集合差: 0 件
- snap=0.0001 と snap=0.001 の集合差: 0 件
- snap=0 と snap=0.001 の集合差: 0 件

- 結論: snap=0とsnap=0.0001で隣接ペアの集合は完全に一致した(174件、集合差0件)。
  座標丸めによって生じた隙間で隣接が失われている形跡は無い。

- 本採用(adjacency_prefecture.csv): snap=0(spdepの既定相当。snap=0.0001と隣接ペアの集合差が無かったため、人為的な結合を一切入れない値を採用)

## 5. 隣接数の要約

- 平均: 3.702
- 最小: 0
- 最大: 8

## 6. 連結成分

- 都道府県単位の空間重み行列(隣接グラフ)が連結しているかどうかは、
  ハンズオン③(MAUP)で都道府県単位のGlobal Moran's Iを計算する際に
  直接効く論点のため、実測して記録する。
- 連結成分の個数: 4
- サイズ(降順)と代表都道府県:
  - 成分1: 38都道府県(青森県、岩手県、宮城県、秋田県、山形県、福島県 ほか32件)
  - 成分2: 7都道府県(福岡県、佐賀県、長崎県、熊本県、大分県、宮崎県 ほか1件)
  - 成分3: 1都道府県(孤立: 北海道)
  - 成分4: 1都道府県(孤立: 沖縄県)

- サイズ1の成分(孤立都道府県)は2件で、診断3で列挙した孤立都道府県2件と一致した。

## 付録: poly2nb 子プロセスの実行ログ

Spherical geometry (s2) switched off
although coordinates are longitude/latitude, st_intersects assumes that they
are planar
poly2nb(snap=snap0): 有向隣接ペア 174 件
although coordinates are longitude/latitude, st_intersects assumes that they
are planar
poly2nb(snap=snap1): 有向隣接ペア 174 件
although coordinates are longitude/latitude, st_intersects assumes that they
are planar
poly2nb(snap=snap10): 有向隣接ペア 174 件
警告メッセージ:
1: poly2nb(pref_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  some observations have no neighbours;
if this seems unexpected, try increasing the snap argument.
2: poly2nb(pref_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  neighbour object has 4 sub-graphs;
if this sub-graph count seems unexpected, try increasing the snap argument.
3: poly2nb(pref_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  some observations have no neighbours;
if this seems unexpected, try increasing the snap argument.
4: poly2nb(pref_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  neighbour object has 4 sub-graphs;
if this sub-graph count seems unexpected, try increasing the snap argument.
5: poly2nb(pref_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  some observations have no neighbours;
if this seems unexpected, try increasing the snap argument.
6: poly2nb(pref_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  neighbour object has 4 sub-graphs;
if this sub-graph count seems unexpected, try increasing the snap argument.
child: 完了
(子プロセスの終了コード: 255 — 計算後のプロセス終了時クラッシュにより非ゼロになりうる。完了マーカーの有無で成否を判定する。)

