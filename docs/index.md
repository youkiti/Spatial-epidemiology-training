# 空間疫学入門

このサイトは、一定の疫学の素養がある読者(公衆衛生大学院生、臨床疫学を学ぶ医療者、行政・研究機関で保健統計を扱う担当者など)を対象にした、空間疫学(地理疫学)の入門教材です。

## この教材の出発点

**「地図を描く」ことと「空間統計を行う」ことは別物です。** choropleth map で地域ごとに色を塗るところまでは多くの教材が扱いますが、その先にある「本当に集まっているのか」を検定する発想 — 空間自己相関、空間重み行列 — は、通常の疫学カリキュラムではあまり扱われません。この区別を、本教材の全章を通じた出発点に置きます。

学習は次の3段階の型で進みます。

| 段階 | 問い | 手法 |
|---|---|---|
| 1 記述 | どこで多い? | 率・有病率・標準化率、SIR/SMR、choropleth map |
| 2 パターン | 集まっている? | Global Moran's I、Local Moran's I(LISA)、Getis-Ord Gi\*、spatial scan statistic |
| 3 説明 | なぜそこに多い? | 通常回帰、spatial regression、CAR / BYM |

## 2部構成

1. **概念パート**(全6章) — 理論・ビジュアル・具体例を並列に提示し、各章に自己チェッククイズと章末クイズが紐づきます。「読んで終わり」ではなく、理解確認を挟みながら進む設計です。
2. **Rハンズオン**(本編3本+環境準備) — 同じ概念を R で手を動かして再現します。①は架空データだけで完結し、②③は日本感染症学会の専門医名簿を題材にした実データも使います。実データが何を数えていて何を数えていないかは、あわせて[ケーススタディのデータ(資料)](handson/04-case-study.md)にまとめています。

## 想定読者

率・有病率・標準化率・交絡といった疫学の基礎概念は既知として説明を省略します。一方で、**空間統計に固有の概念**(空間自己相関、空間重み行列、MAUP、空間的アウトライヤー)は初出の概念として丁寧に扱います。

## 各章への導線

- [使い方](how-to-use.md) — 読み進め方とクイズの位置づけ
- 概念パート: [章1 記述](concepts/ch1-descriptive.md) / [章2 空間重み行列](concepts/ch2-spatial-weights.md) / [章3 Global Moran's I](concepts/ch3-global-moran.md) / [章4 LISA / Gi\* / SaTScan](concepts/ch4-lisa-gi-satscan.md) / [章5 説明](concepts/ch5-explanatory.md) / [章6 落とし穴](concepts/ch6-pitfalls.md)
- Rハンズオン: [⓪環境準備](handson/00-setup.md) / [①地図→Moran's I→LISA→Gi\*](handson/01-map-moran-lisa-gi.md) / [②CAR/BYM](handson/02-car-bym.md) / [③MAUPの実演](handson/03-maup.md)
- 資料: [ケーススタディのデータ](handson/04-case-study.md) — ②③が使う実データの制約
- [このサイトについて](about.md) / [免責事項](disclaimer.md)
