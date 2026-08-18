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

### 岡山↔香川の隣接(3301↔3706)の一次資料での裏取り

`data/geo/adjacency_diagnostics.md` が検出した四国↔本州を繋ぐ唯一のエッジ
`3301`(岡山県 県南東部)↔`3706`(香川県 東部)は、**実在の地理に由来する**ことを
一次資料で確認済み(2026-08-18)。瀬戸内海の**井島(いしま、2.63km²)**は
1つの島の陸地が玉野市(岡山県、県南東部圏)と直島町(香川県、東部圏)に
分かれて属しており、かつ**両県の境界の一部が未定**である。つまり岡山県と
香川県はこの島上で陸続きに接しており、境界GeoJSONの2ポリゴンが頂点を
共有するのは簡略化・丸めの副作用ではない。

| 項目 | 内容 |
|---|---|
| 出典名 | 令和3年 全国都道府県市区町村別面積調(1月1日時点)(国土地理院技術資料 E2-No.71) |
| 発行者 | 国土交通省 国土地理院 |
| URL | <https://www.gsi.go.jp/KOKUJYOHO/MENCHO/backnumber/GSI-menseki20210101>(PDFが直接返る) |
| 確認日 | 2026-08-18 |
| バイト数 | 1,559,537 |
| SHA-256 | `96ae928c27729b32a206b6864ecf1d30492fec1d2d191bbce6c0cee900de42e7` |

該当箇所(ページ番号はPDF機械抽出のページ位置):

- PDF 9ページ「都道府県にまたがる境界未定地域」に岡山県玉野市(*103.58)と
  香川県香川郡直島町(*14.22)が挙がっている(* は参考値の意)
- PDF 62・67ページの注記「玉野市及び香川県香川郡直島町は、境界の一部が
  未定のため、(それぞれについて)参考値を示した」
- PDF 88ページの島面積表[岡山県]に
  「井島 いしま 2.63 境界未定(玉野市[岡山]・直島町[香川])」

この島は岡山側では「石島」、香川側では「井島」と表記されるが、面積調では
岡山県の島として「井島」の名で一括掲載されている。教材の章5で
「隣とは何か」の実例としてこのエッジを使う際は、この出典を引くこと。

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

## 施設の座標データ(issue #9)

専門医名簿の施設名に座標を与え、二次医療圏へ割り付けるための参照点テーブル
(`data/interim/facility_reference.csv`)を作る2つのデータ源。

### 出典・発行者

| 項目 | 内容 |
|---|---|
| 医療情報ネットの出典 | 医療機能情報提供制度(医療情報ネット)。厚生労働省。<https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryou/newpage_43373.html>。公表時点 2025-06-01 |
| P04の出典 | 国土数値情報「医療機関データ」第3.0版(全国)、令和2年度。国土交通省。データページ: <https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P04-v3_0.html>。zip直URL: <https://nlftp.mlit.go.jp/ksj/gml/data/P04/P04-20/P04-20_GML.zip> |
| 取得日(このリポジトリでの取得) | 2026-08-18 |

