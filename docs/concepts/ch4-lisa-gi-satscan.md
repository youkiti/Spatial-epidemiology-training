# 章4: LISA / Gi\* / SaTScan の違い ★教材の山場

<div data-chapter-progress></div>

[章3](ch3-global-moran.md)のGlobal Moran's Iは、地図全体として似た値の地域が集まっているかを1つの数値で教えてくれますが、「具体的にどこに集まっているのか」には答えられません。本章はこの問いに答える3つの手法 — Local Moran's I(LISA)、Getis-Ord Gi\*、spatial scan statistic(SaTScan) — の違いを扱います。3つとも「集まりを探す」手法に見えますが、問いの立て方も出力の形も異なります。段階2(パターン)の核心であり、本教材でもっとも誤解されやすい部分です。

## この章の学習目標

- Local Moran's I(LISA)が「自分の値」と「周囲の値」の組み合わせを High-High / Low-Low / High-Low / Low-High の4種類に分類する手法であることを説明できる
- Getis-Ord Gi\*が「高い値・低い値の“塊”」(hot spot / cold spot)を探す手法であり、LISAのような4分類は行わないことを説明できる
- 「値が高い」ことと「hot spotである」ことは別であることを、具体的な数値グリッドを使って説明できる
- spatial scan statistic(SaTScan)が「地図上を様々な大きさの窓で走査し、異常に患者が多い地理的範囲を探す」手法であり、LISA・Gi\*とは検出の発想自体が異なることを説明できる
- LISAのHigh-Low(空間的アウトライヤー)と、Gi\*のhot spotの違いを説明できる
- LISA・Gi\*の局所的な値は有意性検定のp値だけでなく`Ii`・`Z.Ii`のような統計量としても読めること、統計量とp値がそれぞれ別の問いに答えていることを説明できる

## 事前テスト

本文を読む前に解いてください。正解できなくて構いません — どこが分かっていないかを掴んでから読むための問題です。合否は保存されません。

<div data-quiz-src="../../assets/data/quiz-ch4-selfcheck.json"></div>

## 章3からのつながり — 「集まっている?」から「どこに?」へ

[章3](ch3-global-moran.md)のGlobal Moran's Iは、地図全体を1つの数値に要約する指標でした。プラスに大きければ「全体として似た値の地域が近くにまとまっている」とは言えますが、そのまとまりが地図のどのあたりにあるのかまでは教えてくれません。本章の3手法は、いずれもこの「どこに?」を明らかにするための手法です。ただし問いの立て方が違うため、同じ地図に適用しても検出される場所や出力の形が変わります。まずは一行でそれぞれの役割を押さえておきます。

- **Gi\*は「塊探し」** — 対象の地域とその周囲をまとめて見て、高い値ばかりが集まっているかを調べる。結果はhot spot / cold spot / 特徴なしのいずれか。
- **LISAは「自分と周囲の関係の分類」** — 自分の値と周囲の値が似ているか、逆かによって4種類に分類する。
- **SaTScan(spatial scan statistic)は「異常に患者が多い地理的範囲の探索」** — 地図上をさまざまな大きさの円(窓)で走査し、窓の内と外で人口あたりの患者数を比べて、もっとも尤度の高い範囲を検出する。空間・時間・時空間のクラスターを扱える。

この一行要約を頭に置いたうえで、順番に詳しく見ていきます。なお、LISAとGi\*はどちらも「どの地域を隣とみなすか」という[空間重み行列](ch2-spatial-weights.md)を前提に、その隣接地域の値から「周囲の値」を計算します。空間重み行列を先に決めておく必要があるのは、この2手法に共通する前提です。

## LISAの4分類 — 自分の値 × 周囲の平均

[章3](ch3-global-moran.md)のMoran散布図は、横軸に「自分の値」、縦軸に「周囲の値の平均(空間ラグ)」を取り、地域を4つの象限に位置づけるものでした。Local Moran's I(LISA)は、この散布図の発想を地域ごとの分類に応用した手法です。それぞれの地域について「自分の値」と「周囲の平均」の組み合わせを、次の4種類のいずれかに分類します。

