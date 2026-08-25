# 空間疫学入門

このサイトは、一定の疫学の素養がある読者(公衆衛生大学院生、臨床疫学を学ぶ医療者、行政・研究機関で保健統計を扱う担当者など)を対象にした、空間疫学(地理疫学)の入門教材です。

## この教材の出発点

**「地図を描く」ことと「空間統計を行う」ことは別物です。** 地域ごとに割合などの値を計算し、その値の階級に応じて区域を塗り分けた地図を choropleth map(階級区分による塗り分け地図)と呼びます。次がその模式図です。

<figure>
<svg viewBox="0 0 500 250" width="440" role="img" style="max-width:100%;height:auto" aria-labelledby="idx-choro-title idx-choro-desc">
<title id="idx-choro-title">choropleth map の模式図。7区域からなる架空の地域を、人口10万対患者数の階級で塗り分けている。</title>
<desc id="idx-choro-desc">架空の7区域が1つの島を構成し、各区域に人口10万対患者数の値が書かれている。値が200以上の区域は塗りが最も強く、100未満の区域は塗りが最も弱い。右側に3階級の凡例がある。</desc>
<g stroke="currentColor" fill="currentColor">
<polygon points="150,20 250,15 275,70 205,85 130,65" fill-opacity="0.45"/>
<polygon points="250,15 340,45 330,100 275,70" fill-opacity="0.25"/>
<polygon points="130,65 205,85 195,145 110,130 95,90" fill-opacity="0.05"/>
<polygon points="205,85 275,70 330,100 300,155 195,145" fill-opacity="0.45"/>
<polygon points="110,130 195,145 180,205 120,215 85,175" fill-opacity="0.05"/>
<polygon points="195,145 300,155 290,210 240,225 180,205" fill-opacity="0.25"/>
<polygon points="300,155 355,140 350,200 290,210" fill-opacity="0.05"/>
</g>
<g font-size="13" text-anchor="middle" fill="currentColor">
<text x="200" y="60">320</text>
<text x="300" y="66">180</text>
<text x="148" y="112">60</text>
<text x="255" y="122">290</text>
<text x="140" y="180">70</text>
<text x="240" y="190">150</text>
<text x="322" y="182">55</text>
</g>
<text x="370" y="28" fill="currentColor" font-size="12">人口10万対患者数</text>
<g font-size="12" fill="currentColor">
<rect x="370" y="42" width="20" height="20" fill-opacity="0.45" stroke="currentColor"/>
<text x="396" y="57">200以上</text>
<rect x="370" y="72" width="20" height="20" fill-opacity="0.25" stroke="currentColor"/>
<text x="396" y="87">100〜199</text>
<rect x="370" y="102" width="20" height="20" fill-opacity="0.05" stroke="currentColor"/>
<text x="396" y="117">100未満</text>
</g>
</svg>
<figcaption>架空の7区域(実在の地域ではありません)。各区域の数値は人口10万対患者数で、塗りの強さはその値が属する階級を表す(塗りが強い区域ほど人口10万対患者数が高い階級。ライトテーマでは濃く、ダークテーマでは明るく表示される)。このように区域を値の階級で塗り分けた地図を choropleth map と呼ぶ。</figcaption>
</figure>

多くの教材はこの塗り分けまでを扱いますが、その先にある「本当に集まっているのか」を検定する発想 — 空間自己相関、空間重み行列 — は、通常の疫学カリキュラムではあまり扱われません。上の図でも、人口10万対患者数の多い区域が地理的に固まっているのか偶然そう見えるだけなのかは、色を見ただけでは判定できません。この区別を、本教材の全章を通じた出発点に置きます。choropleth map の作り方は[章1](concepts/ch1-descriptive.md)、集まりの検定は[章3](concepts/ch3-global-moran.md)以降で扱います。

学習は次の3段階の型で進みます。

| 段階 | 問い | 手法 | 詳しくは |
|---|---|---|---|
| 1 記述 | どこで多い? | 累積罹患割合・有病割合・標準化割合、SIR/SMR(観察数と期待数の比)、choropleth map | [章1](concepts/ch1-descriptive.md) |
| 2 パターン | 集まっている? | Global Moran's I(地域全体の集まり具合を1つの値にまとめる)、Local Moran's I = LISA(どの地域が集まりの中にいるかを4分類する)、Getis-Ord Gi\*(高い値・低い値の塊を探す)、spatial scan statistic(異常に患者が多い地理的範囲を探索する) | [章3](concepts/ch3-global-moran.md)・[章4](concepts/ch4-lisa-gi-satscan.md) |
| 3 説明 | なぜそこに多い? | 通常回帰、spatial regression(空間的な近さを回帰に織り込む)、CAR / BYM(隣接構造を使ってSIRを平滑化する階層ベイズモデル) | [章5](concepts/ch5-explanatory.md) |

この3段階すべての前提として、「どの地域とどの地域が隣か」を先に決める**空間重み行列**があります([章2](concepts/ch2-spatial-weights.md))。

## 2部構成

1. **概念パート**(全6章) — 理論・ビジュアル・具体例を並列に提示し、各章に自己チェッククイズと章末クイズが紐づきます。「読んで終わり」ではなく、理解確認を挟みながら進む設計です。
2. **Rハンズオン**(本編3本+環境準備) — 同じ概念を R で手を動かして再現します。①は架空データだけで完結し、②③は日本感染症学会の専門医名簿を題材にした実データも使います。実データが何を数えていて何を数えていないかは、あわせて[ケーススタディのデータ(資料)](handson/04-case-study.md)にまとめています。

## 想定読者

累積罹患割合・有病割合・標準化割合・交絡といった疫学の基礎概念は既知として説明を省略します。一方で、**空間統計に固有の概念**(空間自己相関、空間重み行列、MAUP、空間的アウトライヤー)は初出の概念として説明します。

## 各章への導線

- [使い方](how-to-use.md) — 読み進め方とクイズの位置づけ
- 概念パート: [章1 記述](concepts/ch1-descriptive.md) / [章2 空間重み行列](concepts/ch2-spatial-weights.md) / [章3 Global Moran's I](concepts/ch3-global-moran.md) / [章4 LISA / Gi\* / SaTScan](concepts/ch4-lisa-gi-satscan.md) / [章5 説明](concepts/ch5-explanatory.md) / [章6 落とし穴](concepts/ch6-pitfalls.md)
- Rハンズオン: [⓪環境準備](handson/00-setup.md) / [①地図→Moran's I→LISA→Gi\*](handson/01-map-moran-lisa-gi.md) / [②CAR/BYM](handson/02-car-bym.md) / [③MAUPの実演](handson/03-maup.md)
- 資料: [ケーススタディのデータ](handson/04-case-study.md) — ②③が使う実データの制約
- [このサイトについて](about.md) / [免責事項](disclaimer.md)
