# 章4: LISA / Gi\* / SaTScan の違い ★教材の山場

<div data-chapter-progress></div>

[章3](ch3-global-moran.md)のGlobal Moran's Iは、地図全体として似た値の地域が集まっているかを1つの数値で教えてくれますが、「具体的にどこに集まっているのか」には答えられません。本章はこの問いに答える3つの手法 — Local Moran's I(LISA)、Getis-Ord Gi\*、spatial scan statistic(SaTScan) — の違いを扱います。3つとも「集まりを探す」手法に見えますが、問いの立て方も出力の形も異なります。段階2(パターン)の核心であり、本教材でもっとも誤解されやすい部分です。

## この章の学習目標

- Local Moran's I(LISA)が「自分の値」と「周囲の値」の組み合わせを High-High / Low-Low / High-Low / Low-High の4種類に分類する手法であることを説明できる
- Getis-Ord Gi\*が「高い値・低い値の“塊”」(hot spot / cold spot)を探す手法であり、LISAのような4分類は行わないことを説明できる
- 「値が高い」ことと「hot spotである」ことは別であることを、具体的な数値グリッドを使って説明できる
- spatial scan statistic(SaTScan)が「地図上を様々な大きさの窓で走査し、異常に患者が多い地理的範囲を探す」手法であり、LISA・Gi\*とは検出の発想自体が異なることを説明できる
- LISAのHigh-Low(空間的アウトライヤー)と、Gi\*のhot spotの違いを説明できる

## 章3からのつながり — 「集まっている?」から「どこに?」へ

[章3](ch3-global-moran.md)のGlobal Moran's Iは、地図全体を1つの数値に要約する指標でした。プラスに大きければ「全体として似た値の地域が近くにまとまっている」とは言えますが、そのまとまりが地図のどのあたりにあるのかまでは教えてくれません。本章の3手法は、いずれもこの「どこに?」を明らかにするための手法です。ただし問いの立て方が違うため、同じ地図に適用しても検出される場所や出力の形が変わります。まずは一行でそれぞれの役割を押さえておきます。

- **Gi\*は「塊探し」** — 対象の地域とその周囲をまとめて見て、高い値ばかりが集まっているかを調べる。結果はhot spot / cold spot / 特徴なしのいずれか。
- **LISAは「自分と周囲の関係の分類」** — 自分の値と周囲の値が似ているか、逆かによって4種類に分類する。
- **SaTScan(spatial scan statistic)は「異常に患者が多い地理的範囲の探索」** — 地図上をさまざまな大きさの円(窓)で走査し、窓の内と外で発生率を比べて、もっとも尤度の高い範囲を検出する。空間・時間・時空間のクラスターを扱える。

この一行要約を頭に置いたうえで、順番に詳しく見ていきます。なお、LISAとGi\*はどちらも「どの地域を隣とみなすか」という[空間重み行列](ch2-spatial-weights.md)を前提に、その隣接地域の値から「周囲の値」を計算します。空間重み行列を先に決めておく必要があるのは、この2手法に共通する前提です。

## LISAの4分類 — 自分の値 × 周囲の平均

[章3](ch3-global-moran.md)のMoran散布図は、横軸に「自分の値」、縦軸に「周囲の値の平均(空間ラグ)」を取り、地域を4つの象限に位置づけるものでした。Local Moran's I(LISA)は、この散布図の発想を地域ごとの分類に応用した手法です。それぞれの地域について「自分の値」と「周囲の平均」の組み合わせを、次の4種類のいずれかに分類します。

