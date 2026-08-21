# ハンズオン⓪: 環境準備と進め方

このページは、①〜③のRハンズオン共通の**環境準備と実行方法**をまとめたものです。空間統計そのものの説明はここでは行いません(章1〜6、および①〜③の本編を参照してください)。

## 必要な環境

- R 4.5 系
- パッケージ管理は [renv](https://rstudio.github.io/renv/) を使います。バージョンは `analysis/renv.lock` に固定してあります

## 依存パッケージを揃える

**R を `analysis/` を作業ディレクトリにして起動してください**(RStudio なら `analysis/` を プロジェクトとして開く。ターミナルから起動する場合は `cd` で `analysis/` に入ってから `R` を起動する)。この状態で起動すると `analysis/.Rprofile` が自動で読み込まれ、renv が このプロジェクト専用のライブラリを有効化します。有効化できたら `renv::restore()` を 実行してください。

``` r
renv::restore()
```

`renv.lock` に記録されたバージョンのパッケージが、このプロジェクト専用のライブラリにインストールされます(システムのライブラリやほかのRプロジェクトには影響しません)。**`setwd("analysis")` してから `renv::restore()` を呼ぶだけでは不十分です**(`setwd()` は `analysis/.Rprofile` を読み込まないため renv が有効化されず、`renv::restore()` はシステムのライブラリに直接インストールしてしまいます)。**R の起動時に `analysis/` が作業ディレクトリになっている必要があります。**

この有効化は R セッションの状態として保持されるので、次の節で作業ディレクトリをリポジトリのルートに `setwd()` し直しても解除されません。

**`renv.lock` は「`renv::restore()` で復元できる依存関係の組」の記録であって、このサイトに載っている図を生成した環境の記録ではありません。** サイトの図はレンダリング時のシステムライブラリ(`ggplot2` 4.0.1)で描かれており、`renv.lock` が固定するのは `ggplot2` 4.0.0 です(`sf` 1.0-21 を据え置ける最も新しい日付スナップショットに合わせた結果で、経緯は `analysis/README.md` に記録しています)。そのため `renv::restore()` した環境で knit すると、図の見た目が細部でこのサイトと違うことがあります。一方、**統計量そのものは一致します** — 計算に使う `sf` 1.0-21 / `spdep` 1.4-1 / `CARBayes` 6.1.1 は、`renv.lock` とレンダリングに使ったシステムライブラリとで同じ版だからです。

## `.Rmd` をダウンロードして自分で実行する

各ハンズオンページの末尾に、そのページのもとになった `.Rmd` へのリンクがあります。ダウンロードしたら、**作業ディレクトリをリポジトリのルートに設定してから** knit してください。

``` r
setwd("path/to/Spatial-epidemiology-training")  # リポジトリのルート
rmarkdown::render("analysis/handson/00-setup.Rmd")
```

ハンズオン内のコードは `data/simulated/toy10_areas.csv` のようにリポジトリのルートから見た相対パスでデータを読みます。作業ディレクトリがルートからずれると、データの読み込みでエラーになります。

## 動作確認: 架空10市町村データを読む

環境が整っているか確認するために、架空の10市町村データ(`data/simulated/toy10_areas.csv`)を読み込み、人口10万対罹患率を横棒グラフにします。このデータは①〜③のハンズオンでも共通して使う、教材の概念パートに登場する架空データです。

``` r
library(dplyr)

toy10 <- read.csv("data/simulated/toy10_areas.csv", fileEncoding = "UTF-8")

toy10 <- toy10 |>
  mutate(area_name = factor(area_name, levels = area_name[order(rate_per_100k)]))

ggplot(toy10, aes(x = area_name, y = rate_per_100k)) +
  geom_col(fill = "#2b6cb0") +
  coord_flip() +
  labs(
    title = "架空10市町村の人口10万対罹患率",
    x = "市町村",
    y = "人口10万対罹患率"
  )
```

![架空10市町村の人口10万対罹患率の横棒グラフ。B市が人口10万対300で最も高く、A市・D市・F市・G市・J市は人口10万対100で並んで最も低い。](figures/00-setup-toy10-rate-1.png)

この図が日本語のラベル込みで表示されていれば、環境準備は完了です。図の日本語フォントはOSに応じて自動選択しますが(Windows: Meiryo、macOS: Hiragino Sans、それ以外: Noto Sans CJK JP)、手元の環境にそのフォントが無く文字が豆腐(□)になる場合は、上の setup チャンクの `base_family` を手元にインストールされている日本語フォント名に書き換えてください。

**注意**: このページは choropleth map(地図)を描きません。地図と Moran's I・LISA・Gi\* は①のハンズオンで扱います。

## 次に進む

- [①地図→Moran's I→LISA→Gi\*](01-map-moran-lisa-gi.md)

---

このページのソース: [00-setup.Rmd をダウンロード](rmd/00-setup.Rmd)
