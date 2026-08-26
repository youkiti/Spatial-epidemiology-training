# 参考文献

このページは、本教材が土台にした文献の一覧です。**書誌はすべて一次資料(PubMed / PubMed Central)で確認済み**です。確認した内容と原著の該当箇所は、リポジトリの `documents/引用検証.md` に記録してあります。

## 最初に読む総説

空間疫学という分野の全体像をつかむには、次の4本が入り口になります。

1. Elliott P, Wartenberg D. Spatial epidemiology: current approaches and future challenges. *Environ Health Perspect.* 2004;112(9):998-1006.

    DOI: [10.1289/ehp.6735](https://doi.org/10.1289/ehp.6735) / PMID: [15198920](https://pubmed.ncbi.nlm.nih.gov/15198920/)

    空間疫学を、人口統計・環境・行動・社会経済・遺伝・感染性のリスク要因に関して疾病の地理的変動を記述し分析する分野と位置づけ、small-area analysis(disease mapping・geographic correlation studies・disease clusters・clustering)に焦点を当てた総説です。小地域では疾病割合に占める偶然の変動成分が大きくなりうることや、疾病クラスターの報告がしばしば非系統的に生じることを指摘しています。

    本教材との対応: [章1: 記述](concepts/ch1-descriptive.md)、[章6: 初学者が注意する5つの落とし穴](concepts/ch6-pitfalls.md)(特に小地域の少数例による推定値の不安定さ)。

2. Auchincloss AH, Gebreab SY, Mair C, Diez Roux AV. A review of spatial methods in epidemiology, 2000-2010. *Annu Rev Public Health.* 2012;33:107-122.

    DOI: [10.1146/annurev-publhealth-031811-124655](https://doi.org/10.1146/annurev-publhealth-031811-124655) / PMID: [22429160](https://pubmed.ncbi.nlm.nih.gov/22429160/)

    疫学専門誌7誌の2000〜2010年の研究のうち、主解析に空間解析手法を用いた207件をレビューしています。distance calculations・spatial aggregation・clustering・spatial smoothing and interpolation・spatial regression が多く用いられ、なかでも近接性の指標(proximity measures)が最も多く、主に大気質・気候科学・資源へのアクセスの研究に適用されていました。

    本教材との対応: 教材全体の手法の見取り図(3段階の型と対応づけて読めます)。

3. Beale L, Abellan JJ, Hodgson S, Jarup L. Methodologic issues and approaches to spatial epidemiology. *Environ Health Perspect.* 2008;116(8):1105-1110.

    DOI: [10.1289/ehp.10816](https://doi.org/10.1289/ehp.10816) / PMID: [18709139](https://pubmed.ncbi.nlm.nih.gov/18709139/)

    空間疫学は疫学・統計学・地理情報科学の手法を組み合わせる必要があると述べ、リスク地図の平滑化・空間モデルへの時間次元の導入・個人レベルと地域レベルの情報の統合を統計的な進展として挙げています。地理情報科学由来の技術による不確実性の可視化にも触れています。

    本教材との対応: [章1: 記述](concepts/ch1-descriptive.md)、[章5: 説明](concepts/ch5-explanatory.md)。

4. Hu K, Li C, Yang X, Ou S, Zhang X, Xiao D, Yu M. From infectious diseases to chronic diseases: the paradigm shift of spatial epidemiology in disease prevention and control. *Front Public Health.* 2025;13:1698964.

    DOI: [10.3389/fpubh.2025.1698964](https://doi.org/10.3389/fpubh.2025.1698964) / PMID: [41164843](https://pubmed.ncbi.nlm.nih.gov/41164843/)

    空間疫学が感染症対策から慢性疾患管理へパラダイムシフトしてきたことを総説し、感染症(マラリア・HIV)と慢性疾患(がん・心血管疾患)の双方について、疾病の空間分布パターンの同定・環境曝露の評価・健康政策の意思決定支援における役割を扱っています。マルチスケール解析・データの集約・Modifiable Areal Unit Problem(MAUP)が結果に与える影響にも触れています。

    本教材との対応: [章6: 初学者が注意する5つの落とし穴](concepts/ch6-pitfalls.md)(特にMAUP)。

## 実例として引用している論文

次の2本は、本教材が具体的な分析手順の実例として本文中で参照している論文です。統計値は各章の本文にすでに掲載しているため、ここでは書誌と読むときの注意にとどめます。

1. Blazel MM, Perzynski AT, Gunsalus PR, Mourany L, Gunzler DD, Jones RW, Pfoh ER, Dalton JE. Neighborhood-Level Disparities in Hypertension Prevalence and Treatment Among Middle-Aged Adults. *JAMA Netw Open.* 2024;7(8):e2429764.

    DOI: [10.1001/jamanetworkopen.2024.29764](https://doi.org/10.1001/jamanetworkopen.2024.29764) / PMID: [39177999](https://pubmed.ncbi.nlm.nih.gov/39177999/)

    [章5: 説明](concepts/ch5-explanatory.md)で、地図による記述 → Moran's I による確認 → Bayesian CAR Poisson モデルによる説明という一連の流れの実例として使っています。

    **読むときの注意**: この論文は隣接(空間重み行列)の定義を明示していません。「neighboring block groups」の空間相関を CAR で考慮した、という記述にとどまり、queen contiguity などの具体的な定義は本文中に現れません。**「queen contiguity を使った」と書いてはいけません**(それは Pradhan 2025 の側の記述です)。査読を通った論文でも隣接の定義が明示されないことがある例として、[章6](concepts/ch6-pitfalls.md)の落とし穴「『隣』の定義」とあわせて読めます。

2. Pradhan P, Iyer HS, Rebbeck TR. Geographic and Temporal Patterns of Screening for Breast, Cervical, and Colorectal Cancer in the US, 1997-2019. *JAMA Netw Open.* 2025;8(10):e2537905.

    DOI: [10.1001/jamanetworkopen.2025.37905](https://doi.org/10.1001/jamanetworkopen.2025.37905) / PMID: [41105409](https://pubmed.ncbi.nlm.nih.gov/41105409/)

    [章3: Global Moran's I](concepts/ch3-global-moran.md)と[章4: LISA / Gi\* / SaTScan の違い](concepts/ch4-lisa-gi-satscan.md)で、queen contiguity → Global Moran's I → LISA という手順の実例として使っています。

    **読むときの注意**: この論文の LISA は **bivariate LISA** です。high/high・high/low などの4分類は「自分と周囲の関係」ではなく、**2つの時点間の推移**(一貫して高い/一貫して低い/高から低へ変化した/低から高へ変化した)を意味します。[章4](concepts/ch4-lisa-gi-satscan.md)が教えている univariate LISA の4分類(自分の値と周囲の値の組み合わせ)とは語義が異なるため、混同しないでください。

## データ・ソフトウェアの出典について

ケーススタディで使うデータや境界データ、クイズエンジンなどソフトウェアの出典は、このページでは扱いません。[このサイトについて](about.md)の「出典」節を参照してください。