<svg viewBox="0 0 320 320" role="img" aria-labelledby="lisa-quad-title lisa-quad-desc" style="max-width:100%;height:auto">
  <title id="lisa-quad-title">LISAの4分類(自分の値×周囲の平均)</title>
  <desc id="lisa-quad-desc">横軸は自分の値、縦軸は周囲の平均。右上がHigh-High、左上がLow-High、左下がLow-Low、右下がHigh-Low。High-HighとLow-Lowはクラスターの中心(塗りが濃い)、High-LowとLow-Highは空間的アウトライヤー(塗りが薄い)。</desc>
  <rect x="170" y="20" width="130" height="130" fill="currentColor" fill-opacity="0.22" stroke="currentColor" stroke-opacity="0.4"/>
  <rect x="40" y="20" width="130" height="130" fill="currentColor" fill-opacity="0.08" stroke="currentColor" stroke-opacity="0.4"/>
  <rect x="40" y="150" width="130" height="130" fill="currentColor" fill-opacity="0.22" stroke="currentColor" stroke-opacity="0.4"/>
  <rect x="170" y="150" width="130" height="130" fill="currentColor" fill-opacity="0.08" stroke="currentColor" stroke-opacity="0.4"/>
  <line x1="170" y1="20" x2="170" y2="280" stroke="currentColor" stroke-width="1.5"/>
  <line x1="40" y1="150" x2="300" y2="150" stroke="currentColor" stroke-width="1.5"/>
  <text x="235" y="80" text-anchor="middle" fill="currentColor" font-size="14" font-weight="bold">High-High</text>
  <text x="235" y="97" text-anchor="middle" fill="currentColor" font-size="11">クラスターの中心</text>
  <text x="105" y="80" text-anchor="middle" fill="currentColor" font-size="14" font-weight="bold">Low-High</text>
  <text x="105" y="97" text-anchor="middle" fill="currentColor" font-size="11">空間的アウトライヤー</text>
  <text x="105" y="215" text-anchor="middle" fill="currentColor" font-size="14" font-weight="bold">Low-Low</text>
  <text x="105" y="232" text-anchor="middle" fill="currentColor" font-size="11">クラスターの中心</text>
  <text x="235" y="215" text-anchor="middle" fill="currentColor" font-size="14" font-weight="bold">High-Low</text>
  <text x="235" y="232" text-anchor="middle" fill="currentColor" font-size="11">空間的アウトライヤー</text>
  <text x="170" y="308" text-anchor="middle" fill="currentColor" font-size="13">自分の値 →</text>
  <text x="14" y="150" text-anchor="middle" fill="currentColor" font-size="13" transform="rotate(-90 14 150)">周囲の平均 →</text>
  <text x="45" y="296" text-anchor="start" fill="currentColor" font-size="11">低</text>
  <text x="295" y="296" text-anchor="end" fill="currentColor" font-size="11">高</text>
  <text x="30" y="277" text-anchor="middle" fill="currentColor" font-size="11">低</text>
  <text x="30" y="28" text-anchor="middle" fill="currentColor" font-size="11">高</text>
</svg>

| 分類 | 自分の値 | 周囲の平均 | 位置づけ |
|---|---|---|---|
| High-High | 高い | 高い | クラスターの中心 |
| Low-Low | 低い | 低い | クラスターの中心 |
| High-Low | 高い | 低い | 空間的アウトライヤー |
| Low-High | 低い | 高い | 空間的アウトライヤー |

High-HighとLow-Lowは「自分も周囲も同じ傾向」なので、似た値の地域が寄り集まったクラスターの中心とみなせます。一方High-LowとLow-Highは「自分だけ周囲と逆」なので、周囲から浮いた空間的アウトライヤーとみなせます。

## Gi\* — 高い値・低い値の“塊”を探す

Getis-Ord Gi\*は、LISAのような4分類は行いません。調べるのは「対象の地域とその周囲をまとめて見たときに、高い値ばかりが集まっているか」という一点です。結果は次の3種類のいずれかにまとまります。

- hot spot(高い値の塊)
- cold spot(低い値の塊)
- 特に特徴なし

Gi\*にとって重要なのは「中心の地域だけが高いか」ではなく「周囲を含めて高いか」です。自分と周囲をまとめて評価するため、周囲が低いと中心の高さは押し下げられます。この性質が、次節で扱う本章の核心につながります。

