# data/processed/

感染症専門医名簿PDF(`data/raw/meibo_260701.pdf`)から抽出した、氏名を含まない
集計CSV。`scripts/parse_meibo.py` の出力をそのままコミットしている
(個人名を含まないためコミット対象。氏名を含む中間ファイルは `data/interim/`
にあり、`.gitignore` で除外している)。

再生成するには:

```bash
python scripts/fetch_meibo.py
python scripts/parse_meibo.py
```

出典・取得日・SHA-256などの来歴は [documents/DATA_SOURCES.md](../../documents/DATA_SOURCES.md) にある。

## この非対称を必ず読むこと

1ページ目(`specialists_prefecture.csv` の元)の集計は「名簿非掲載者含む」ため、
名簿本体(`specialists_facility.csv` の元、2ページ目以降)から数えた人数と
**構造的に一致しない**。都道府県レベルの分子には1ページ目の公式集計を使い、
二次医療圏レベルには名簿本体(施設ベース)を使うしかないので、
二次医療圏レベルの分子は都道府県レベルより**過小カウントになる**
(要件定義書・issue #8 の想定どおり)。

**さらに実測で判明した点**: この過小カウントは常に非負とは限らない。
2026-08-18時点の実測では、47都道府県のうち9都道府県
(青森県・栃木県・千葉県・神奈川県・新潟県・石川県・京都府・兵庫県・山口県)で
名簿本体から数えた人数が1ページ目の集計を**上回っている**
(`specialists_reconciliation.csv` の `diff` が負)。全国合計では
名簿本体1,894名 < 1ページ目1,903名(合計としては非負)だが、
都道府県単位では符号が反転する箇所がある。この9都道府県について
抽出コード側の重複カウント・取りこぼしが無いか目視で確認したが
(氏名リストを1件ずつ数え、`scripts/parse_meibo.py` の出力と一致することを確認)、
再現する不一致であり抽出バグとは考えにくい。

**抽出バグではないと判断できる、より強い根拠**: 都道府県マーカーの
forward-fillがページ境界でズレていれば、次の都道府県ブロックは五十音の
途中から始まるはずである。名簿本体は都道府県ブロックごとに施設名の
かな順で並んでいるため、実際に確かめると、東京都ブロックは東京の施設
「順天堂大学医学部附属練馬病院」で終わり、神奈川県ブロックは
五十音の**先頭**「あざがみクリニック」から始まっていた。つまり境界は
正しく、東京 +4・神奈川 −4 という対称的なズレも境界ズレではなく
分類基準の違いで説明がつく形をしている。1ページ目の集計基準
(会員登録上の都道府県)と名簿本体の分類基準(所属施設の所在都道府県)が
一致しない実務上の理由がある可能性があるが、**この対応関係自体は依然として
未確認の仮説**である。

`scripts/parse_meibo.py` の検算は、この非対称を踏まえて2段階に分けている:

- **ハード検算(失敗で終了コード1)**: 全国合計の `diff` が0以上であること
  (1ページ目が「名簿非掲載者含む」ことから構造的に保証される)。
- **警告(終了コードには影響しない)**: 都道府県単位で `diff` が負になる件。
  該当都道府県と実測値を stdout に列挙し、`specialists_reconciliation.csv`
  の `note` 列に `body_exceeds_page1` の印を付ける。都道府県単位の符号は
  「1ページ目の分類基準」と「施設所在地」が一致する保証が無い以上、
  非負であることまでは保証されないため。

## ファイル一覧

### `specialists_prefecture.csv`(issue #7)

列: `pref_code, pref_name, n_certified, source, retrieved_on, roster_date`

- 1ページ目「都道府県別認定者数(名簿非掲載者含む)」の表をそのまま集計した48行
  (47都道府県+「海外」)。合計1,903名。
- `pref_code`: JIS X 0401 の2桁コード(`01`〜`47`)。**「海外」は `99`**。
  地図対象を機械的に除外するには `pref_code` が `01`〜`47` の範囲かどうかで
  判定できる(PDF上の都道府県の並び順は地方ブロック単位でJISコード順ではないため、
  コードは名前引きの固定表 `scripts/parse_meibo.py` の `PREF_CODES` から採番している)。
- `source`: 取得元URL。`retrieved_on`: PDF取得日(UTC日付、`fetch_meibo.py` の
  メタ情報から)。`roster_date`: 名簿の版(令和8年7月1日 = `2026-07-01`)。

### `specialists_facility.csv`(issue #8)

列: `pref_name, facility_name, n_specialists`

- 名簿本体(施設名の行→直下の氏名の行)を施設単位で集計。1,059行
  (`pref_name, facility_name` の組でユニーク。施設名だけでユニークにすると1,039件で、
  「施設掲載なし」のように複数の都道府県で同名が繰り返される施設があるため
  組の件数の方が多い)。
- 名簿本体から抽出した氏名の総数は1,894名(`n_specialists` の全国合計と一致する
  ことを `scripts/parse_meibo.py` の検算で確認している)。
- **氏名は一切含まない**(集計値のみ)。ただし氏名が無いことと再識別リスクが
  無いことは別問題である。公開範囲の考え方と利用上の注意は、本ファイル末尾の
  「施設単位データの公開範囲と利用上の注意」節を参照。

### `specialists_reconciliation.csv`

列: `pref_code, pref_name, n_certified_page1, n_roster_body, diff, note`

- 都道府県ごとに、1ページ目の公式集計(`n_certified_page1`)と名簿本体から
  数えた人数(`n_roster_body`)を並べた監査表。`diff = n_certified_page1 - n_roster_body`。
- 全国合計の `diff` は **9**(1,903 − 1,894)。ただし上記のとおり都道府県単位では
  負になる箇所がある。
- `note`: `diff` が負の行にのみ `body_exceeds_page1` が入る(それ以外は空文字)。
  機械可読な印であり、CSVだけを読む後続処理が異常に気づけるようにするためのもの
  (stdout の警告だけでは後続処理から見えないため)。

## data/interim/ との関係

氏名を含む中間ファイル `data/interim/specialists_names.csv`
(`pref_name, facility_name, person_name`)は `.gitignore` で除外されており、
このリポジトリには入らない。上記の不一致(`diff` が負の都道府県)を再調査する際は、
`python scripts/parse_meibo.py` を再実行してローカルに生成すること。

## 人口(分母)データ(issue #5)

隣リポジトリ(visualize-regional-medical-care-for-2040)が既に厚生労働省
「2040年に向けた地域医療構想」の公表資料から抽出済みの `area_basic.csv`・
`prefecture_basic.csv` を入力に、`scripts/build_population.py` の出力を
そのままコミットしている。出典・ライセンス・取得日などの来歴は
[documents/DATA_SOURCES.md](../../documents/DATA_SOURCES.md) の
「境界データ・人口データ」節を参照。

再生成するには:

```bash
python scripts/build_population.py
```

(`data/geo/iryoken2.geojson` との area_code 突合を行うため、先に
`Rscript scripts/build_geo.R` を実行しておくこと。)

### `population_iryoken2.csv`

列: `area_code, area_name, pref_code, pref_name, population_2020, source, retrieved_on`
に加え、issue #28(下記「年齢階級別人口」節)で年齢列
(`pop_0_4`〜`pop_100plus`, `pop_65plus`, `pop_age_unknown`, `pop_total_census`)
を追加している。

- 339区域(`area_basic.csv` の `published_fy=="R7"` 行)の2020年国勢調査人口。
  `area_code` 昇順。
- `data/geo/iryoken2.geojson` の `area_code` 集合と完全一致することを
  `scripts/build_population.py` がハード検算している(片方にしか無い
  コードがあれば全部列挙して終了コード1で失敗する)。

### `population_prefecture.csv`

列: `pref_code, pref_name, population_2020, source, retrieved_on`
に加え、issue #28 で年齢列(`population_iryoken2.csv` と同じ列名)を
追加している。

- 47都道府県(`prefecture_basic.csv` の `published_fy=="R7"` 行、
  「全国」行(`pref_code="00"`)は除く)の2020年国勢調査人口。`pref_code` 昇順。

### 検算結果(2026-08-18実行)

区域(`population_iryoken2.csv`)の人口合計・都道府県
(`population_prefecture.csv`)の人口合計・`prefecture_basic.csv` の
「全国」行(pref_code="00")の人口は、いずれも **126,146,099人で完全一致**
(差0)。差があること自体は許容する設計だが、今回の実測では差は生じていない。

## 年齢階級別人口(issue #28)

339構想区域・47都道府県の人口に、2020年国勢調査の年齢5歳階級・65歳以上
人口を追加した。出典・取得日・SHA-256などの来歴は
[documents/DATA_SOURCES.md](../../documents/DATA_SOURCES.md) の
「年齢階級別人口(2020年国勢調査、issue #28)」節を参照。

再生成するには:

```bash
python scripts/fetch_census_age.py
python scripts/build_population_age.py
```

(`build_population_age.py` は隣リポジトリ visualize-regional-medical-care-for-2040
の `data/processed/iryoken2_A38-20.geojson`・`area_geo_join.csv`・
`data/reference/mie_area_municipalities.csv` を読む。パスは
`--a38-geojson`・`--area-geo-join`・`--mie-csv` で変更できる。
`python scripts/build_population.py` で `population_iryoken2.csv`・
`population_prefecture.csv` の基礎列(総人口)が先に存在している必要がある。)

### 列の共通の注意点(男女計 vs 性別内訳)

- `population_iryoken2.csv`・`population_prefecture.csv` に追加した年齢列は
  **男女計**(census の「0_総数」行)。
- 性別内訳が要るときは `population_iryoken2_age_sex.csv`・
  `population_prefecture_age_sex.csv`(下記)を使う。同じ列名だが
  `sex` 列(`male`/`female`)で行が分かれている。
- `pop_0_4`〜`pop_100plus` は5歳階級21区分(`pop_0_4, pop_5_9, …,
  pop_95_99, pop_100plus`)。`pop_65plus` は census の「(再掲)65歳以上」列
  (5歳階級の再集計ではなく census 自身の値をそのまま使っている)。この列が
  `pop_65_69`〜`pop_100plus`(65-69〜100歳以上の5歳階級バンド)の合計と
  完全一致することも `scripts/build_population_age.py` がハード検算している
  (将来 e-Stat が「(再掲)」の定義を変えた場合に不整合を静かに出荷しない
  ための検算)。`pop_age_unknown` は census の「年齢『不詳』」列
  (`pop_total_census` から5歳階級の合計を引いた値と完全一致することを
  同スクリプトがハード検算している)。`pop_total_census` は census の
  「総数」列(年齢不詳を含む)で、既存の `population_2020` と比較するための列
  (今回の実測では全339区域・47都道府県で完全一致、差0)。
- コードは `muni_code`/`area_code`/`pref_code` いずれもゼロ埋め文字列
  (`dtype=str` で読むこと。先頭ゼロが落ちる典型的な罠)。

### `population_iryoken2_age_sex.csv` / `population_prefecture_age_sex.csv`

列: `area_code, area_name, pref_code, pref_name, sex, pop_0_4, …, pop_100plus,
pop_65plus, pop_age_unknown, pop_total_census`
(都道府県版は `area_code`/`area_name` の代わりに `pref_code`/`pref_name` のみ)

- 339区域×2性別=678行、47都道府県×2性別=94行。SMR算出などの分母として
  性別ストラタが要る場面向け。`sex` は `male`/`female`(census の
  「1_男」/「2_女」)のみで、`0_総数` 相当は男女計の主CSV側にある。

### `municipality_to_iryoken2.csv`

列: `muni_code, muni_name, area_code, area_name, pref_code, pref_name, mapping_source`

- 全国1,896市区町村(政令指定都市の区を含む)→339構想区域の対応表。
  `muni_code` 昇順。
- `mapping_source` は `A38b_001`(隣リポジトリの `iryoken2_A38-20.geojson`
  経由、1,867件)または `mie_area_municipalities`(三重県、
  `data/reference/mie_area_municipalities.csv` 経由、29件)。三重県だけ
  A38の335圏版とR7の339区域版で粒度が異なる(旧4圏域が8区域に細分化)ため、
  隣リポジトリの `area_geo_join.csv` で unmatched になっている12区域全てを
  この対応表で置き換えている(詳細は
  [documents/DATA_SOURCES.md](../../documents/DATA_SOURCES.md) 参照)。
- census(2020年国勢調査)の市区町村コード集合と、この対応表の `muni_code`
  集合が完全一致することを `scripts/build_population_age.py` が
  ハード検算している(片方にしか無いコードは握り潰さず
  `population_age_audit.csv` に書き出す。issue #28 の要件)。

### `population_age_audit.csv`

列: `check, code, name, expected, actual, diff, note`

- `scripts/build_population_age.py` が常に(異常が無くても)書き出す監査表。
  ヘッダのみ(0行)なら異常なし。
- 想定する `check` 値: `muni_only_in_census` / `muni_only_in_mapping`
  (対応表の網羅性)、`national_reconciliation`(全国検算)、
  `sex_consistency`(男+女≠総数)、`pop65plus_vs_band_sum`
  (`pop_65plus` ≠ Σ65-69〜100歳以上バンド)、`pref_rollup`
  (都道府県ロールアップ)、`area_total_vs_population_2020` /
  `pref_total_vs_population_2020`(census総数と既存 `population_2020` の差)。
- 2026-08-18実行時点では **0行**(異常なし。全339区域・47都道府県・
  1,896市区町村ですべてのハード検算に合格)。

### やっていないこと(推測で作らない)

`iryoken2_A38-20.geojson`(335圏版、生のA38属性)には `A38b_007`〜`A38b_011`
という人口らしき数値属性があるが、各属性が何を指すかを国土数値情報の
仕様書で確認していないため使わない(今後の手がかりとしてのみ記録)。

## 施設の二次医療圏割付(issue #9)

`specialists_facility.csv`(名簿本体、施設ベース、1,059行)の各行を、
医療情報ネット・国土数値情報P04の参照点テーブルに突合し、二次医療圏へ
割り付けた結果。出典・生成コマンドは
[documents/DATA_SOURCES.md](../../documents/DATA_SOURCES.md) の
「施設の座標データ」節を参照。`data/curated/facility_crosswalk.csv`
(人手の対応づけ)の位置づけは [data/curated/README.md](../curated/README.md)。

再生成するには:

```bash
python scripts/build_facility_reference.py
python scripts/link_facilities.py
python scripts/verify_facility_linkage.py
```

### `facility_geo_audit.csv`

列: `pref_name, facility_name, n_specialists, match_status, match_method,
coordinate_source, assignment_basis, care_setting, ref_facility_name,
iryoken2_code, iryoken2_name, lon, lat, reason_code, contested`

名簿本体の全1,059行(突合の成否を問わず)を1行も落とさず載せる監査表。
氏名は含まないが、施設単位の集計値である点は `specialists_facility.csv` と
同様。公開範囲の考え方と利用上の注意は、本ファイル末尾の「施設単位データの
公開範囲と利用上の注意」節を参照。

- `match_status`: `matched`(割付できた)/ `unmatched`(施設名が参照点に
  当たらなかった)/ `unassignable`(座標を持たせようがない: 名簿に施設の
  記載が無い・国外・または診療を行わない勤務先で所在の参照点も決まらない)
- `match_method`: `normalized_exact`(正規化名の完全一致)/
  `normalized_suffix`(接尾一致)/ `crosswalk`(人手の対応づけ)/ 空(未割付・割付不可)
- `coordinate_source`: 座標の出所(`iryojoho_hospital` / `iryojoho_clinic` /
  `ksj_p04` / `crosswalk`)
- `assignment_basis`: 割付の根拠。`automatic`(名寄せの自動突合)/
  `university_hospital` / `research_institute` / `renamed` / `non_care_workplace`
  (いずれも crosswalk 経由の推論)/ `unassignable`
- **`care_setting`(issue #9改訂で新設): 診療の場かどうか。`care` / `non_care` /
  空(座標を持たせようがない行のみ)。** `automatic` 突合は医療情報ネット・
  P04の病院票/診療所票の参照点にしか当たらないため、突合できた時点で
  構造的に診療の場であり一律 `care` を入れる(`link_facilities.py` の
  コメント参照)。crosswalk 経由の行は `data/curated/facility_crosswalk.csv`
  の `care_setting` 列をそのまま反映する。ユーザー指摘
  (「国立健康危機管理研究機構 国立感染症研究所は診療機関じゃない」)を
  受けて、「除外する/しない」の二択から「診療の場かどうかをフラグで持ち、
  2通りの分布を出す」設計に変更した(詳細は
  [docs/handson/04-case-study.md](../../docs/handson/04-case-study.md)
  「データの制約」節)。
- `contested`: 複数の名簿行が同じ参照点に当たった採用行に立つ補助フラグ
  (採用/不採用の別である `match_status`/`reason_code` とは別列)

2026-08-18時点の実測(`PYTHONUTF8=1 python scripts/link_facilities.py`):

| 区分 | 行 | 専門医数 |
|---|---:|---:|
| crosswalk 経由の割付 | 100 | 536 |
| tier1 医療情報ネット | 506 | 755 |
| tier2 医療情報ネット | 178 | 246 |
| tier1 P04 | 66 | 93 |
| tier2 P04 | 24 | 26 |
| **matched 計(施設を特定できた)** | **874** | **1,656(87.4%)** |
| — うち診療の場(care) | 862 | 1,628 |
| — うち非診療の勤務先(non_care) | 12 | 28 |
| unmatched(未割付) | 147 | 163 |
| unassignable(施設掲載なし21行46名＋海外1行13名) | 22 | 59 |
| unassignable(non_care_workplaceで所在不明) | 16 | 16 |
| 合計 | 1,059 | 1,894 |

**「施設を特定できた」(matched)と「二次医療圏の地図に載る」(iryoken2_code
が非空)は別の数である点に注意。** さらに地図に載る人数は **care(主系列)**
と **all(care+non_care)** の2系列がある:

| 系列 | 地図に載る人数 | 割付率 |
|---|---:|---:|
| care(診療の場のみ・主系列) | 1,626名 | 85.9% |
| all(勤務地ベース。care+non_care) | 1,654名 | 87.3% |
| (参考: 施設を特定できた割合。matched全体) | 1,656名 | 87.4% |

matched(1,656名)のうち二次医療圏ポリゴンに入らない施設は
`長崎県 サン・レモ リハビリ病院`(2名、care)の1件のみで、この差は
care・all両系列に共通して現れる(1,626 + 2 = 1,628 = matched care、
1,654 + 2 = 1,656 = matched全体)。

- **未割付(unmatched)**: 施設名が医療情報ネット・P04のどちらの参照点にも
  正規化名で当たらなかった行。147行・163名。
- **割付不可(unassignable)**: 2つの内訳がある。
  - 名簿に施設の記載が無い(「施設掲載なし」、21行・46名)、または勤務先が
    国外(「海外」、1行・13名)。合わせて22行・59名(`care_setting` は空)。
  - `basis=non_care_workplace`(診療を行わない勤務先)だが所在の参照点が
    決まらなかった行(`reason_code=no_location_for_non_care`)。16行・16名
    (`care_setting=non_care`。所在不明なので座標もiryoken2_codeも無いが、
    診療を行わない勤務先であることは分かっているため `care_setting` は
    埋まる)。
- `assignment_basis` の分布: `automatic` 921 / `university_hospital` 82 /
  `non_care_workplace` 22(うち所在判明 6行7名・matched / 所在不明 16行16名・
  unassignable) / `unassignable` 22 / `renamed` 9 / `research_institute` 3
- 都道府県別の割付率(専門医数ベース・care基準=主系列)は富山県 64.3% が
  最低、島根県ほか複数県で 100%(「海外」は 0/13 で対象外)
- 欠測の偏り検査: 県別の割付率(matched かつ iryoken2_codeが非空 かつ
  care_setting==care、つまり主系列で実際に地図に載る人数/名簿本体人数)と
  人口10万対専門医数(名簿本体ベース)の Spearman順位相関は **ρ = −0.1134**。
  地図の模様が欠測パターンの反映になっていないことの確認で、
  `PYTHONUTF8=1 python scripts/verify_facility_linkage.py`(条件7)を
  実行すれば再現できる
- 参照点テーブル: 医療情報ネット 78,385件 + P04 112,452件 = 190,837件
  (読み込み82,841件、うち座標センチネル等4,456件を除外)

### `specialists_iryoken2.csv`

列: `iryoken2_code, iryoken2_name, pref_name, n_specialists_care, n_specialists_all`

- `facility_geo_audit.csv` の `match_status=matched` かつ `iryoken2_code` が
  非空の行を二次医療圏で合計したもの。`iryoken2.geojson` の339区域を
  過不足なく含む(0人の区域も行として存在する。0人と欠測を区別するため)。
- **`n_specialists_care` が主系列。** `care_setting=="care"` の行だけを
  合計したもの、つまり「診療の場にいる専門医だけを数える」分布。教材が
  扱うのは専門医による診療へのアクセスであり、感染症研究所・保健所・
  製薬企業等は専門医ではあるがその医療圏の住民が受診できる先ではないため、
  主系列には含めない。合計は **1,626名**。
- `n_specialists_all` は `care_setting=="care"` に `"non_care"` を加えた
  「名簿の勤務地をすべて数える」分布。合計は **1,654名**
  (`n_specialists_all >= n_specialists_care` が339区域すべてで成り立つ。
  `scripts/verify_facility_linkage.py` の条件9)。
- matched 合計 1,656名との差2名(care・all共通)は
  `長崎県 サン・レモ リハビリ病院`。参照点の座標がどの医療圏ポリゴンにも
  入らないため(`iryoken2.geojson` は1km²未満の離島リングを除去済み)、
  この施設は `matched` として専門医数に数えられているが、どの二次医療圏の
  集計にも入らない。

## 施設単位データの公開範囲と利用上の注意

`specialists_facility.csv`・`facility_geo_audit.csv` はいずれも施設単位の
集計値を保持している(issue #47)。この2ファイルに共通する公開範囲と
注意点をここにまとめる。

- **由来**: 日本感染症学会 感染症専門医名簿(2026-07-01版)の公開PDFを
  機械的に集計したもの。取得日・出典URLなどの来歴は
  [documents/DATA_SOURCES.md](../../documents/DATA_SOURCES.md) を参照。
- **氏名は一切含まないが、それは再識別リスクが無いことを意味しない**:
  両ファイルとも氏名列は持たない(集計値のみ)。ただし施設名
  (`facility_name`)は公開されている名簿PDFと突合可能であり、施設名と
  名簿を突き合わせれば個人単位の推定が可能な場合がある。「氏名列が無い」
  ことと「再識別されえない」ことは別問題として扱うこと。
- **利用上のお願い**: これらのファイルは都道府県別・二次医療圏別の
  集計を組み立てる元のファイルとして公開している。個人の特定を目的とした
  利用はしないこと。

この節の判断の経緯は issue #47(2026-08-21 のコメントで承認)。あわせて
`CLAUDE.md`「決定済み」節・`LICENSE` §3 も参照。