<svg viewBox="0 0 320 320" width="100%" role="img" aria-labelledby="lisa-quad-title lisa-quad-desc" style="max-width:100%;height:auto">
  <title id="lisa-quad-title">LISAの4分類(自分の値×周囲の平均)</title>
  <desc id="lisa-quad-desc">横軸は自分の値、縦軸は周囲の平均。右上がHigh-High、左上がLow-High、左下がLow-Low、右下がHigh-Low。High-HighとLow-Lowはクラスターの中心(塗りが強い)、High-LowとLow-Highは空間的アウトライヤー(塗りが弱い)。</desc>
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

以下の2つの3×3グリッドは、それ自体で完結した地図ではなく、全体としては値の低い広い地図から切り出した一部です。ここでは地図全体の平均をおよそ3とします。Gi\*もLISAのHigh/Low判定も、「高い/低い」を**地図全体の平均を基準に**判定するのであり、グリッド内の9マスだけで平均を取り直して判定するわけではありません。

この前提のもとで、2つの3×3グリッドを比べます。どちらも中央のマスが目を引きますが、周囲の値が違います。

<svg viewBox="0 0 360 210" width="100%" role="img" aria-labelledby="grid-cmp-title grid-cmp-desc" style="max-width:100%;height:auto">
  <title id="grid-cmp-title">数値グリッドの対比: 空間的アウトライヤーとhot spot</title>
  <desc id="grid-cmp-desc">左のグリッドは中央が20、周囲8マスがすべて2。中央だけが突出して高いが周囲は低い。右のグリッドは中央が12、周囲が10または11。突出した値はないが全体が高い水準でまとまっている。塗りの強さは各グリッド内での値の相対的な高さを表す。</desc>
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

上の2つのグリッドでは、塗りの強さはそれぞれのグリッドの中だけでの値の相対的な高さを表しており、左右のグリッドをまたいで塗りの強さを比較することはできません(値そのものは各マスに数値で書いてあるので、比較するときはその数値を見てください)。塗りの強さは、ライトテーマでは濃く、ダークテーマでは明るく表示されます。

左のグリッドは、中央の20が周囲(すべて2)よりはるかに大きく、明らかに「値が高い」地域です。しかし周囲は低いままなので、Gi\*ではhot spotとして検出されにくくなります。Gi\*は自分と周囲をまとめて見るため、周囲が低いと中心の高さが押し下げられてしまうからです。LISAではこれを **High-Low(空間的アウトライヤー)** として明示的に検出できます。

右のグリッドは、中央の12が周囲(10・11)より突出しているわけではなく、値の差はわずかです。しかし周囲を含めて全体が高い水準でまとまっているため、Gi\*では典型的な **hot spot** になり得ます。

同じ「真ん中が高い」という見た目でも、周囲がどうかによってGi\*の判定は正反対になります。**この対比が本章の核心です。**「値そのものが高い」ことと「高い値が地理的に固まっている」ことは別、という区別を必ず押さえてください。

LISAの視点で同じ2つのグリッドを見直すと、対比がさらにはっきりします。LISAでいう「周囲の平均」は、自分自身を除いた隣接地域だけの平均です。

- 空間的アウトライヤーの例: 中心の自分の値は20。隣接する8地域はすべて2なので、周囲の平均は2。「自分は高い・周囲は低い」の組み合わせなのでHigh-Lowに分類されます
- hot spotの例: 中心の自分の値は12。隣接する8地域(10が4つ、11が4つ)の平均は (10×4+11×4) ÷ 8 = 10.5。中心の12も隣接平均の10.5も、地図全体の平均(約3)と比べればどちらも高い値なので、「自分も高い・周囲も高い」の組み合わせでHigh-Highに分類されます

同じ「中心が高い」という見た目でも、周囲の平均を計算するとLISAの分類はHigh-LowとHigh-Highで正反対になり、Gi\*の判定(hot spotになりにくい/なりやすい)とも対応しています。

