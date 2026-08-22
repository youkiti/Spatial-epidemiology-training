# 章1: 記述 — どこで多い?

<div data-chapter-progress></div>

空間疫学は「記述(どこで多い?) → パターン(集まっている?) → 説明(なぜそこに多い?)」という3段階で組み立てると理解しやすい教材です。この章は**段階1(記述)**にあたり、患者数をそのまま地図にすることの落とし穴、率・標準化率・SIR/SMRの考え方、choropleth map(階級区分による塗り分け地図)の作り方を扱います。「集まっている」かどうかを統計的に判定する話(空間統計)は章2以降で扱います。この章ではまず、地図に塗る前の数字そのものを正しく作ることに集中します。

## この章の学習目標

- 患者数(count)をそのまま地図にすることの問題点を説明できる
- 発生率・有病率・死亡率を地域単位で計算できる
- 年齢構成が地域間で異なる場合に標準化率が必要な理由を説明できる
- SIR/SMR(観察数と期待数の比)の意味を説明できる(SIR = 1.5 は「期待値の1.5倍」)
- choropleth map の作り方と、色分けの区切り(階級区分)が与える印象の違いに注意できる

## 患者数をそのまま地図にしない

次の2つの地域を比べます。

- 人口10万人の市で、ある感染症が100人発症した
- 人口1,000人の町で、同じ感染症が20人発症した

患者「数」だけを見ると、市(100人)のほうが町(20人)より多く見えます。しかし人口あたりで見ると、市は人口10万対100人、町は人口10万対2,000人であり、町のリスクは市の20倍です。患者数という絶対量と、率という相対量は、まったく違う順位を作ります。

したがって空間疫学の記述の基本は、

```
患者数 ÷ その地域の人口
```

を地域ごとに計算することです。これは発生率(incidence)・有病率(prevalence)・死亡率(mortality)のいずれについても同じで、疫学の素養がある読者にはおなじみの操作でしょう。この章で強調したいのは、この操作を**地図の上で**忘れがちだという点です。次の節で理由を掘り下げます。

## なぜ「地図」では分母の無視が特に起きやすいのか

率ではなく数をそのまま棒グラフにする誤りは、疫学の授業で早い段階に注意されます。ところが地図になると、同じ誤りがずっと見つけにくくなります。理由は地図という表現形式そのものにあります。

- **面積が大きい地域ほど視覚的に目立つ。** 人口が少なく面積の広い地域(山間部など)が地図上で大きな塊として描かれ、実際の患者数や率以上に注意を引きやすくなります。
- **色の濃さは「量が多い」という印象を直接生む。** 濃い色の面が並ぶと、見る側は率の違いではなく単に「色が濃い=悪い」という短絡的な読み取りをしがちです。分子(患者数)をそのまま塗ると、この短絡が起きた結果がそのまま人口の多さの地図になってしまいます。
- **棒グラフと違い、地図には軸(数値の目盛り)が常に見えているとは限らない。** 凡例を確認せずに色の濃淡だけで比較されやすい表現形式です。

次の図で、同じ架空データを患者数で塗った場合と率で塗った場合を比較します。

### 図1: 患者数の地図と率の地図の対比(架空データ)

以下は説明のために作った架空の5市町村のデータです(実在の地域ではありません)。

| 市町村 | 人口 | 患者数 | 人口10万対の率 |
|---|---:|---:|---:|
| A市 | 100,000 | 100 | 100 |
| B町 | 1,000 | 20 | 2,000 |
| C市 | 50,000 | 60 | 120 |
| D市 | 20,000 | 40 | 200 |
| E町 | 5,000 | 15 | 300 |

患者数だけで順位をつけると A(100)>C(60)>D(40)>B(20)>E(15) ですが、率で順位をつけると B(2,000)>E(300)>D(200)>C(120)>A(100) と、ほぼ逆転します。下の図は、この2つの塗り分けを塗りの強さ(不透明度)で表したものです。