### Gi\*が実際に見ている数値のイメージ

Gi\*は、対象の地域と周囲を合わせた領域全体の値の合計(または平均)を、地図全体の平均と比べるという考え方に基づきます。次節で使う2つのグリッドで、中心の地域と周囲8地域を合わせた9マスの平均を計算してみると、この違いがはっきりします。

- 空間的アウトライヤーの例(2が8個、20が1個): 9マスの平均は (2×8+20) ÷ 9 = 4.0。中心の値20そのものよりずっと低く、周囲8マスの低さに引っ張られる
- hot spotの例(10・11・12が周囲を埋める): 9マスの平均は (10×4+11×4+12) ÷ 9 ≈ 10.7。個々の値(10〜12)と近く、全体として高い水準を保ったまま

同じ「中心の値が周囲より高い」状況でも、9マスの平均で見るとまったく違う結果になります。これがGi\*が「値そのものの高さ」ではなく「周囲を含めた高さ」を検出する仕組みです。

## 核心: 「値が高い」ことと「hot spotである」ことは別

以下の2つの3×3グリッドを比べます。どちらも中央のマスが目を引きますが、周囲の値が違います。

<svg viewBox="0 0 360 210" role="img" aria-labelledby="grid-cmp-title grid-cmp-desc" style="max-width:100%;height:auto">
  <title id="grid-cmp-title">数値グリッドの対比: 空間的アウトライヤーとhot spot</title>
  <desc id="grid-cmp-desc">左のグリッドは中央が20、周囲8マスがすべて2。中央だけが突出して高いが周囲は低い。右のグリッドは中央が12、周囲が10または11。突出した値はないが全体が高い水準でまとまっている。塗りの濃さは各グリッド内での値の相対的な高さを表す。</desc>
  <text x="86" y="18" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">空間的アウトライヤーの例</text>
  <text x="86" y="34" text-anchor="middle" fill="currentColor" font-size="11">中央だけ高く周囲は低い</text>
  <rect x="20" y="54" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="64" y="54" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="108" y="54" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="20" y="98" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="64" y="98" width="44" height="44" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="108" y="98" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="20" y="142" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="64" y="142" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="108" y="142" width="44" height="44" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-opacity="0.5"/>
  <text x="42" y="81" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="86" y="81" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="130" y="81" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="42" y="125" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="86" y="125" text-anchor="middle" fill="currentColor" font-size="15">20</text>
  <text x="130" y="125" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="42" y="169" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="86" y="169" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="130" y="169" text-anchor="middle" fill="currentColor" font-size="15">2</text>
  <text x="274" y="18" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">hot spotの典型例</text>
  <text x="274" y="34" text-anchor="middle" fill="currentColor" font-size="11">突出はないが周囲も高い</text>
  <rect x="208" y="54" width="44" height="44" fill="currentColor" fill-opacity="0.30" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="252" y="54" width="44" height="44" fill="currentColor" fill-opacity="0.38" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="296" y="54" width="44" height="44" fill="currentColor" fill-opacity="0.30" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="208" y="98" width="44" height="44" fill="currentColor" fill-opacity="0.38" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="252" y="98" width="44" height="44" fill="currentColor" fill-opacity="0.45" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="296" y="98" width="44" height="44" fill="currentColor" fill-opacity="0.38" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="208" y="142" width="44" height="44" fill="currentColor" fill-opacity="0.30" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="252" y="142" width="44" height="44" fill="currentColor" fill-opacity="0.38" stroke="currentColor" stroke-opacity="0.5"/>
  <rect x="296" y="142" width="44" height="44" fill="currentColor" fill-opacity="0.30" stroke="currentColor" stroke-opacity="0.5"/>
  <text x="230" y="81" text-anchor="middle" fill="currentColor" font-size="15">10</text>
  <text x="274" y="81" text-anchor="middle" fill="currentColor" font-size="15">11</text>
  <text x="318" y="81" text-anchor="middle" fill="currentColor" font-size="15">10</text>
  <text x="230" y="125" text-anchor="middle" fill="currentColor" font-size="15">11</text>
  <text x="274" y="125" text-anchor="middle" fill="currentColor" font-size="15">12</text>
  <text x="318" y="125" text-anchor="middle" fill="currentColor" font-size="15">11</text>
  <text x="230" y="169" text-anchor="middle" fill="currentColor" font-size="15">10</text>
  <text x="274" y="169" text-anchor="middle" fill="currentColor" font-size="15">11</text>
  <text x="318" y="169" text-anchor="middle" fill="currentColor" font-size="15">10</text>
