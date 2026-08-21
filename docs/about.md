# このサイトについて

## 教材の目的

本サイトは、疫学の素養がある読者を対象に、「地図を描くこと」と「空間統計を行うこと」を明確に区別しながら空間疫学(地理疫学)の考え方を学べる教材を提供することを目的としています。概念パート(全6章、クイズ付き)と、R で手を動かして再現するハンズオン(環境準備を含めて4ページ、本編3本)の2部構成です。あわせて、ハンズオンが使う実データの制約をまとめた[ケーススタディ資料](handson/04-case-study.md)を置いています。

## 出典

- 教材の骨格・概念構成は本リポジトリの `documents/要件定義書.md` および `documents/カリキュラム設計.md` に基づきます。
- ケーススタディで扱う専門医の地域分布データは、日本感染症学会が公開する専門医名簿(2026-07-01版)を出典とします。名簿は公開データですが、教材で扱うのは地域単位に集計した人数・率のみであり、個人を特定した分析結果は公開しません。
- 境界データ(地図のポリゴン)の入手元・処理方針は隣接リポジトリ [visualize-regional-medical-care-for-2040](https://github.com/youkiti/visualize-regional-medical-care-for-2040) の整理を参考にしています。

## クイズエンジンについて

本サイトのクイズ機能は、同一著者による [ai-kotohajime](https://github.com/youkiti/ai-kotohajime)(生成AI活用FDサイト)の静的 JS クイズエンジンを移植したものです。ブラウザ内で完結し、採点結果を外部に送信しない設計を踏襲しています。

## ライセンス

対象ごとに2つのライセンスを使い分けています。

| 対象 | ライセンス |
|---|---|
| 教材そのもの(本サイトの文章・図・クイズ、リポジトリの `documents/`、`analysis/` の `.Rmd` の地の文とそこから生成される図) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) |
| コード(`scripts/`、`analysis/` の `.Rmd`(コードチャンク)、クイズエンジンの JavaScript、CI 定義) | [MIT License](https://github.com/youkiti/Spatial-epidemiology-training/blob/main/LICENSE-CODE) |
| 外部データに由来するファイル(`data/` の一部) | 各出典の利用条件に従います(上記「出典」および `documents/DATA_SOURCES.md`) |

教材は**営利目的を含めて自由に複製・改変・再配布できます。** 条件はクレジットの表示だけです。表示例:

```
「空間疫学入門」(youkiti 作)を改変して利用。
https://youkiti.github.io/Spatial-epidemiology-training/
CC BY 4.0 https://creativecommons.org/licenses/by/4.0/
```

正本は[リポジトリの LICENSE](https://github.com/youkiti/Spatial-epidemiology-training/blob/main/LICENSE) です。
