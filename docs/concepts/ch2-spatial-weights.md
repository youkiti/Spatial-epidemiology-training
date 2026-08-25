# 章2: 空間重み行列 — 「隣」を先に決める

<div data-chapter-progress></div>

前章では、地域ごとの割合を計算し地図に描きました。ここから先は3段階の2番目、「集まっているか」というパターンの検討に進みます。しかしパターンを統計的に検定する前に、人間がひとつだけ決めておかなければならないことがあります。「どの地域とどの地域を隣とみなすか」です。この定義を空間重み行列(spatial weights matrix)と呼び、次章以降の Global Moran's I・LISA・Getis-Ord Gi\* はすべてこの行列を土台にして計算されます。本章では、隣接の代表的な定義方法と、定義を変えると分析結果が変わりうることを扱います。

## この章の学習目標

- 通常の統計にはない発想として、「A地域の隣はどこか」を先に定義する必要性を説明できる
- queen contiguity(境界を共有すれば隣)の定義を説明できる
- 距離閾値による近接定義(例: 50km以内は隣)を説明できる
- 隣接定義を変えると分析結果が変わりうることを理解する

## 通常の統計にはない発想

回帰分析やt検定では、データ点どうしの位置関係を定義する必要はありません。標本の各行は互いに交換可能なものとして扱われ、「このデータ点とあのデータ点は隣同士だから特別扱いする」といった作業は発生しません。

ところが空間統計では話が変わります。「地域Aの値は周囲の地域と似ているか」を調べるには、そもそも「周囲」が何を指すのかを先に決めておかないと計算を始められません。この「隣」の定義を、地域の数だけ並べた正方行列として表したものが空間重み行列 `W` です。行列の `i` 行 `j` 列の要素は、地域 `i` から見た地域 `j` の重みを表し、対角要素(自分自身に対応する行と列が交わる要素)は常に0にします。

`W` の作り方には複数の流儀があり、どれを選ぶかは分析者が自分で決めます。統計ソフトが自動的に最適な定義を選んでくれるわけではありません。代表的な決め方を順に見ていきます。

## 隣接による定義: queen contiguity と rook contiguity

もっとも直感的な決め方は、境界を共有しているかどうかで隣を決める方法です。ここには2つの流儀があります。

- **queen contiguity**: 境界を1点でも共有していれば隣とみなす(頂点だけが接している斜めの位置関係も含む)。チェスのクイーンが縦・横・斜めのどの方向にも動けることになぞらえた呼び方です。
- **rook contiguity**: 境界を線として共有している場合だけ隣とみなす(頂点だけの接触は除く)。チェスのルークが縦・横にしか動けないことになぞらえています。

3×3のマス目の中央のセルを基準にすると、queen では周囲8マスすべてが隣になりますが、rook では上下左右の4マスだけが隣になります。

<svg viewBox="0 0 380 180" width="100%" role="img" style="max-width:100%;height:auto">
  <title>queen contiguity と rook contiguity の比較。3×3マスの中央セルを基準に、queenでは周囲8マス、rookでは上下左右4マスが隣になる</title>
  <text x="89" y="16" text-anchor="middle" font-size="13" fill="currentColor">queen contiguity(8方向)</text>
  <text x="267" y="16" text-anchor="middle" font-size="13" fill="currentColor">rook contiguity(4方向)</text>
  <!-- queen grid: origin (20,34), cell 42, gap 6, step 48 -->
  <g>
    <rect x="20" y="34" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="68" y="34" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="116" y="34" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="20" y="82" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="68" y="82" width="42" height="42" fill="currentColor" fill-opacity="0.35" stroke="currentColor"/>
    <rect x="116" y="82" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="20" y="130" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="68" y="130" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="116" y="130" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <text x="41" y="60" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="89" y="60" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="137" y="60" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="41" y="108" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="89" y="108" text-anchor="middle" font-size="15" fill="currentColor">●</text>
    <text x="137" y="108" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="41" y="156" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="89" y="156" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="137" y="156" text-anchor="middle" font-size="15" fill="currentColor">1</text>
  </g>
  <!-- rook grid: origin (198,34) -->
  <g>
    <rect x="198" y="34" width="42" height="42" fill="none" stroke="currentColor"/>
    <rect x="246" y="34" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="294" y="34" width="42" height="42" fill="none" stroke="currentColor"/>
    <rect x="198" y="82" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="246" y="82" width="42" height="42" fill="currentColor" fill-opacity="0.35" stroke="currentColor"/>
    <rect x="294" y="82" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="198" y="130" width="42" height="42" fill="none" stroke="currentColor"/>
    <rect x="246" y="130" width="42" height="42" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
    <rect x="294" y="130" width="42" height="42" fill="none" stroke="currentColor"/>
    <text x="219" y="60" text-anchor="middle" font-size="15" fill="currentColor">0</text>
    <text x="267" y="60" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="315" y="60" text-anchor="middle" font-size="15" fill="currentColor">0</text>
    <text x="219" y="108" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="267" y="108" text-anchor="middle" font-size="15" fill="currentColor">●</text>
    <text x="315" y="108" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="219" y="156" text-anchor="middle" font-size="15" fill="currentColor">0</text>
    <text x="267" y="156" text-anchor="middle" font-size="15" fill="currentColor">1</text>
    <text x="315" y="156" text-anchor="middle" font-size="15" fill="currentColor">0</text>
  </g>
