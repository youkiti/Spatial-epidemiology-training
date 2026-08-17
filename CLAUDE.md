# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このリポジトリの現状

**まだ何も実装されていない。** 存在するのは [docs/memo.md](docs/memo.md) 1ファイルのみで、git リポジトリですらない（`git init` 未実施）。ビルド・テスト・リントのコマンドは存在しない。「既存コードを読んで合わせる」対象がないので、最初の構造を作るときは下記「未決定事項」をユーザーに確認してから着手すること。

## プロジェクトの目的

**一定の疫学の素養がある読者向けの、空間疫学（地理疫学）教材**。最終形は公開ページで、2つのパートからなる:

1. **概念パート** — 理論・ビジュアル・具体例を*並列に*提示し、クイズを解きながら進む形式。「読んで終わり」ではなく、各概念に理解確認のクイズが紐づく設計が要求されている。
https://github.com/youkiti/ai-kotohajime
このレポジトリの設計思想を輸入してほいい

2. **Rハンズオン（Rmd）** — 同じ概念を R で手を動かして再現する。

### 題材（ケーススタディ）

**感染症専門医の地域偏在の可視化。** データ源は日本感染症学会の専門医名簿 PDF:
https://www.kansensho.or.jp/uploads/files/senmoni/meibo_260701.pdf （2026-07-01 版）

このPDFはリポジトリにまだ無い。取り込む際の注意:

- 名簿は**個人名と所属を含む**が公開データであるため処理することに問題はない。
　レポジトリでは加工過程のコードと出力される図表のみを保持する。
　今後、データにアクセスできなくなったときのため、シミュレーションデータでも動かせるようにする

- 分子（専門医数）だけを地図にしてはいけない — これは教材自身が「15. 落とし穴」で戒めている誤りそのもの。人口（分母）と対にして人口10万対専門医数を出す。医師偏在の文脈では患者側の需要指標（高齢者割合など）での標準化も検討対象。
- PDF は改訂されうる。取得日をファイル名かメタデータに残す。

## 教材の骨格（docs/memo.md より）

[docs/memo.md](docs/memo.md) はユーザーとの対話ログで、**教材のカリキュラム設計そのもの**。新しい章やクイズを作るときはここの構成に従う。要点:

### 3段階の骨格（これが最初に教える型）

| 段階 | 質問 | 手法 |
|---|---|---|
| 1 記述 | どこで多い？ | 率・有病率・標準化率、SIR/SMR、choropleth map |
| 2 パターン | 集まっている？ | Global Moran's I、Local Moran's I (LISA)、Getis-Ord Gi*、spatial scan statistic |
| 3 説明 | なぜそこに多い？ | 通常回帰、spatial regression、CAR / BYM |

### 教材が最重要視している論点

- **「地図を描く」と「空間統計」は別物。** 色を塗っただけでは「本当に集まっている」とは言えない、という区別が教材全体の出発点。
- **Gi\* / LISA / SaTScan の違い。** memo.md の後半（635行目以降）がまるごとこの説明に費やされている＝ユーザーが明示した躓きポイント。Gi\* は「塊探し」、LISA は「自分と周囲の関係の分類」（High-High / Low-Low / High-Low / Low-High）、SaTScan は「異常に患者が多い地理的範囲の探索」。特に **「値が高い」と「hot spot である」は別**（周囲が低ければ単独の高値は High-Low の空間的アウトライヤーであって hot spot ではない）という区別を、必ず具体的な数値グリッドで示すこと。
- **空間重み行列（「隣」の定義）を先に決める。** 普通の統計に無い発想として強調されている。queen contiguity / 距離閾値。
- **5つの落とし穴** — 人口の多さの無視、小地域の少数例による率の不安定、MAUP（Modifiable Areal Unit Problem）、地域レベルの関連を個人の因果と取り違える（生態学的誤謬）、「隣」の定義の事後決定。

### 教材として使う実例論文

