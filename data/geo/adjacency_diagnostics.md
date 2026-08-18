# 境界データ診断(build_geo.R)

- 実行日(ローカル): 2026-08-18
- 二次医療圏の入力: C:/Users/youki/codes/visualize-regional-medical-care-for-2040/data/processed/area_boundaries_R7.geojson
- 都道府県の入力: C:/Users/youki/codes/visualize-regional-medical-care-for-2040/data/processed/prefecture_boundaries_R7.geojson

## 1. フィーチャ数

- 二次医療圏: 339 件(期待値 339)
- 都道府県: 47 件(期待値 47)

## 2. ジオメトリ妥当性(st_is_valid)

- 二次医療圏: 不正なジオメトリ 7 件 / 339 件
  - 修復対象(二次医療圏): 県南(0703), 常陸太田・ひたちなか(0803), 新宮(3007), 岩国(3501), 周南(3503), 宇和島(3806), 宮古(4704)
  - st_make_valid() 後の不正件数: 0 件
- 都道府県: 不正なジオメトリ 0 件 / 47 件

## 3. 孤立区域(隣接0件)の列挙

- 孤立区域: 14 件
  - 島しょ(1313, 東京都)
  - 佐渡(1507, 新潟県)
  - 淡路(2810, 兵庫県)
  - 隠岐(3207, 島根県)
  - 小豆(3702, 香川県)
  - 五島(4206, 長崎県)
  - 上五島(4207, 長崎県)
  - 壱岐(4208, 長崎県)
  - 対馬(4209, 長崎県)
  - 天草(4311, 熊本県)
  - 熊毛(4611, 鹿児島県)
  - 奄美(4612, 鹿児島県)
  - 宮古(4704, 沖縄県)
  - 八重山(4705, 沖縄県)
- 離島のみで構成される医療圏(隠岐・対馬・五島等)であれば妥当。内陸の区域が
  含まれる場合は簡略化・座標丸めの副作用を疑うこと。

## 4. snap 感度テスト

- snap=0(頂点完全一致のみ): 有向隣接ペア 1558 件
- snap=0.0001(座標丸め幅と同程度、約11m): 有向隣接ペア 1558 件
- snap=0.001(座標丸め幅の10倍、約111m): 有向隣接ペア 1562 件
- snap=0 と snap=0.0001 の集合差: 0 件
- snap=0.0001 と snap=0.001 の集合差: 4 件
- snap=0 と snap=0.001 の集合差: 4 件

- 結論: 座標が0.0001度(約11m)に丸められているにもかかわらず、snap=0とsnap=0.0001で
  隣接ペアの集合は完全に一致した(1558件、集合差0件)。丸めによって生じた隙間で
  隣接が失われている形跡は無い。これは mapshaper の簡略化が共有アークを
  1度だけ処理する(トポロジ保存)ことと整合する。
  snapを丸め幅の10倍(0.001度、約111m)まで緩めると4件増えるが、これは
  本来隣接していないポリゴンを許容幅で結合してしまう過剰結合であり、
  丸めの影響を示すものではない(対照条件で差が出たことを理由に本採用の
  snapを緩めてはいけない)。

- 本採用(adjacency_iryoken2.csv): snap=0(spdepの既定相当。snap=0.0001と隣接ペアの集合差が無かったため、人為的な結合を一切入れない値を採用)

## 5. 隣接数の要約

- 平均: 4.596
- 最小: 0
- 最大: 11

## 6. 連結成分

- 空間重み行列(隣接グラフ)が連結しているかどうかは、章5(空間回帰・
  CAR/BYM)で必ず問題になる論点のため、実測して記録する。
- 連結成分の個数: 18
- サイズ(降順)と代表都道府県:
  - 成分1: 250区域(代表: 青森県、岩手県、宮城県、秋田県、山形県、福島県 ほか32県)
  - 成分2: 51区域(代表: 福岡県、佐賀県、長崎県、熊本県、大分県、宮崎県 ほか1県)
  - 成分3: 21区域(代表: 北海道)
  - 成分4: 3区域(代表: 沖縄県)
  - 成分5: 1区域(孤立: 島しょ, 東京都)
  - 成分6: 1区域(孤立: 佐渡, 新潟県)
  - 成分7: 1区域(孤立: 淡路, 兵庫県)
  - 成分8: 1区域(孤立: 隠岐, 島根県)
  - 成分9: 1区域(孤立: 小豆, 香川県)
  - 成分10: 1区域(孤立: 五島, 長崎県)
  - 成分11: 1区域(孤立: 上五島, 長崎県)
  - 成分12: 1区域(孤立: 壱岐, 長崎県)
  - 成分13: 1区域(孤立: 対馬, 長崎県)
  - 成分14: 1区域(孤立: 天草, 熊本県)
  - 成分15: 1区域(孤立: 熊毛, 鹿児島県)
  - 成分16: 1区域(孤立: 奄美, 鹿児島県)
  - 成分17: 1区域(孤立: 宮古, 沖縄県)
  - 成分18: 1区域(孤立: 八重山, 沖縄県)

- サイズ1の成分(孤立区域)は14件で、診断3で列挙した孤立区域14件と一致した。

## 7. ブリッジ(この1本で連結が決まるエッジ)

- ブリッジとは、除去すると連結成分の数が増えるエッジのこと。空間重み行列
  (隣接グラフ)において、その1本の隣接判定だけで全体の連結構造が決まる
  急所であり、「隣とは何か」の判断が結果を大きく変える具体例になる。
- ブリッジ総数: 9 件(無向グラフとして判定)
- うち都道府県をまたぐもの: 1 件
- うち同一都道府県内: 8 件(詳細は割愛)

都道府県をまたぐブリッジの一覧:

  - 県南東部(3301, 岡山県) <-> 東部(3706, 香川県)

- 3301<->3706(岡山県 県南東部 <-> 香川県 東部)はブリッジとして検出された。
  このエッジを除くと、3301側は235区域、3706側は15区域に分かれる(実測)。
  この1本が両側の連結・非連結を決めている(診断6参照)。

## 付録: poly2nb 子プロセスの実行ログ

Spherical geometry (s2) switched off
although coordinates are longitude/latitude, st_intersects assumes that they
are planar
poly2nb(snap=snap0): 有向隣接ペア 1558 件
although coordinates are longitude/latitude, st_intersects assumes that they
are planar
poly2nb(snap=snap1): 有向隣接ペア 1558 件
although coordinates are longitude/latitude, st_intersects assumes that they
are planar
poly2nb(snap=snap10): 有向隣接ペア 1562 件
警告メッセージ:
1: poly2nb(area_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  some observations have no neighbours;
if this seems unexpected, try increasing the snap argument.
2: poly2nb(area_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  neighbour object has 18 sub-graphs;
if this sub-graph count seems unexpected, try increasing the snap argument.
3: poly2nb(area_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  some observations have no neighbours;
if this seems unexpected, try increasing the snap argument.
4: poly2nb(area_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  neighbour object has 18 sub-graphs;
if this sub-graph count seems unexpected, try increasing the snap argument.
5: poly2nb(area_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  some observations have no neighbours;
if this seems unexpected, try increasing the snap argument.
6: poly2nb(area_sf, queen = TRUE, snap = snap_values[[nm]]) で:
  neighbour object has 18 sub-graphs;
if this sub-graph count seems unexpected, try increasing the snap argument.
child: 完了
(子プロセスの終了コード: 255 — 上の docstring のとおり、計算後のプロセス終了時クラッシュにより非ゼロになりうる。完了マーカーの有無で成否を判定する。)