<figure>
<svg viewBox="0 0 640 220" width="480" role="img" style="max-width:100%;height:auto" aria-labelledby="fig1-title fig1-desc">
<title id="fig1-title">患者数の地図と人口10万対の率の地図の対比(架空5市町村)</title>
<desc id="fig1-desc">同じ5市町村を、患者数で塗った場合と人口10万対の率で塗った場合で、塗りが強い市町村が入れ替わることを示す図。数値は表1と同じ。</desc>
<text x="10" y="24" fill="currentColor" font-size="15">患者数の地図(塗りが強い = 患者数の順位が高い、5段階)</text>
<g font-size="13">
<rect x="10" y="36" width="100" height="60" fill="currentColor" fill-opacity="0.45" stroke="currentColor"/>
<text x="60" y="60" text-anchor="middle" fill="currentColor">A</text>
<text x="60" y="80" text-anchor="middle" fill="currentColor">100</text>
<rect x="120" y="36" width="100" height="60" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
<text x="170" y="60" text-anchor="middle" fill="currentColor">B</text>
<text x="170" y="80" text-anchor="middle" fill="currentColor">20</text>
<rect x="230" y="36" width="100" height="60" fill="currentColor" fill-opacity="0.35" stroke="currentColor"/>
<text x="280" y="60" text-anchor="middle" fill="currentColor">C</text>
<text x="280" y="80" text-anchor="middle" fill="currentColor">60</text>
<rect x="340" y="36" width="100" height="60" fill="currentColor" fill-opacity="0.25" stroke="currentColor"/>
<text x="390" y="60" text-anchor="middle" fill="currentColor">D</text>
<text x="390" y="80" text-anchor="middle" fill="currentColor">40</text>
<rect x="450" y="36" width="100" height="60" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="500" y="60" text-anchor="middle" fill="currentColor">E</text>
<text x="500" y="80" text-anchor="middle" fill="currentColor">15</text>
</g>
<text x="10" y="130" fill="currentColor" font-size="15">率の地図(塗りが強い = 人口10万対の率の順位が高い、5段階)</text>
<g font-size="13">
<rect x="10" y="142" width="100" height="60" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="60" y="166" text-anchor="middle" fill="currentColor">A</text>
<text x="60" y="186" text-anchor="middle" fill="currentColor">100</text>
<rect x="120" y="142" width="100" height="60" fill="currentColor" fill-opacity="0.45" stroke="currentColor"/>
<text x="170" y="166" text-anchor="middle" fill="currentColor">B</text>
<text x="170" y="186" text-anchor="middle" fill="currentColor">2000</text>
<rect x="230" y="142" width="100" height="60" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
<text x="280" y="166" text-anchor="middle" fill="currentColor">C</text>
<text x="280" y="186" text-anchor="middle" fill="currentColor">120</text>
<rect x="340" y="142" width="100" height="60" fill="currentColor" fill-opacity="0.25" stroke="currentColor"/>
<text x="390" y="166" text-anchor="middle" fill="currentColor">D</text>
<text x="390" y="186" text-anchor="middle" fill="currentColor">200</text>
<rect x="450" y="142" width="100" height="60" fill="currentColor" fill-opacity="0.35" stroke="currentColor"/>
<text x="500" y="166" text-anchor="middle" fill="currentColor">E</text>
<text x="500" y="186" text-anchor="middle" fill="currentColor">300</text>
</g>
</svg>
<figcaption>表1の架空データ。数値ラベルは表1と同一。塗りの強さは数値そのものではなく5市町村内での順位を表す(最も強い0.45が1位、最も弱い0.05が5位)。塗りの強さは、ライトテーマでは濃く、ダークテーマでは明るく表示される。上段は患者数、下段は人口10万対の率で塗り分けている。A市は患者数の地図では最も強い(1位)が、率の地図では最も弱い(5位)。逆にB町はその反対になる。</figcaption>
</figure>

A市は患者数の地図では塗りが最も強いのに、率の地図では塗りが最も弱くなります。逆にB町は患者数の地図では目立たないのに、率の地図では塗りが最も強くなります。感染症専門医の地域偏在を扱うこの教材でも同じ注意が必要です。専門医「数」だけを地図にすると、単に人口が多い都市部が濃く塗られるだけになり、人口あたりで見たときの偏在(人口10万対専門医数)が隠れてしまいます。

## 年齢構成の違いと標準化率