### よくある誤解

- 「値が単独で高ければhot spotだ」という誤解: 誤り。周囲が低ければGi\*ではhot spotになりにくく、LISAではHigh-Low(空間的アウトライヤー)になる
- 「LISAとGi\*は同じものを違う名前で呼んでいるだけ」という誤解: 誤り。LISAは4分類、Gi\*はhot spot/cold spot/特徴なしの3分類であり、そもそも分類のカテゴリ数と定義が異なる
- 「SaTScanもLISA・Gi\*と同じく地域ごとに指標を計算する」という誤解: 誤り。SaTScanは地域ごとの指標ではなく、様々な範囲(窓)を候補として比較し、範囲そのものを検出する

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

## Gi\* と LISA の対応表

同じ状況について、Gi\*とLISAがそれぞれ何と呼ぶかを整理します。

| 状況 | Gi\*の判定 | LISAの判定 |
|---|---|---|
| 自分も周囲も高い | hot spot | High-High(クラスターの中心) |
| 自分も周囲も低い | cold spot | Low-Low(クラスターの中心) |
| 自分だけ高い(周囲は低い) | hot spotになりにくい | High-Low(空間的アウトライヤー) |
| 自分だけ低い(周囲は高い) | cold spotになりにくい | Low-High(空間的アウトライヤー) |

上段2行(自分も周囲も高い/低い)ではGi\*とLISAの結論はほぼ一致します。違いが表に出るのは下段2行、つまり自分と周囲の値がずれているときです。Gi\*はこの状況を積極的には拾わない一方、LISAはHigh-Low・Low-Highという名前を与えて明示的に分類します。この表を「LISAはGi\*の上位互換だ」と読むのは誤りで、Gi\*は「塊のまとまり具合」を、LISAは「自分と周囲の関係」を、それぞれ別の切り口で見ているだけです。

## 有意性をどう扱うか — p値と統計量は別の問い

### LISA・Gi\*の有意性の考え方

LISA・Gi\*とも、計算した値がどのくらい極端かを、[章3](ch3-global-moran.md)で扱ったpermutation test(値をシャッフルして偶然の集まり方と比較する)と同じ考え方で検定できます。1つの地域だけでなく地図上の全地域について同時に検定を行うため、偶然でも一部の地域は有意な結果になりやすいという多重比較の問題が生じます。これはLISA・Gi\*に共通する注意点であり、後述するSaTScanの検定方法とも対比できます。

ここまではp値、つまり「有意かどうか」の話でした。しかしLISA・Gi\*の出力はp値だけではなく、検定を経る前の統計量としても読めます。以下ではそれを整理します。

### `Ii` はp値だけではない — Global Moran's Iの分解

[ハンズオン①](../handson/01-map-moran-lisa-gi.md)のStep 4で見た`localmoran()`の戻り値には、局所p値(`Pr(z != E(Ii))`)だけでなく、1列目に`Ii`という列があります。これは局所Moran's I統計量そのもの、つまり検定を経る前の生の値です。

行標準化した重み(`style = "W"`。ハンズオン①が使う設定)のもとでは、次の関係が成り立ちます。

```
mean(Ii) = Global Moran's I
```

つまり`Ii`は「各地域がGlobal Moran's I全体にどれだけ寄与しているか」への分解になっています。Local Indicator of Spatial Association(LISA)という名前が指すのはまさにこの性質(局所統計量の平均が対応するGlobal統計量に一致すること)であり、p値を計算する前の`Ii`自体がLISAの本体です。したがって、有意性検定を経ずに`Ii`をそのまま地図に塗るという選択肢もあります。

### 生の `Ii` は地域間で比べられない

ただし`Ii`をそのまま比べてよいわけではありません。`localmoran()`の出力では`Ii`の隣に`E.Ii`(期待値)と`Var.Ii`(分散)が並んでおり、この2つは地域ごとに異なります。

