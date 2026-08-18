# DATA_SOURCES.md

このリポジトリが使う外部データの出典を記録する正本。データ源ごとに見出しを分けている。
後続の issue(境界データ・人口データなど)で新しいデータ源を追加する際は、
下に見出しを追加すること。

隣接リポジトリ <https://github.com/youkiti/visualize-regional-medical-care-for-2040>
の `doc/DATA_SOURCES.md` を参考に、同じ様式(出典名・発行者・URL・取得日・SHA-256・
ライセンス／利用条件・生成コマンド)で記録する。

## 感染症専門医名簿(日本感染症学会)

| 項目 | 内容 |
|---|---|
| 出典名 | 感染症専門医名簿(令和8年7月1日) |
| 発行者 | 一般社団法人 日本感染症学会 |
| URL | <https://www.kansensho.or.jp/uploads/files/senmoni/meibo_260701.pdf> |
| roster_date(名簿の版) | 令和8年7月1日(`2026-07-01`) |
| 取得日(UTC) | 2026-08-18T03:53:30Z |
| バイト数 | 1,038,914 |
| SHA-256 | `c0520d19785824bdf05552b2b0477d6e9204670351882a7e430ec12ad10a19a7` |
| ライセンス／利用条件 | 学会公式サイトで一般公開されているPDF。個人名と所属を含むため、**このリポジトリには生データを含めない**(`data/raw/` は `.gitignore` 済み)。加工過程のコードと、氏名を含まない集計CSVのみを保持する(要件定義書 §4.2) |
| 生成コマンド | `python scripts/fetch_meibo.py`(取得)→ `python scripts/parse_meibo.py`(集計CSV生成) |
| 出力 | `data/processed/specialists_prefecture.csv`(issue #7)、`data/processed/specialists_facility.csv` / `data/processed/specialists_reconciliation.csv`(issue #8)。詳細は [data/processed/README.md](../data/processed/README.md) |

### 既知の注意点

- **PDFは改訂されうる。** 次回取得時にファイルが変わっていたら、SHA-256・バイト数・
  取得日をこの表で更新し、`roster_date` も名簿本体の版に合わせて更新すること。
- **1ページ目の集計(名簿非掲載者含む)と名簿本体(施設ベース)の人数は
  構造的に一致しない。** 都道府県単位でも一致しない箇所が実測で見つかっている。
  詳細は [data/processed/README.md](../data/processed/README.md) の
  「この非対称を必ず読むこと」を参照。
- 冪等な再取得: `scripts/fetch_meibo.py` は `data/raw/` に既存ファイルがあり、
  かつそのSHA-256がメタJSON(`*.meta.json`)に記録済みのSHA-256と**一致するときだけ**
  再ダウンロードをスキップする。存在するだけでは信用しない(途中で切れた
  壊れたファイルが使われ続ける事故を防ぐため)。メタが無い・読めない・
  SHA-256が不一致な場合は再取得する。PDFの改訂を確認したい場合は
  `data/raw/meibo_260701.pdf` を手動で削除してから再実行すること。

## 境界データ・人口データ(issue #4・#5)

二次医療圏・都道府県の境界(queen contiguity 用のジオメトリ)と、その分母となる
人口(総人口・2020年国勢調査)。どちらも隣リポジトリ
[visualize-regional-medical-care-for-2040](https://github.com/youkiti/visualize-regional-medical-care-for-2040)
が既に生成済みの `data/processed/` 配下の成果物を入力にしている
(このリポジトリからは、国土数値情報や e-Stat 等の一次配布元に直接アクセスしていない)。

### 出典・発行者

| 項目 | 内容 |
|---|---|
| 境界の一次出典 | 国土数値情報 医療圏データ 第2.0版(A38-20)、国土交通省 国土数値情報ダウンロードサービス。<https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A38-v2_0.html> |
| 境界のライセンス | 国土数値情報ダウンロードサービス利用規約(オープンデータ)。原典は都道府県の地域保健医療計画等に基づき、**測量法に基づく国土地理院長承認 R 2JHs 664** |
| 人口の一次出典 | 厚生労働省「2040年に向けた地域医療構想」公表資料(令和7年度、R7/001723349.xlsx=②構想区域の病床数等・R7/001722915.xlsx=①都道府県の病床数等)に掲載された2020年国勢調査人口。<https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000080850_00014.html> |
| 取得日 | 2026-08-04(隣リポジトリが一次出典から取得した日。隣リポジトリの `doc/DATA_SOURCES.md` に記録されている取得日をそのまま引き継いでいる) |

### 直接の入力ファイル(隣リポジトリの成果物)とSHA-256

| ファイル | 内容 | SHA-256 |
|---|---|---|
| `data/processed/area_boundaries_R7.geojson` | 二次医療圏境界(339区域、簡略化済み) | `385f9ed78adfbf426ed8aaabde227a7e975051450c1e9a4f38b684a1c53b8a9e` |
| `data/processed/prefecture_boundaries_R7.geojson` | 都道府県境界(47都道府県) | `0ea8bb69414bfe2d3b945adc696d8205bce486e887f5e1b6cc31d50cf7f44779` |
| `data/processed/area_basic.csv` | 区域別 基礎情報(2020年人口・面積、R6+R7で678行) | `bd88040df87384f5fd4843115f70266973847641774a9613f4625dc76c128669` |
| `data/processed/prefecture_basic.csv` | 都道府県別 基礎情報(2020年人口・面積、R6+R7で96行) | `d9fc24a9244dce55a543c32cd9b88db21cae576a57419bc49467437bc777298a` |

これらの成果物自体の加工内容(ディゾルブ・簡略化・帳票のtidy化など)は
隣リポジトリの `doc/DATA_SOURCES.md` に記録されている。

### 「表示専用」の但し書き

隣リポジトリの `doc/DATA_SOURCES.md` は境界GeoJSONについて、
「1km²未満の離島リング除去・Visvalingam加重2%簡略化・座標0.0001度(約11m)丸め」
を行い、**「面積計算等の解析には使わず表示専用とする」**と明記している。
この教材は境界から queen contiguity(隣接関係)を導くことを中心概念とするため、
「表示専用データで隣接を導いてよいか」を `scripts/build_geo.R` が実測で
診断している。診断結果の要約は [data/geo/README.md](../data/geo/README.md)、
全文は `data/geo/adjacency_diagnostics.md` を参照。結論(2026-08-18時点):
座標の0.0001度丸めは queen contiguity の判定に影響していない(snap感度
テストで確認済み)。

### このリポジトリでの設計判断(逸脱とその理由)

issue #4 の本文とは異なる判断を3点行っている。理由は以下のとおり
(コード上は `scripts/build_geo.R` の docstring にも同じ内容を記載):

1. **主ジオメトリを `iryoken2_A38-20.geojson`(335圏、生のA38属性)ではなく
   `area_boundaries_R7.geojson`(339区域)にした。** 属性が `area_code`/
   `pref_code` として既に整理されており、人口CSV(`area_basic.csv`、339区域)
   とそのまま `area_code` で結合できるため。335圏版は令和2年度時点の生の
   A38属性のままで、結合キーを作り直す必要がある。339 と 335 の差は
   三重県の構想区域細分化に由来する(隣リポの `tools/build_area_boundaries.py`
   docstring 参照)。
2. **issue #4 が求める「目標1MB級」への追加簡略化(`st_simplify()` 等)を
   行っていない。** この教材の中心概念は queen contiguity(隣接の定義)
   そのものであり、追加の簡略化は隣接関係を変えうる。入力は既に約4.5MBで
   GitHubの100MB制限に対して十分小さく、削る利益より隣接を壊すリスクの
   ほうが大きいと判断した。
3. **A38の生zip(1.13GB)をダウンロードしていない。** 隣リポジトリの取得
   スクリプトは Selenium + Chrome で公式サイトのアンケートモーダルを辿る
   作りで重く壊れやすいため、今回は隣リポジトリの成果物(既に加工済みの
   GeoJSON/CSV)を起点にした。

### 生成コマンド・出力

| 生成コマンド | 出力 |
|---|---|
| `Rscript scripts/build_geo.R` | `data/geo/iryoken2.geojson`・`data/geo/prefecture.geojson`・`data/geo/adjacency_iryoken2.csv`・`data/geo/adjacency_diagnostics.md`(詳細は [data/geo/README.md](../data/geo/README.md)) |
| `python scripts/build_population.py` | `data/processed/population_iryoken2.csv`・`data/processed/population_prefecture.csv`(詳細は [data/processed/README.md](../data/processed/README.md)) |

### 未着手

年齢階級別人口・65歳以上人口は e-Stat からの取得が別途必要で未着手
(`area_basic.csv` には総人口しか無い)。

なお隣リポジトリの `iryoken2_A38-20.geojson`(335圏、生のA38属性)は
`A38b_007`〜`A38b_011` という人口らしき数値属性を持つ。年齢階級別人口を
含む可能性があるが、**各属性が何を指すかは国土数値情報の仕様書で未確認**
のため今回は使っていない。年齢階級別人口が必要になった時点で、仕様書で
確認したうえで e-Stat と比較検討する。