地域どうしで率を比べるとき、もう1つ注意が必要なのが年齢構成です。多くの疾患は高齢者ほど率が高いため、高齢者の割合が高い地域は、それだけで粗率(年齢調整をしない率)が見かけ上高くなります。したがって年齢構成が地域間で大きく異なる場合は、年齢構成をそろえた**年齢標準化率**で比較します。直接法・間接法という2通りの標準化の方法があること自体は、疫学の基礎科目で扱われる範囲なのでここでは深入りしません。空間疫学として重要なのは、**地図に塗る数値をどちらで作るか(粗率か標準化率か)によって、地図の見え方が変わりうる**という点です。

## SIR/SMR — 観察数と期待数の比

標準化のもう1つの表現方法が、SIR(標準化罹患比、Standardized Incidence Ratio)やSMR(標準化死亡比、Standardized Mortality Ratio)です。考え方はシンプルで、

```
SIR (または SMR) = 観察数 O ÷ 期待数 E
```

です。期待数Eは、その地域の年齢構成(や性別構成)に、基準となる集団(全国など)の年齢別の率を当てはめて計算した「もしこの地域が基準集団と同じ率だったら何人発症するはずか」という数値です。したがってSIR = 1.5は「期待される患者数の1.5倍の患者が実際に観察された」という意味になり、SIR = 1が基準(期待通り)、1より大きければ期待より多い、小さければ期待より少ないと読みます。疾病地図では、率をそのまま塗るよりもSIR/SMRを塗るほうが好まれる場面が多くあります。年齢構成の違いを地域ごとに織り込んだうえで、O/Eという一つの比に集約できるため、地域間の比較がしやすくなるからです。

## choropleth map の階級区分

率やSIR/SMRを計算したあと、地図として塗り分ける(choropleth map)ときには、色を変える数値の境目、すなわち**階級区分**を決める必要があります。代表的な階級区分の取り方には次のようなものがあります。

| 階級区分の方法 | 考え方 |
|---|---|
| 等間隔(equal interval) | 最小値から最大値までを同じ幅で区切る |
| 分位(quantile) | 各階級に含まれる地域の数が同じになるように区切る |
| 自然な区切り(natural breaks) | データの値の集まり方(隙間)をもとに区切る |

同じ数値データでも、どの方法を選ぶかによって地図の印象は変わります。次の例で確認します。

### 図2: 階級区分の違いで印象が変わる例

図1の率(表1と同じ、人口10万対)を、3階級に区切ってみます。

| 市町村 | 率 | 等間隔での階級 | 分位での階級 |
|---|---:|:---:|:---:|
| A市 | 100 | 低 | 低 |
| C市 | 120 | 低 | 低 |
| D市 | 200 | 低 | 中 |
| E町 | 300 | 低 | 中 |
| B町 | 2,000 | 高 | 高 |

等間隔(最小100〜最大2,000の幅を3等分)では、B町だけが突出して「高」に入り、残る4市町はすべて「低」という同じ扱いになります。分位(地域数が均等になるように3階級に分ける)では、同じデータでもD市とE町が「中」に移り、A市・C市とは違う色になります。**元のデータは1つも変えていません。**変えたのは区切り方だけです。それでも、地図を見た人が受ける印象(どこが「同じグループ」でどこが「違うグループ」か)は変わります。