期待値が地域ごとに違う理由は、隣接地域の数が地域ごとに違うから、だけではありません。`E.Ii`の計算には**その地域自身の値**が入っています。`localmoran()`が使う期待値は条件付きランダム化(conditional randomization)のもとでの期待値で、対象地域の値を固定したまま、残りの地域の値だけをシャッフルするという発想に対応します。

そのため、「`Ii`が大きい地域ほど強い」と素朴に読むことはできません。異なる地域どうしを比べたいときは、期待値・分散で標準化した`Z.Ii`(標準化統計量)を見る必要があります。

### LISAは符号だけでは4分類を決められない

`Z.Ii`の符号は、正なら「周囲と似ている」(High-HighまたはLow-Low)、負なら「周囲と逆」(High-LowまたはLow-High)を表します。強さは`Z.Ii`の絶対値に載りますが、**4分類のどれに当たるかは`Z.Ii`だけからは決まりません**。

4分類そのものは、[章3](ch3-global-moran.md)のMoran散布図の象限、つまり「自分の値」と「周囲の平均」がそれぞれ全体平均より上か下かという符号の組み合わせだけで機械的に決まります。この分類自体には有意性も強さも含まれません([ハンズオン①](../handson/01-map-moran-lisa-gi.md)のStep 4で見たB市の例のように、局所p値が大きくてもLISA分類は普通に付きます)。

連続量でLISA地図を描くなら、この2つを重ねる必要があります。**4象限を色相で分け、`Z.Ii`の絶対値を濃淡にする**、という2軸の塗り分けです。これなら閾値を一切切らずに描けます。逆に言うと、よく見る「有意なHigh-Highだけ色を塗り、残りは灰色にする」地図は、連続量を局所p値でマスクした**表示**の一種であって、LISAという手法そのものの出力ではありません。

### Gi\*はもともとz値

Getis-Ord Gi\*は、LISAとは事情が異なります。定義からして標準化されており、`localG()`が返すのはp値ではなくz値そのものです。hot spot解析でよく見る「±1.65・±1.96・±2.58で階級を切った地図」([ハンズオン①](../handson/01-map-moran-lisa-gi.md)のStep 5で使った閾値z≥1.96もこの一例です)は、まさに統計量そのもので議論している形です。

ただし正規近似のもとではz値とp値は1対1で単調に対応するため、Gi\*についてはz値を地図に塗ってもLISAの場合のような情報の追加はありません。得られる利得は「階級分けの閾値を切らずに済む」ことだけです。`Ii`が抱えていた「地域間で直接比べられない」という問題そのものが、Gi\*には最初から無いという違いがここにあります。

### 順位づけには統計量が要る

permutation testの擬似p値には、原理的な下限があります。999回のシャッフルであれば、両側の擬似p値が取りうる最小値は`0.002`で、これより小さい値は出せません。

そのため、「もっとも極端な地域から順に並べる」という操作はp値ではできません。上位の地域がまとめて同じ最小値に張り付いてしまうからです。順位づけをしたいなら`Z.Ii`(あるいはGi\*のz値)を使うしかありません。

多重比較の問題(前節で述べたLISA・Gi\*に共通する注意点)も、統計量を連続的に地図に描けば「何地域が有意だったか」を数えるという操作自体を避けられるという形で緩和はできます。ただし**問題そのものが消えるわけではありません**。多数の地域を同時に検定していることに変わりはなく、統計量で表示を変えても検定の枠組みが変わるわけではないからです。

### それでも統計量だけでは足りない

だからといって、p値をやめて統計量だけを見ればよいわけでもありません。

- `Ii`は**その地域自身の値の外れ具合に強く引きずられます**。自分の値が全体平均から大きく離れていれば、周囲との関係がどうであれ`|Ii|`は大きくなりやすいという性質があります
- 割合を扱うとき、人口の小さい地域では推定値がばらつくという問題([章6](ch6-pitfalls.md)で扱う落とし穴の1つ)が、`Ii`にも`Z.Ii`にも同じように乗ります。統計量に切り替えても、この不安定さから逃れられるわけではありません
- 局所のp値が答えているのは「**その地域の値を固定したうえで、周囲の配置がこれほど偏るのは偶然として起こりうるか**」であって、「その地域の値が高いか」ではありません。この2つは別の問いです