</svg>

左のグリッドは、中央の20が周囲(すべて2)よりはるかに大きく、明らかに「値が高い」地域です。しかし周囲は低いままなので、Gi\*ではhot spotとして検出されにくくなります。Gi\*は自分と周囲をまとめて見るため、周囲が低いと中心の高さが押し下げられてしまうからです。LISAではこれを **High-Low(空間的アウトライヤー)** として明示的に検出できます。

右のグリッドは、中央の12が周囲(10・11)より突出しているわけではなく、値の差はわずかです。しかし周囲を含めて全体が高い水準でまとまっているため、Gi\*では典型的な **hot spot** になり得ます。

同じ「真ん中が高い」という見た目でも、周囲がどうかによってGi\*の判定は正反対になります。**この対比が本章の核心です。**「値そのものが高い」ことと「高い値が地理的に固まっている」ことは別、という区別を必ず押さえてください。

LISAの視点で同じ2つのグリッドを見直すと、対比がさらにはっきりします。LISAでいう「周囲の平均」は、自分自身を除いた隣接地域だけの平均です。

- 空間的アウトライヤーの例: 中心の自分の値は20。隣接する8地域はすべて2なので、周囲の平均は2。「自分は高い・周囲は低い」の組み合わせなのでHigh-Lowに分類されます
- hot spotの例: 中心の自分の値は12。隣接する8地域(10が4つ、11が4つ)の平均は (10×4+11×4) ÷ 8 = 10.5。「自分も高い・周囲も高い」の組み合わせなのでHigh-Highに分類されます

同じ「中心が高い」という見た目でも、周囲の平均を計算するとLISAの分類はHigh-LowとHigh-Highで正反対になり、Gi\*の判定(hot spotになりにくい/なりやすい)とも対応しています。

### よくある誤解

- 「値が単独で高ければhot spotだ」という誤解: 誤り。周囲が低ければGi\*ではhot spotになりにくく、LISAではHigh-Low(空間的アウトライヤー)になる
- 「LISAとGi\*は同じものを違う名前で呼んでいるだけ」という誤解: 誤り。LISAは4分類、Gi\*はhot spot/cold spot/特徴なしの3分類であり、そもそも分類のカテゴリ数と定義が異なる
- 「SaTScanもLISA・Gi\*と同じく地域ごとに指標を計算する」という誤解: 誤り。SaTScanは地域ごとの指標ではなく、様々な範囲(窓)を候補として比較し、範囲そのものを検出する

## 自己チェック

合否は記録されません。その場での理解確認用です。

<div data-quiz-src="../../assets/data/quiz-ch4-selfcheck.json"></div>

## 「クラスター」は一般名詞である

ここまで見てきたhot spot・cold spot・LISAの4分類・SaTScanの検出領域は、それぞれ別の手法・別の定義に基づいています。それにもかかわらず、これらをまとめて「クラスター」と呼ぶ場面が多く、これが混乱のもとになります。

**クラスターは一般名詞**であり、手法によって指すものが異なります。たとえば「果物」という言葉の中にリンゴやミカンがあるように、「クラスター」という言葉の中にhot spot・LISAクラスター・SaTScanクラスターがあると考えると整理しやすくなります。

