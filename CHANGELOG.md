# Changelog

このプロジェクトの変更履歴。形式は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に、バージョン番号は [Semantic Versioning](https://semver.org/lang/ja/) に準拠する。

**注記: このリポジトリはまだタグを1件も打っていない。** 初回リリース `v0.1.0` はまだ存在しないため、これまでの変更はすべて下記の `[Unreleased]` にまとめてある。初回リリースのタグを打つときは、`RELEASE.md` の手順（3.3節）にしたがって `## [Unreleased]` の見出しを `## [0.1.0] - YYYY-MM-DD` に書き換え、新しい空の `## [Unreleased]` をその上に追加すること。

## [Unreleased]

### 追加

- 設計3文書（要件定義書・カリキュラム設計・作問ガイドライン）を正本として整備（PR #21）
- MkDocs Material によるサイト骨格を構築し、GitHub Pages へのデプロイと `mkdocs build --strict` の CI 検査を追加（PR #22）
- クイズエンジン（`storage.js` → `quiz.js` → `progress.js`）を [ai-kotohajime](https://github.com/youkiti/ai-kotohajime) から移植（PR #23）
- 概念パート全6章を執筆し、合成データ生成器（`scripts/simulate_spatial_data.py`）を追加（issue #6, #10〜#15、PR #25）
- データ層を整備: 感染症専門医名簿PDFの取得・抽出、境界データ（国土数値情報 A38）の生成、人口データの取得（issue #7・#8・#4・#5、PR #27）
- 人口データに5歳階級・65歳以上の列を追加し、需要指標による標準化に使えるようにした（issue #28、PR #29）
- 専門医名簿の施設名を医療情報ネット・国土数値情報P04の参照点に突合し、座標割付・二次医療圏割付を行うパイプラインを追加（issue #9、PR #30）
- Rmd レンダリング配管（`analysis/handson/*.Rmd` → `docs/handson/` の md + 図）、`renv.lock`、生成物の鮮度チェック（`check_handson_fresh.py`）を追加（issue #17、PR #31）
- Rハンズオン①「地図 → Global Moran's I → LISA → Gi\*」を追加（issue #18、PR #32）
- Rハンズオン②「CAR / BYM」（`CARBayes` 採用）を追加し、`renv::restore()` を修復（issue #19、PR #36）
- Rハンズオン③「MAUP の実演 — 都道府県 vs 二次医療圏」を追加（issue #20、PR #35）
- リリース手順書（`RELEASE.md`）・変更履歴（`CHANGELOG.md`）・引用情報（`CITATION.cff`）を追加（issue #55）

### 変更

- ライセンスを確定（教材は CC BY 4.0、コードは MIT）し、`LICENSE` / `LICENSE-CODE` / `README.md` / `docs/about.md` を対応させ、利用者向け文書の古い記述（`CARBayes` か `INLA` か未決定、SaTScan の扱い、`renv.lock` と図の版の関係）を更新（PR #43）
- 隣接生成スクリプトの後片付け（issue #40、PR #41）
- ハンズオン③の有意性の記載・本文の食い違い・Gi\* 地図の配色を修正（issue #37〜#39、PR #42）
- ライトモードの本文リンク色を WCAG AA 以上のコントラストに修正（issue #33、PR #34）
- 監査由来の3件に対応: ライセンス表記の確定（issue #46）、CI ゲートの追加整備（issue #48・#52）（PR #56）
- クイズ採点結果の a11y を改善（`role="status"` とフォーカス管理）（issue #50、PR #59）

### 修正

- 外部リンク検査（`external-links.yml`）で lychee がルート相対リンクを解決できず、外部リンクの生存確認に到達する前に失敗していたのを修正（issue #53、PR #57）
- Rハンズオンの全件レンダリングを止めていた `MASS::select` によるマスクを修正（issue #44、PR #58）

### セキュリティ

- データ整備用依存（`requirements-data.txt`）の既知脆弱性3件を解消し、Windows ARM64 環境への対応を追加（issue #45、PR #60）
