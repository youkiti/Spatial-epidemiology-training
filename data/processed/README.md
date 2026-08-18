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
- **氏名は一切含まない**(集計値のみ)。

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

- 339区域(`area_basic.csv` の `published_fy=="R7"` 行)の2020年国勢調査人口。
  `area_code` 昇順。
- `data/geo/iryoken2.geojson` の `area_code` 集合と完全一致することを
  `scripts/build_population.py` がハード検算している(片方にしか無い
  コードがあれば全部列挙して終了コード1で失敗する)。

### `population_prefecture.csv`

列: `pref_code, pref_name, population_2020, source, retrieved_on`

- 47都道府県(`prefecture_basic.csv` の `published_fy=="R7"` 行、
  「全国」行(`pref_code="00"`)は除く)の2020年国勢調査人口。`pref_code` 昇順。

### 検算結果(2026-08-18実行)

区域(`population_iryoken2.csv`)の人口合計・都道府県
(`population_prefecture.csv`)の人口合計・`prefecture_basic.csv` の
「全国」行(pref_code="00")の人口は、いずれも **126,146,099人で完全一致**
(差0)。差があること自体は許容する設計だが、今回の実測では差は生じていない。

### やっていないこと(推測で作らない)

年齢階級別人口・65歳以上人口は `area_basic.csv` に無いため、今回は
**総人口のみ**を出す。年齢階級別は e-Stat からの取得が別途必要で未着手。

`iryoken2_A38-20.geojson`(335圏版、生のA38属性)には `A38b_007`〜`A38b_011`
という人口らしき数値属性があるが、各属性が何を指すかを国土数値情報の
仕様書で確認していないため使わない(今後の手がかりとしてのみ記録)。
