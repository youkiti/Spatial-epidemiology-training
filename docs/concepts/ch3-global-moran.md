# 章3: Global Moran's I — 全体として偏っている?

<div data-chapter-progress></div>

章1では地域ごとの率を計算して地図に塗り(記述)、章2では「隣」をどう定義するか(空間重み行列)を先に決めました。この章はその続きで、教材3段階の**2番目「パターン」**に入ります。決めた「隣」を使って、「地図全体として、似た値を持つ地域が近くに集まっているか」を1つの数値で要約する Global Moran's I を扱います。地図の色を見て「なんとなく固まっている気がする」という印象を、数値と検定に置き換える最初の一歩です。

## この章の学習目標

- 空間的自己相関(spatial autocorrelation)とは何かを、正の自己相関・負の自己相関の両方を例に説明できる
- Global Moran's I が「地図全体として似た地域が集まっているか」を測る指標であることを説明できる
- Moran's I の符号(プラス/ランダム付近/マイナス)の解釈を説明できる
- permutation test(値をシャッフルして偶然の集まり方と比較する)による有意性検定の考え方を説明できる
- Global Moran's I だけでは「どこが集まっているか」は分からないという限界を説明できる

## 空間的自己相関 — 「近くは似ているか」を測る

普通の統計では、観測値どうしは互いに独立だと仮定することが多くあります。しかし地域データでは、隣どうしの地域は年齢構成・医療アクセス・社会経済状況などが似ていることが多く、値そのものも近くの地域どうしで似た傾向を持ちやすい、という発想があります。この「近くの地域ほど値が似ているか」という性質を**空間的自己相関(spatial autocorrelation)**と呼びます。

空間的自己相関には向きが2つあります。

- **正の空間自己相関**: 高い値の地域の近くには高い値の地域が、低い値の地域の近くには低い値の地域が来やすい状態。似た値どうしが地理的にまとまっている。
- **負の空間自己相関**: 高い値の地域の隣に低い値の地域が来やすい状態。市松模様のように高低が入れ替わる。

どちらの場合も、「近く」が何を指すかは章2で決めた空間重み行列(W)に依存します。W を変えれば「隣」の範囲が変わるため、同じデータでも空間的自己相関の測り方は変わりえます([章2: 空間重み行列](ch2-spatial-weights.md)を参照)。

## 図で見る: 正の空間自己相関と負の空間自己相関

同じ大きさの4行5列のグリッドで、正の場合と負の場合を並べます。数値はどちらも架空の例(仮に有病率だとします)で、実際に計算した Moran's I の値ではありません。

<figure>
<svg viewBox="0 0 220 180" width="220" style="max-width:100%;height:auto" role="img">
<title>正の空間自己相関の例。左上に高い値(12〜15)がまとまり、右上に低い値(2〜3)がまとまっている。</title>
<rect x="10" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.36" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="35" text-anchor="middle" font-size="14" fill="currentColor">12</text>
<rect x="50" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.39" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="35" text-anchor="middle" font-size="14" fill="currentColor">13</text>
<rect x="90" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.42" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="35" text-anchor="middle" font-size="14" fill="currentColor">14</text>
<rect x="130" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.08" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="35" text-anchor="middle" font-size="14" fill="currentColor">3</text>
<rect x="170" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="35" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="10" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.39" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="75" text-anchor="middle" font-size="14" fill="currentColor">13</text>
<rect x="50" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="75" text-anchor="middle" font-size="14" fill="currentColor">15</text>
<rect x="90" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.42" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="75" text-anchor="middle" font-size="14" fill="currentColor">14</text>
<rect x="130" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="75" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="170" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.08" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="75" text-anchor="middle" font-size="14" fill="currentColor">3</text>
<rect x="10" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.36" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="115" text-anchor="middle" font-size="14" fill="currentColor">12</text>
<rect x="50" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.42" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="115" text-anchor="middle" font-size="14" fill="currentColor">14</text>
<rect x="90" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.39" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="115" text-anchor="middle" font-size="14" fill="currentColor">13</text>
<rect x="130" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.08" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="115" text-anchor="middle" font-size="14" fill="currentColor">3</text>
<rect x="170" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="115" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="10" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.11" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="155" text-anchor="middle" font-size="14" fill="currentColor">4</text>
<rect x="50" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.08" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="155" text-anchor="middle" font-size="14" fill="currentColor">3</text>
<rect x="90" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="155" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="130" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.23" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="155" text-anchor="middle" font-size="14" fill="currentColor">8</text>
<rect x="170" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="155" text-anchor="middle" font-size="14" fill="currentColor">7</text>
</svg>
<figcaption>正の空間自己相関の例(架空データ)。塗りが強いセルほど値が高いことを表す(ライトテーマでは濃く、ダークテーマでは明るく表示される)。左上(12〜15)は高い値どうし、右上(2〜3)は低い値どうしが隣接しており、近くの値が似ている。</figcaption>
</figure>