p値は「偶然でもこの配置が起こりうるか」を答え、統計量は「どれくらい強いか」を答えます。どちらか一方でもう一方を置き換えられるものではなく、両方を見る必要があります。

## SaTScan — 発想そのものが異なる

LISAとGi\*は、どちらも「各地域について1つずつ指標を計算し、その地域を分類する」という発想です。SaTScan(spatial scan statistic)はこれとは異なり、**範囲そのものを候補として走査し、もっとも尤度比の高い範囲を選ぶ**という発想を取ります。

具体的には、地図上にさまざまな大きさ・位置の円(窓)を置き、それぞれの窓について「窓の内側の人口あたりの患者数」と「窓の外側の人口あたりの患者数」を比較します。人口から期待される患者数に比べて窓の内側の患者数が多いほど尤度比が大きくなり、この尤度比がもっとも大きい窓を「もっとも異常な範囲(最尤クラスター)」として検出します。SaTScanは空間だけでなく、時間・時空間のクラスターも同じ発想で検出できます。代表的なソフトウェアの名前がそのまま手法名としても使われています。

```
      ○
    ○ ○ ○
  ○ ○ ○ ○ ○
    ○ ○ ○
```

イメージとしては、上のような円(窓)を地図上のあらゆる位置・あらゆる大きさで動かし、「この円の中だけ患者が人口から期待される数より異常に多くないか」を1つずつ調べていく、という探索です。LISA・Gi\*が「あらかじめ決めた地域(二次医療圏や都道府県など)ごとに指標を計算する」のに対し、SaTScanは「地域の境界とは無関係に、円という任意の範囲を候補として動かす」という点で発想の出発点が異なります。

LISA・Gi\*とSaTScanの違いは、出力される形にも表れます。LISA・Gi\*の出力は「地域ごとのラベル」(この地域はHigh-High、あの地域はhot spot、といった具合)ですが、SaTScanの出力は「円などで囲まれた領域」です。多重比較への対処も異なります。LISA・Gi\*は地図上のすべての地域について同時にモンテカルロ検定を行うのに対し、SaTScanは無数の窓を試したうえで選ばれた1つの最尤クラスターについて、観測データを繰り返しシミュレーションするモンテカルロ検定でその有意性を確認します。

なお、本教材ではSaTScanの考え方の紹介にとどめ、実際の操作手順は扱いません。SaTScanはRのパッケージではなく独立したソフトウェアであり、導入と操作の説明だけで独立した教材に相当する分量になるためです。Rハンズオンで扱うのは、`spdep` だけで完結するGlobal Moran's I・LISA・Gi\*と、`CARBayes` によるCAR/BYMです。

## 3手法をどう使い分けるか

ここまでの内容を、実際の分析でどう使い分けるかという視点で整理します。

- **「高い値の塊がどこにあるか、ざっくり掴みたい」** → Gi\*が向いています。hot spot / cold spot / 特徴なしという3分類は解釈しやすく、地図として提示しやすい結果になります
- **「自分の地域が周囲と似ているか、逆に浮いているかまで知りたい」** → LISAが向いています。High-Low・Low-Highという空間的アウトライヤーは、Gi\*だけでは見落とされがちな情報です
- **「地域の境界にとらわれず、患者が異常に多い範囲そのものを知りたい」** → SaTScanが向いています。あらかじめ決めた地域単位の粒度に縛られず、円という任意の範囲で検出します

3手法は競合するものではなく、目的に応じて使い分ける、あるいは組み合わせて使うものです。たとえば地図全体の偏りをGlobal Moran's Iで確認し(章3)、具体的な場所をLISAで特定し、それとは独立にSaTScanでも異常範囲が一致するかを確認する、という使い方もできます。