- Blazel MM, et al. *JAMA Netw Open.* 2024;7:e2429764 — 高血圧。地図 → Moran's I (0.58, P<.001) → Bayesian CAR Poisson model。**Moran → 空間回帰**まで通す例。
- Pradhan P, Iyer HS, Rebbeck TR. *JAMA Netw Open.* 2025;8:e2537905 — 米国3,142 counties のがん検診。queen contiguity → Global Moran's I → LISA。**Global → Local の対比**を見せる例（マンモ検診 I=0.57→0.10 と経時低下、それでも LISA では Northeast に high-high、Southwest に low-low が残る）。
- 総説4本: Elliott & Wartenberg 2004 (EHP)、Auchincloss et al. 2012 (Annu Rev Public Health)、Beale et al. 2008 (EHP)、Hu et al. 2025 (Front Public Health)。

memo.md の末尾は「架空の10市町村データで ①地図 → ②Moran's I → ③LISA map → ④Gi* map → ⑤CARモデル と順に見せる」構成を提案している。Rハンズオンの雛形はこれに沿わせるのが自然。ただし**最終的な題材は架空データではなく感染症専門医名簿**なので、架空データは概念導入用、実データはケーススタディ用、と役割を分けるか統一するかはユーザーに確認する。

## 環境（検証済み・2026-08-18）

| ツール | バージョン |
|---|---|
| R | 4.5.2 |
| Quarto | 1.8.26 |
| Pandoc | 3.8.3 |
| Node / npm | 22.21.0 / 10.9.4 |
| Python | 3.11.9 |

R パッケージのインストール状況:

- **導入済み**: `sf` 1.0.21, `spdep` 1.4.1, `spatialreg` 1.4.2, `ggplot2` 4.0.1, `dplyr` 1.1.4, `rmarkdown` 2.30, `knitr` 1.50
- **未導入**（この教材で必要になりうる）: `tmap`, `sfdep`, `leaflet`, `SpatialEpi`, `CARBayes`, `INLA`, `jpndistrict`, `NipponMap`

Global/Local Moran's I と Gi\* は `spdep` だけで完結する（`moran.test` / `localmoran` / `localG`）ので、段階1〜2 は追加インストールなしで書ける。CAR/BYM（段階3）に進む時点で `CARBayes` か `INLA` の選択が必要になる。**`INLA` は CRAN ではなく専用リポジトリからの導入**で、教材の読者に要求するハードルが `CARBayes` より高い点に注意。

※最終的にレポジトリにrequirementは入れる

Rmd のレンダリング確認:

```bash
Rscript -e 'rmarkdown::render("path/to/file.Rmd")'
```

## 未決定事項（実装前にユーザーに確認する）

1. **公開ページの実装手段。** Quarto が入っているので Quarto Website が第一候補（Rmd ハンズオンと概念パートを同一プロジェクトで扱え、`quarto render` 一発になる）だが、クイズのインタラクティブ性（採点・即時フィードバック）をどこまで求めるかで変わる。Quarto + 自前JS か、別の静的サイトか。
github pagesを使う　
https://github.com/youkiti/ai-kotohajime　の思想を輸入

2. **公開先。** GitHub Pages を想定するなら `git init` → GitHub リポジトリ作成が先。`prep-claude-cloud` スキルがこの整備を担当できる。
3. **地域単位。** 都道府県（47）か二次医療圏（約330）か市区町村か。MAUP の教材でもあるので、複数単位で結果が変わることを見せる構成もありうる。
2次医療圏をメイン、都道府県でもやってみよう

4. **境界データ（ポリゴン）の入手元。** 国土数値情報 / e-Stat（統計GIS）など。ライセンス表示の要否とファイルサイズ（リポジトリに直接置くか、取得スクリプトにするか）を決める。
https://github.com/youkiti/visualize-regional-medical-care-for-2040
ここに地図を作ったときの資料があるから、病院の住所も含めて参照して


5. **言語。** memo.md は日本語。公開ページも日本語で書く前提でよいか。
はい

## 執筆上の注意

- memo.md 中の統計値・論文情報は対話ログ由来で、**一次資料での裏取りが済んでいない**。
これは執筆の際にちゃんとsonnet使って確認して
公開ページに載せる数値（Moran's I の値、prevalence ratio、論文の書誌情報など）は原著で確認すること。`verify-slide-citations` スキルが引用検証に使える。
- 読者は疫学の素養がある前提。率・標準化・交絡の基礎説明は省いてよいが、**空間統計に固有の概念**（空間自己相関、空間重み行列、MAUP、空間的アウトライヤー）は丁寧に扱う。