<figure>
<svg viewBox="0 0 220 180" width="220" style="max-width:100%;height:auto" role="img">
<title>負の空間自己相関の例。高い値(10)と低い値(2)が市松模様に交互配置されている。</title>
<rect x="10" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="35" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="50" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="35" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="90" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="35" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="130" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="35" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="170" y="10" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="35" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="10" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="75" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="50" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="75" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="90" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="75" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="130" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="75" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="170" y="50" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="75" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="10" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="115" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="50" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="115" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="90" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="115" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="130" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="115" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="170" y="90" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="115" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="10" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="30" y="155" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="50" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="70" y="155" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="90" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="110" y="155" text-anchor="middle" font-size="14" fill="currentColor">2</text>
<rect x="130" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.3"/>
<text x="150" y="155" text-anchor="middle" font-size="14" fill="currentColor">10</text>
<rect x="170" y="130" width="40" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.3"/>
<text x="190" y="155" text-anchor="middle" font-size="14" fill="currentColor">2</text>
</svg>
<figcaption>負の空間自己相関の例(架空データ)。高い値(10)のセルの隣は必ず低い値(2)のセルになっており、市松模様になっている。</figcaption>
</figure>

1枚目のグリッドは、隣どうしが似た値を持つ配置なので、正の空間自己相関の典型例です。このような配置では Global Moran's I はプラス寄りの値になりやすいと考えられます。2枚目は隣どうしが逆の値を持つ市松模様で、負の空間自己相関の典型例であり、Moran's I はマイナス寄りの値になりやすいと考えられます。どちらも、実際に Moran's I を計算した数値ではなく、符号の向きについての説明であることに注意してください(具体的な数値は自分で計算していません)。

## Moran scatterplot のイメージ — 値と「隣の平均」の関係

Global Moran's I を直感的にイメージする方法があります。章2で決めた空間重み行列 W を行ごとに合計が1になるよう調整(行標準化)すると、各地域について「隣接地域の値の平均」を計算できます。これを**空間ラグ(spatial lag)**と呼びます。

Global Moran's I は、大まかに言えば

```
各地域の値 × その地域の空間ラグ(隣の平均的な値)
```

の相関を見ていると考えるとよいです。横軸に各地域の値、縦軸にその地域の空間ラグをとって散布図を描いたものを**Moran scatterplot**と呼び、Moran's I はこの散布図に引いた回帰直線の傾きにおおむね対応します。