</svg>

図中の●が基準セル、1と書かれたマスがそのセルから見た隣、0と書かれたマスは隣とみなさないマスです。細長い形の地域や、頂点だけで接する地域が多い地図では、queen と rook のどちらを選ぶかで隣の数が変わり、後述するように分析結果にも影響します。

## 距離に基づく定義: 距離閾値と k近傍

境界を共有しない場合でも隣を定義したいことがあります。たとえば地域の代表点(役所の位置や重心)だけを扱う場合や、境界を共有していなくても近ければ影響し合うと考えたい場合です。ここでは2つの方法がよく使われます。

- **距離閾値**: 「地域の中心点どうしの距離が50km以内なら隣」のように、距離の基準値を1つ決めて隣を定義する方法です。基準値の取り方次第で隣の数が地域ごとに大きく変わります(都市部では多数、過疎地では少数、になりやすい)。
- **k近傍(k-nearest neighbors)**: 各地域について、距離が近い順にちょうどk個の地域を隣とする方法です。すべての地域で隣の数がk個に揃う一方、地域の密度が違うと隣までの距離はばらつきます。都市部のk近傍は数km以内に収まっても、過疎地のk近傍は数十km離れることがあります。

距離閾値もk近傍も、境界を共有しない地域(離島や飛び地)にも隣を割り当てられるという利点があります。次のセクションで、この利点が実務上どれだけ重要かを見ます。

## 隣接関係を重み行列にする

隣の定義が決まったら、それを行列 `W` として書き出します。A市・B市・C市・D市の4地域が、次のような位置関係にあるとします(架空の配置例です)。

<svg viewBox="0 0 260 200" width="100%" role="img" style="max-width:100%;height:auto">
  <title>4地域の隣接関係。A市はB市・C市と隣接し、D市とは隣接しない(架空の配置例)</title>
  <line x1="84" y1="50" x2="176" y2="50" stroke="currentColor"/>
  <line x1="60" y1="74" x2="60" y2="136" stroke="currentColor"/>
  <line x1="200" y1="74" x2="200" y2="136" stroke="currentColor"/>
  <line x1="84" y1="160" x2="176" y2="160" stroke="currentColor"/>
  <circle cx="60" cy="50" r="24" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
  <circle cx="200" cy="50" r="24" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
  <circle cx="60" cy="160" r="24" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
  <circle cx="200" cy="160" r="24" fill="currentColor" fill-opacity="0.15" stroke="currentColor"/>
  <text x="60" y="55" text-anchor="middle" font-size="15" fill="currentColor">A市</text>
  <text x="200" y="55" text-anchor="middle" font-size="15" fill="currentColor">B市</text>
  <text x="60" y="165" text-anchor="middle" font-size="15" fill="currentColor">C市</text>
  <text x="200" y="165" text-anchor="middle" font-size="15" fill="currentColor">D市</text>
</svg>