<figure>
<svg viewBox="0 0 640 150" width="480" role="img" style="max-width:100%;height:auto" aria-labelledby="fig2-title fig2-desc">
<title id="fig2-title">同じ率データを等間隔と分位で階級区分した場合の塗り分けの違い</title>
<desc id="fig2-desc">表2の5市町村を、等間隔での3階級と分位での3階級でそれぞれ塗り分けた図。D市とE町の階級(塗りの強さ)が、区切り方によって変わることを示す。</desc>
<text x="10" y="20" fill="currentColor" font-size="14">等間隔(A,C,D,Eが同じ「低」、Bだけ「高」)</text>
<g font-size="12">
<rect x="10" y="30" width="90" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="55" y="54" text-anchor="middle" fill="currentColor">A 低</text>
<rect x="110" y="30" width="90" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="155" y="54" text-anchor="middle" fill="currentColor">C 低</text>
<rect x="210" y="30" width="90" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="255" y="54" text-anchor="middle" fill="currentColor">D 低</text>
<rect x="310" y="30" width="90" height="40" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="355" y="54" text-anchor="middle" fill="currentColor">E 低</text>
<rect x="410" y="30" width="90" height="40" fill="currentColor" fill-opacity="0.45" stroke="currentColor"/>
<text x="455" y="54" text-anchor="middle" fill="currentColor">B 高</text>
</g>
<text x="10" y="100" fill="currentColor" font-size="14">分位(D,Eが「中」に移り、A,Cと色が分かれる)</text>
<g font-size="12">
<rect x="10" y="110" width="90" height="30" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="55" y="130" text-anchor="middle" fill="currentColor">A 低</text>
<rect x="110" y="110" width="90" height="30" fill="currentColor" fill-opacity="0.05" stroke="currentColor"/>
<text x="155" y="130" text-anchor="middle" fill="currentColor">C 低</text>
<rect x="210" y="110" width="90" height="30" fill="currentColor" fill-opacity="0.25" stroke="currentColor"/>
<text x="255" y="130" text-anchor="middle" fill="currentColor">D 中</text>
<rect x="310" y="110" width="90" height="30" fill="currentColor" fill-opacity="0.25" stroke="currentColor"/>
<text x="355" y="130" text-anchor="middle" fill="currentColor">E 中</text>
<rect x="410" y="110" width="90" height="30" fill="currentColor" fill-opacity="0.45" stroke="currentColor"/>
<text x="455" y="130" text-anchor="middle" fill="currentColor">B 高</text>
</g>
</svg>
<figcaption>表2の架空データ。塗りの強さは割り当てられた階級(低・中・高)を表す(低0.05・中0.25・高0.45)。区切り方(等間隔/分位)だけを変え、元の率の値は変えていない。それでもD市・E町の塗りの強さが変わる。</figcaption>
</figure>

したがって、他人が作ったchoropleth mapを見るときは、色の濃淡だけでなく**凡例に示された階級区分の方法と境目の数値**を必ず確認する必要があります。逆に自分で地図を作るときは、階級区分の選び方そのものが結論に影響しうることを踏まえ、複数の区切り方で見え方が大きく変わらないかを確認しておくと安全です。

## 自己チェック

合否は記録されません。その場での理解確認用です。

<div data-quiz-src="../../assets/data/quiz-ch1-selfcheck.json"></div>

## 「地図を描く」ことと「空間統計」は別物

この章で扱ったのは、率・標準化率・SIR/SMRという「正しい数値の作り方」と、choropleth mapという「その数値の見せ方」でした。ここまでの作業だけでも、色の濃い地域がどこかは分かります。しかし、**その色の濃い地域どうしが偶然ではなく地理的にまとまっているのかどうか**は、地図を眺めるだけでは判定できません。「なんとなく集まって見える」ことと「統計的にまとまりがあると言える」ことの間には距離があります。この距離を埋めるのが、章2以降で扱う空間統計(空間重み行列、Global Moran's I、LISA/Gi\*/SaTScanなど)です。段階1(記述)から段階2(パターン)への切り替わりが、この章と次章以降の境目にあたります。

## まとめ

- 患者「数」をそのまま地図にすると、単に人口が多い(または面積が大きい)地域が目立つだけになる。人口(分母)で割った率で比較する。
- 地図は面積の大きさや色の濃さが直感的な印象を作りやすく、他の表現形式より分母の無視が起きやすい。
- 年齢構成が地域間で異なる場合は年齢標準化率を使い、年齢構成の違いによる見かけの差を除いて比較する。
- SIR/SMRは観察数Oと期待数Eの比(O/E)であり、SIR = 1.5は「期待値の1.5倍」を意味する。
- choropleth mapの階級区分(等間隔・分位・自然な区切りなど)は、同じデータでも選び方によって地図の印象を変える。
- ここまではすべて「記述」の段階であり、「集まっている」かどうかを判定する空間統計とは別の作業である。

## 章末クイズ

全問に回答してから、まとめて採点します(一括採点)。8割(10問中8問)以上の正解で合格です。不正解だった設問には解説が表示されます。何度でも再挑戦できます。合格記録はこの端末のブラウザ内(localStorage)にのみ保存され、サーバーには送信されません。

<div data-quiz-src="../../assets/data/quiz-ch1.json" data-quiz-gate="ch1"></div>

## 次に読む章

地図に塗る前の数値の作り方が分かったところで、次は空間統計を始める前の準備として「隣」をどう定義するかを扱う [章2: 空間重み行列 — 「隣」を先に決める](ch2-spatial-weights.md) に進んでください。