## 実例: Global から Local への対比

Pradhan P, Iyer HS, Rebbeck TR. *JAMA Netw Open.* 2025;8(10):e2537905 は、米国3,142郡(county)のがん検診データについて、queen contiguityで空間重み行列を定義し、Global Moran's Iで全体としての偏りの有無を確認したうえで、空間的自己相関が認められた場合にLISAへ進んで「具体的にどこに偏りがあるか」を特定する、という手順を取っています。[章3](ch3-global-moran.md)のGlobal Moran's Iだけでは分からなかった「具体的にどこか」を、この章のLISAが補うという構造を、実際の論文の手順として確認できます。地図全体の偏りを1つの数値で確認したあとに、具体的な場所を特定する段階に進むというこの2段構えの流れは、本章冒頭で示した「Global→Local」の関係そのものです。

マンモグラフィ検診では、ほとんどの期間を通じて受診割合が高いクラスターが北東部(メイン、ニューハンプシャー、バーモント、マサチューセッツ)に、低いクラスターが南西部(テキサス、ニューメキシコ、アリゾナ)に現れています。有意性はpermutation testで評価されています(章3で説明した、値の配置を無作為に入れ替えて比較する考え方です)。

### 注意: この論文の High-Low はこの章の High-Low とは意味が違う

ただし、この論文が使っているのは **bivariate LISA** であり、4分類は**2つの時期の間の推移**で定義されています。原著の定義は「(1) 一貫して受診割合が高い郡 (high/high)、(2) 一貫して低い郡 (low/low)、(3) 高から低へ変化した郡 (high/low)、(4) 低から高へ変化した郡 (low/high)」です。

つまり、この論文の high/low は「高から低へ変化した郡」であって、**この章で扱ってきた「自分は高いが周囲は低い」空間的アウトライヤーではありません**。同じ High-Low という表記が、何を2つ並べているか(自分と周囲か、前の時期と後の時期か)によって別の意味になります。論文でLISAの結果を読むときは、まず「何と何の関係を分類しているのか」を方法の記述で確認してください。この章で標準として扱っているのは、自分の値と周囲の値を対比するunivariate LISAのほうです。

## まとめ

- Gi\*は「塊探し」、LISAは「自分と周囲の関係の分類」、SaTScanは「異常な範囲の探索」であり、3手法は問いの立て方が異なる
- LISAはHigh-High / Low-Low / High-Low / Low-Highの4分類を行う。High-High・Low-Lowはクラスターの中心、High-Low・Low-Highは空間的アウトライヤー
- 「値が高い」ことと「hot spotである」ことは別。周囲が低ければ単独の高値はGi\*ではhot spotになりにくく、LISAではHigh-Lowとして検出される
- 「クラスター」は一般名詞であり、hot spot・LISAの分類・SaTScanの検出領域はそれぞれ別の定義に基づく
- LISA・Gi\*はp値だけでなく統計量(`Ii`・`Z.Ii`)としても読める。統計量は強さや順位を、p値は偶然かどうかを教えるという、別々の問いに答えている
- SaTScanはLISA・Gi\*と異なり、範囲そのものを走査して最尤の領域を選ぶ手法であり、出力の形(領域かラベルか)や多重比較への対処も異なる
- 3手法は競合するものではなく、地図全体の偏り(Global Moran's I)→具体的な場所(LISA・Gi\*)→境界にとらわれない異常範囲(SaTScan)という順に、目的に応じて使い分けたり組み合わせたりできる

## 章末クイズ

全問に回答してから、まとめて採点します(一括採点)。12問中10問以上の正解で合格です。不正解だった設問には解説が表示されます。何度でも再挑戦できます。合格記録はこの端末のブラウザ内(localStorage)にのみ保存され、サーバーには送信されません。

<div data-quiz-src="../../assets/data/quiz-ch4.json" data-quiz-gate="ch4"></div>

## 次に読む章

[章5: 説明 — なぜそこに多い?](ch5-explanatory.md)に進みます。