```
空間クラスター(一般名詞)
├─ 高い値の塊       → hot spot(Gi*)
├─ 低い値の塊       → cold spot(Gi*)
├─ High-High        → LISAクラスター
├─ Low-Low          → LISAクラスター
└─ 異常発生領域      → SaTScanクラスター
```

一言でまとめると、**ホットスポット・コールドスポットは「高い/低い値のまとまり」を指す言葉であり、クラスターはもっと広い概念で、LISAやSaTScanでは別の定義のまとまりもクラスターと呼ぶ**、ということです。

### LISA・Gi\*の有意性の考え方

LISA・Gi\*とも、計算した値がどのくらい極端かを、[章3](ch3-global-moran.md)で扱ったpermutation test(値をシャッフルして偶然の集まり方と比較する)と同じ考え方で検定できます。1つの地域だけでなく地図上の全地域について同時に検定を行うため、偶然でも一部の地域は有意な結果になりやすいという多重比較の問題が生じます。これはLISA・Gi\*に共通する注意点であり、次節で扱うSaTScanの検定方法とも対比できます。

## Gi\* と LISA の対応表

同じ状況について、Gi\*とLISAがそれぞれ何と呼ぶかを整理します。

| 状況 | Gi\*の判定 | LISAの判定 |
|---|---|---|
| 自分も周囲も高い | hot spot | High-High(クラスターの中心) |
| 自分も周囲も低い | cold spot | Low-Low(クラスターの中心) |
| 自分だけ高い(周囲は低い) | hot spotになりにくい | High-Low(空間的アウトライヤー) |
| 自分だけ低い(周囲は高い) | cold spotになりにくい | Low-High(空間的アウトライヤー) |

上段2行(自分も周囲も高い/低い)ではGi\*とLISAの結論はほぼ一致します。違いが表に出るのは下段2行、つまり自分と周囲の値がずれているときです。Gi\*はこの状況を積極的には拾わない一方、LISAはHigh-Low・Low-Highという名前を与えて明示的に分類します。この表を「LISAはGi\*の上位互換だ」と読むのは誤りで、Gi\*は「塊のまとまり具合」を、LISAは「自分と周囲の関係」を、それぞれ別の切り口で見ているだけです。

## SaTScan — 発想そのものが異なる

LISAとGi\*は、どちらも「各地域について1つずつ指標を計算し、その地域を分類する」という発想です。SaTScan(spatial scan statistic)はこれとは異なり、**範囲そのものを候補として走査し、もっとも尤度比の高い範囲を選ぶ**という発想を取ります。

具体的には、地図上にさまざまな大きさ・位置の円(窓)を置き、それぞれの窓について「窓の内側の発生率」と「窓の外側の発生率」を比較します。人口から期待される患者数に比べて窓の内側の患者数が多いほど尤度比が大きくなり、この尤度比がもっとも大きい窓を「もっとも異常な範囲(最尤クラスター)」として検出します。SaTScanは空間だけでなく、時間・時空間のクラスターも同じ発想で検出できます。代表的なソフトウェアの名前がそのまま手法名としても使われています。

```
      ○
    ○ ○ ○
  ○ ○ ○ ○ ○
    ○ ○ ○
```

イメージとしては、上のような円(窓)を地図上のあらゆる位置・あらゆる大きさで動かし、「この円の中だけ患者が人口から期待される数より異常に多くないか」を1つずつ調べていく、という探索です。LISA・Gi\*が「あらかじめ決めた地域(二次医療圏や都道府県など)ごとに指標を計算する」のに対し、SaTScanは「地域の境界とは無関係に、円という任意の範囲を候補として動かす」という点で発想の出発点が異なります。

LISA・Gi\*とSaTScanの違いは、出力される形にも表れます。LISA・Gi\*の出力は「地域ごとのラベル」(この地域はHigh-High、あの地域はhot spot、といった具合)ですが、SaTScanの出力は「円などで囲まれた領域」です。多重比較への対処も異なります。LISA・Gi\*は地図上のすべての地域について同時にモンテカルロ検定を行うのに対し、SaTScanは無数の窓を試したうえで選ばれた1つの最尤クラスターについて、観測データを繰り返しシミュレーションするモンテカルロ検定でその有意性を確認します。