<figure>
<svg viewBox="0 0 240 240" width="240" style="max-width:100%;height:auto" role="img">
<title>Moran scatterplot の模式図。横軸は各地域の値、縦軸はその地域の空間ラグ(隣の平均)。右上がりの傾向は正の空間自己相関を示す。</title>
<line x1="20" y1="120" x2="220" y2="120" stroke="currentColor" stroke-opacity="0.5"/>
<line x1="120" y1="20" x2="120" y2="220" stroke="currentColor" stroke-opacity="0.5"/>
<line x1="30" y1="210" x2="210" y2="30" stroke="currentColor" stroke-opacity="0.6" stroke-dasharray="4 3"/>
<circle cx="40" cy="195" r="4" fill="currentColor"/>
<circle cx="55" cy="175" r="4" fill="currentColor"/>
<circle cx="70" cy="165" r="4" fill="currentColor"/>
<circle cx="95" cy="140" r="4" fill="currentColor"/>
<circle cx="110" cy="128" r="4" fill="currentColor"/>
<circle cx="130" cy="112" r="4" fill="currentColor"/>
<circle cx="150" cy="95" r="4" fill="currentColor"/>
<circle cx="170" cy="70" r="4" fill="currentColor"/>
<circle cx="185" cy="55" r="4" fill="currentColor"/>
<circle cx="200" cy="40" r="4" fill="currentColor"/>
<circle cx="60" cy="105" r="4" fill="currentColor" fill-opacity="0.4"/>
<circle cx="175" cy="165" r="4" fill="currentColor" fill-opacity="0.4"/>
<text x="215" y="134" font-size="11" text-anchor="end" fill="currentColor">値(自分の地域)</text>
<text x="30" y="30" font-size="11" text-anchor="start" fill="currentColor">隣の平均</text>
<text x="170" y="65" font-size="11" text-anchor="middle" fill="currentColor">High-High</text>
<text x="70" y="65" font-size="11" text-anchor="middle" fill="currentColor">Low-High</text>
<text x="70" y="185" font-size="11" text-anchor="middle" fill="currentColor">Low-Low</text>
<text x="170" y="185" font-size="11" text-anchor="middle" fill="currentColor">High-Low</text>
</svg>
<figcaption>Moran scatterplot の模式図(架空データ)。点が右上(High-High)と左下(Low-Low)の象限に多く集まり、右上がりの回帰直線になるほど、Global Moran's I はプラスに大きくなる。この4象限の名称は、章4で扱う Local Moran's I(LISA)の分類とそのままつながっている。</figcaption>
</figure>

点が右上(自分も高い・隣の平均も高い)と左下(自分も低い・隣の平均も低い)に多く集まり、右上がりの直線に近づくほど正の空間自己相関が強いことになります。逆に、点が右下(自分は高いのに隣の平均は低い)と左上(自分は低いのに隣の平均は高い)に多く集まり、右下がりの直線になると負の空間自己相関を示します。この4つの象限の名前(High-High / Low-High / Low-Low / High-Low)は章4の Local Moran's I(LISA)でそのまま使う分類なので、ここで見た目を覚えておくと章4の理解が早くなります。

## Global Moran's I の符号の読み方

| Moran's I の値 | 解釈 |
|---|---|
| プラスで大きい | 高い値の地域の近くに高い値の地域、低い値の地域の近くに低い値の地域が集まりやすい(正の空間自己相関) |
| ランダム時の期待値付近 | 地理的なパターンは特にない(値の配置が偶然のばらつきと区別しにくい) |
| マイナス | 高い値の地域の隣に低い値の地域が来やすい(負の空間自己相関、市松模様的な配置) |

ここで注意したいのは、「ランダムなら Moran's I はちょうど0になる」わけではないという点です。地域数を n とすると、値の配置が完全にランダムなときの Moran's I の期待値は

```
-1 / (n - 1)
```

であり、厳密には0ではなくわずかにマイナスの値です。n が大きくなるほどこの期待値は0に近づくため実務上は無視できることが多いのですが、地域数が少ない場合は「マイナスだから負の空間自己相関」と早合点せず、この期待値と比べて有意に低いかどうかを確認する必要があります。

## permutation test — 「偶然の集まり方」と比べる

観測された Moran's I の値が、単なる偶然でも起こりうる程度なのか、それとも偶然では説明しにくいほど極端なのかを判断するために、**permutation test**(並べ替え検定)がよく使われます。考え方は次の通りです。

1. 空間重み行列 W(隣接構造)は固定したまま変えない。
2. 各地域に割り当てられている値だけを、地図上でランダムにシャッフルし直す。
3. シャッフルした配置で Moran's I を計算する。
4. 2〜3 を何百回・何千回と繰り返し、Moran's I の分布(シャッフルを繰り返したときにどんな値が出やすいか)を作る。
5. 実際に観測された Moran's I が、この分布の中でどのくらい極端な位置にあるかを見る。分布の端(上位・下位のごく一部)に位置するなら、偶然では説明しにくい=統計的に有意と判断する。

ポイントは、**隣接構造(誰と誰が隣か)は固定したまま、値の配置だけを偶然にする**という点です。実際の地域の位置関係は変えず、「もしこの値がこの地図の上でランダムに散らばっていたら」という仮想的な状況と比較します。この方法は近年の空間疫学の研究でも有意性の評価によく用いられています。

## Global で分かること・分からないこと