線で結ばれた地域どうしが隣です。A市はB市・C市と隣接しますが、対角線上のD市とは境界を共有していないため隣ではありません(rook contiguity に相当する配置です)。この関係をそのまま0/1の行列にすると、次の表になります。行が「見る側」、列が「見られる側」で、対角(自分自身)は0です。

| |A市|B市|C市|D市|
|---|---|---|---|---|
|A市|0|1|1|0|
|B市|1|0|0|1|
|C市|1|0|0|1|
|D市|0|1|1|0|

この行列を**行標準化(row-standardization)**すると、各行の和が1になるように重みを配分し直します。A市の行は隣が2つ(B市・C市)なので、それぞれの重みを1/2にします。

| |A市|B市|C市|D市|
|---|---|---|---|---|
|A市|0|0.5|0.5|0|
|B市|0.5|0|0|0.5|
|C市|0.5|0|0|0.5|
|D市|0|0.5|0.5|0|

行標準化した `W` を使うと、ある地域の「隣の値」を計算する操作が、隣接する地域の値の**単純平均**を取る操作と一致します。この「隣の平均値」という考え方は、次章で扱う Global Moran's I の計算にそのまま使われるため、ここで形を確認しておく意味があります。

## テスト

<div data-quiz-src="../../assets/data/quiz-ch2-selfcheck.json"></div>

## 定義を変えると結果は変わる

ここまでに見た定義方法は、どれも「唯一の正解」ではありません。同じ地図でも、どの定義を選ぶかによって隣の数や隣の顔ぶれが変わり、その結果として空間統計の計算結果も変わりえます。

たとえば、対角線上でしか接していない2地域があるとします。queen contiguity ではこの2地域は隣ですが、rook contiguity では隣になりません。地域の形が入り組んでいる地図(海岸線が複雑な地域や、都道府県境が斜めに走る地域)では、この違いだけで隣の総数が大きく変わることがあります。

さらに深刻なのは、離島や飛び地の扱いです。本州から海を隔てた島は、どの地域とも境界を共有しないため、queen contiguity でも rook contiguity でも隣が0個になります。隣が0個の地域は、行標準化のときに行の和が0のままになってしまい、「隣の平均値」を計算できません。このような地域を含む地図では、境界共有による定義だけに頼らず、距離閾値やk近傍を併用して隣を補う必要があります。

もう1つ注意すべき点があります。分析結果を見てから「こちらの定義のほうが望ましい結果になるから」という理由で隣の定義を選び直すことは避けるべきです。これは章6で扱う落とし穴の1つ、「隣」の定義の事後決定にあたります(詳しくは[章6: 初学者が注意する5つの落とし穴](ch6-pitfalls.md)を参照)。隣の定義は、分析結果を見る前に、地域の形状やデータの性質にもとづいて決めておくべき事柄です。

## まとめ

- 空間統計では、分析を始める前に「どの地域とどの地域が隣か」を人間が定義する必要がある。これは通常の回帰分析やt検定にはない発想である
- queen contiguity は境界の共有(頂点のみの接触を含む)で隣を決め、rook contiguity は辺の共有だけで隣を決める。チェスのクイーンとルークの動き方になぞらえられる
- 境界を共有しない地域には、距離閾値やk近傍による定義を使う。特に離島・飛び地では境界共有による定義だけでは隣が0個になりうる
- 隣接関係は0/1の空間重み行列 `W` として表し、行標準化すると「隣の平均値」を計算する操作になる
- 隣の定義を変えると分析結果も変わりうるため、分析結果を見てから定義を選び直すこと(事後決定)は避ける

## 章末クイズ

全問に回答してから、まとめて採点します(一括採点)。8割以上の正解で合格です。不正解だった設問には解説が表示されます。何度でも再挑戦できます。合格記録はこの端末のブラウザ内(localStorage)にのみ保存され、サーバーには送信されません。

<div data-quiz-src="../../assets/data/quiz-ch2.json" data-quiz-gate="ch2"></div>

## 次に読む章

次章の[章3: Global Moran's I — 全体として偏っている?](ch3-global-moran.md)では、本章で定義した空間重み行列を使って、地図全体としてまとまりがあるかを検定する Global Moran's I を扱います。