なお、本教材ではSaTScanの考え方の紹介にとどめ、実際の操作手順はここでは扱いません。SaTScanを実演するハンズオンにするかどうかは、本教材ではまだ決まっていません。

## 3手法をどう使い分けるか

ここまでの内容を、実際の分析でどう使い分けるかという視点で整理します。

- **「高い値の塊がどこにあるか、ざっくり掴みたい」** → Gi\*が向いています。hot spot / cold spot / 特徴なしという3分類は解釈しやすく、地図として提示しやすい結果になります
- **「自分の地域が周囲と似ているか、逆に浮いているかまで知りたい」** → LISAが向いています。High-Low・Low-Highという空間的アウトライヤーは、Gi\*だけでは見落とされがちな情報です
- **「地域の境界にとらわれず、患者が異常に多い範囲そのものを知りたい」** → SaTScanが向いています。あらかじめ決めた地域単位の粒度に縛られず、円という任意の範囲で検出します

3手法は競合するものではなく、目的に応じて使い分ける、あるいは組み合わせて使うものです。たとえば地図全体の偏りをGlobal Moran's Iで確認し(章3)、具体的な場所をLISAで特定し、それとは独立にSaTScanでも異常範囲が一致するかを確認する、という使い方もできます。

## 実例: Global から Local への対比

Pradhan P, Iyer HS, Rebbeck TR. *JAMA Netw Open.* 2025;8:e2537905 は、米国の郡(county)単位のがん検診データについて、queen contiguityで空間重み行列を定義し、Global Moran's Iで全体としての偏りの有無を確認したうえで、LISAで具体的にどこに偏りがあるかを特定するという手順を取っています。[章3](ch3-global-moran.md)のGlobal Moran's Iだけでは分からなかった「具体的にどこか」を、この章のLISAが補うという構造を、実際の論文の手順として確認できます。地図全体の偏りを1つの数値で確認したあとに、具体的な場所を特定する段階に進むというこの2段構えの流れは、本章冒頭で示した「Global→Local」の関係そのものです。具体的な統計値はここでは示しません(裏取りが済み次第、別途反映されます)。

## まとめ

- Gi\*は「塊探し」、LISAは「自分と周囲の関係の分類」、SaTScanは「異常な範囲の探索」であり、3手法は問いの立て方が異なる
- LISAはHigh-High / Low-Low / High-Low / Low-Highの4分類を行う。High-High・Low-Lowはクラスターの中心、High-Low・Low-Highは空間的アウトライヤー
- 「値が高い」ことと「hot spotである」ことは別。周囲が低ければ単独の高値はGi\*ではhot spotになりにくく、LISAではHigh-Lowとして検出される
- 「クラスター」は一般名詞であり、hot spot・LISAの分類・SaTScanの検出領域はそれぞれ別の定義に基づく
- SaTScanはLISA・Gi\*と異なり、範囲そのものを走査して最尤の領域を選ぶ手法であり、出力の形(領域かラベルか)や多重比較への対処も異なる
- 3手法は競合するものではなく、地図全体の偏り(Global Moran's I)→具体的な場所(LISA・Gi\*)→境界にとらわれない異常範囲(SaTScan)という順に、目的に応じて使い分けたり組み合わせたりできる

## 章末クイズ

全問に回答してから、まとめて採点します(一括採点)。12問中10問以上の正解で合格です。不正解だった設問には解説が表示されます。何度でも再挑戦できます。合格記録はこの端末のブラウザ内(localStorage)にのみ保存され、サーバーには送信されません。

<div data-quiz-src="../../assets/data/quiz-ch4.json" data-quiz-gate="ch4"></div>

## 次に読む章

[章5: 説明 — なぜそこに多い?](ch5-explanatory.md)に進みます。