**いずれも一次配布元に直接アクセスしていない。** 隣リポジトリ
[visualize-regional-medical-care-for-2040](https://github.com/youkiti/visualize-regional-medical-care-for-2040)
が既に取得・SHA-256記録済みのファイルをそのまま複製して使っている(上の
「境界データ・人口データ」節と同じ扱い)。生データは `data/raw/`
(`.gitignore` 済み)に置く。

### 直接の入力ファイルとSHA-256

| ファイル | 内容 | SHA-256 |
|---|---|---|
| `01-1_hospital_facility_info_20250601.zip` | 医療情報ネット 病院票 | `bc1ee5f4614a3cd0d66b0ce1d736b857426feb511ca3163925bd7285ba8bffd1` |
| `02-1_clinic_facility_info_20250601.zip` | 医療情報ネット 診療所票 | `366679df93a61c6eded7bcf4ad680c805461a747242560ff38f535c237265575` |
| `001306376.xlsx` | 医療情報ネットの列定義書 | `8715356b200196df9d9a226ad58a1290c667891bf9241af6f1c0ab2f14aefb8e` |
| `P04-20_GML.zip` | 国土数値情報 医療機関データ(点データ) | `24d49390c0760416223784ab2dbb6ad852dbda9a07a5d3b769fba91be91c9732` |

### ライセンス／利用条件

医療情報ネットは公表制度に基づく行政公開情報、国土数値情報はダウンロード
サービス利用規約(オープンデータ)に基づく。個人名を含まない施設情報のみで、
このリポジトリでの取り扱い方針(要件定義書 §4.2)に抵触しない。

### 生成コマンド

```bash
python scripts/build_facility_reference.py
python scripts/link_facilities.py
python scripts/verify_facility_linkage.py
```

出力は `data/interim/facility_reference.csv`(`.gitignore` 済み)、
`data/processed/facility_geo_audit.csv`、`data/processed/specialists_iryoken2.csv`。
詳細は [data/processed/README.md](../data/processed/README.md)。
`data/curated/facility_crosswalk.csv` の位置づけは
[data/curated/README.md](../data/curated/README.md) を参照。

### 既知の注意点

- **医療情報ネットの一括公開ファイルは都道府県ごとに網羅性が大きく違う。**
  実測で沖縄県は病院30件・診療所91件、鳥取県は病院31件・診療所134件、
  京都府は診療所626件しか収録されていない。`島根県立中央病院`・
  `京都市立病院`・`自治医科大学附属病院`・`国立病院機構東京医療センター`
  はいずれも収録されておらず、P04 にのみ存在する。**だから P04 を併用する
  ことが必須**で、`build_facility_reference.py` は P04 を既定で読む。
- **医療情報ネットの一括公開ファイルには公表時点が複数ある**
  (2024-08-01 / 2024-12-01 / 2025-06-01 / 2025-12-01 / 2026-06-01)。
  このリポジトリが 2025-06-01 版を使っているのは、隣リポジトリの選択を
  そのまま引き継いでいるため(隣リポジトリは「原典の報告時点より後の移転を
  拾うと、原典が誤っているのか原典の後に施設が動いたのかを分離できない」
  という理由で 2025-06-01 を採用している)。名簿(2026-07-01)との間には
  **13か月の開差**があり、この間の改称・移転・閉院は名簿側と一致しなくなる。
- P04 は令和2年度で名簿(2026-07-01)と6年の開差がある。改称・移転・閉院は
  一致しなくなる。
- 医療情報ネットの座標欠測センチネルは空欄ではなく `0.0`/`0.0`(実測4,456件・
  5.4%)。空欄判定では検出できず、範囲判定が要る。
- **原典の座標そのものが壊れている行がある。** 実測例: 山形県鶴岡市の
  診療所の経度が `139.0`(丸められている)、鹿児島県瀬戸内町の施設が
  `129.2/28.1`、熊本県上益城郡の施設が `123.393744/41.769863`
  (中国遼寧省付近)。
- **同一施設が医療情報ネットとP04の両方に載っていて、二次医療圏が
  食い違うことがある。** 実測: `厚生労働省霞が関診療所` は両者とも住所が
  「千代田区霞が関1-2-2 中央合同庁舎第5号館3階」で同一なのに、座標は
  P04 が実際の霞が関から約0.2km、医療情報ネットが約12.4km離れており、
  二次医療圏が 1301(区中央部)と 1304(区西部)に分かれる
  (`data/curated/facility_crosswalk.csv` の当該行のnote参照。医療情報ネット
  側のジオコーディング誤りと判断した)。`link_facilities.py` は、この
  食い違いを**黙って片方に寄せず、エラーで落とす**(`resolved_facility_name`
  から医療圏コードを導出するとき、県内に複数の医療圏コードが候補として
  出たら一意に決まらないとして落とす設計。`_resolve_iryoken2_code_from_name`
  参照)。決着は人が `data/curated/facility_crosswalk.csv` に
  `iryoken2_code` を直接書いて行う。**これは「2つの公表物が食い違ったときは
  推測しない」という原則の実装であり**、隣リポジトリ
  `doc/DECISION_FACILITY_COORDINATES.md` の決定3と同じ考え方。