Global Moran's I は、地図全体をひとつの数値に要約した指標です。「日本全体として、地域差が地理的にまとまっているか」というレベルの問いには答えられますが、次のことは分かりません。

- **どこが集まっているか**: Global Moran's I が大きくプラスであっても、それが地図のどの部分で起きているかは教えてくれません。
- **正と負が打ち消し合っている可能性**: 地図の一部に強い正のクラスター(似た値どうしのまとまり)があり、別の一部に負のパターン(高低が入れ替わる配置)があると、両者が互いに打ち消し合って Global Moran's I 全体としてはほぼ0に近い値になることがあります。この場合、「Global の値が小さいから地理的なパターンはない」と結論づけると、実際に存在する局所的なクラスターを見落とすことになります。

「どこが集まっているか」を具体的な地域単位で調べるには、地域ごとの局所指標である Local Moran's I(LISA)や Getis-Ord Gi\* が必要です。これは次の章で扱います([章4: LISA / Gi\* / SaTScan の違い](ch4-lisa-gi-satscan.md))。

## 実例: がん検診研究にみる手順

Pradhan P, Iyer HS, Rebbeck TR. *JAMA Netw Open.* 2025;8(10):e2537905(がん検診)は、米国3,142 county 単位のがん検診受診率(乳がん・子宮頸がん・大腸がんの各検診、1997〜2019年)を対象に、次の手順で分析しています。

1. county ごとの検診率を地図にする。
2. queen contiguity(章2で扱った、境界を共有すれば隣とみなす定義)で隣接関係を定義する。
3. Global Moran's I で「全米として検診率の地理的な偏りがあるか」を確認する。
4. LISA(Local Moran's I)で「具体的にどの地域がクラスターになっているか」を特定する。

報告されている Global Moran's I は、たとえばマンモグラフィ検診では 1997〜1999年の 0.57 から 2017〜2019年の 0.10 へと、83%減衰しています(子宮頸がん検診では 0.44 から 0.07 へ、85%の減衰)。同じ指標を時期ごとに繰り返し計算することで、「検診受診率の地理的なまとまりが、20年かけて弱まってきた」という時間変化を1つの数値の推移として読めるようになっている点が、この論文の Global Moran's I の使い方の特徴です。

ただし、0.10 という値は「地理的な偏りが消えた」という意味ではありません。この論文自身が、Global Moran's I で空間的自己相関を確認したうえで、続けて「具体的にどこか」を特定する段階に進んでいます。手順の続き(LISA による具体的なクラスターの特定)は次章で扱います。

## 自己チェック

合否は記録されません。その場での理解確認用です。

<div data-quiz-src="../../assets/data/quiz-ch3-selfcheck.json"></div>

## まとめ

- 空間的自己相関には正(似た値どうしが近接)と負(高低が交互に配置)の2方向がある。
- Global Moran's I は「各地域の値」と「空間ラグ(隣の平均)」の関係を1つの数値に要約した指標であり、Moran scatterplot の回帰直線の傾きに相当するとイメージできる。
- 符号の解釈はプラス(正の自己相関)/ランダム時の期待値付近(パターンなし)/マイナス(負の自己相関)の3通り。ランダム時の期待値は -1/(n-1) であり厳密には0ではない。
- permutation test は、隣接構造を固定したまま値の配置だけをシャッフルし、観測された Moran's I が偶然の分布の中でどれだけ極端かを見る方法である。
- Global Moran's I は地図全体の要約値であり、どこが集まっているかは教えてくれない。正のクラスターと負のパターンが打ち消し合い、Global がほぼ0になることもある。
- 「どこが集まっているか」を特定するには次章の Local Moran's I(LISA)や Getis-Ord Gi\* が必要になる。

## 章末クイズ

全問に回答してから、まとめて採点します(一括採点)。8割以上の正解で合格です。不正解だった設問には解説が表示されます。何度でも再挑戦できます。合格記録はこの端末のブラウザ内(localStorage)にのみ保存され、サーバーには送信されません。

<div data-quiz-src="../../assets/data/quiz-ch3.json" data-quiz-gate="ch3"></div>

## 次に読む章

[章4: LISA / Gi\* / SaTScan の違い](ch4-lisa-gi-satscan.md) — Global Moran's I では分からなかった「どこが集まっているか」を、地域ごとに具体的に特定する方法を扱います。
