# analysis/

Rハンズオン(`docs/handson/` に公開される各ページ)の **ソース**を置く R プロジェクトです。
サイトに載る md・図・配布用 `.Rmd` は、このディレクトリの `.Rmd` を
`scripts/render_handson.R` でレンダリングして生成します。CI には R を入れない方針
(リポジトリ直下の `CLAUDE.md` 参照)のため、**レンダリングは常にローカルで行い、
生成物をコミットします**。

## 依存パッケージを揃える(`renv::restore()`)

依存パッケージのバージョンは `analysis/renv.lock` に固定してあります。

```r
# リポジトリのルートから
setwd("analysis")
renv::restore()
```

`renv.lock` は `DESCRIPTION` の `Imports` に書かれたパッケージ(と、その再帰的な依存)
だけを対象にした `explicit` スナップショットです。issue #17 の時点では
`analysis/handson/00-setup.Rmd` 1本と `scripts/render_handson.R` が使うパッケージ
(`rmarkdown`, `knitr`, `ggplot2`, `dplyr`, `ragg`, `digest`, `jsonlite`)のみが対象です。
issue #18〜#20 でハンズオンの中身(地図・Moran's I・LISA・Gi\*・CAR/BYM・MAUP・
ケーススタディ)を書く際に、`sf`・`spdep`・`spatialreg` 等を `DESCRIPTION` に足して
`renv::snapshot()` し直す想定です。

### `renv::restore()` は Windows でソースビルドに落ちる(2026-08-19 時点で未解決)

CRAN が Windows 向けのバイナリを配布しているのは、基本的に**各パッケージの最新版だけ**です。
`renv.lock` は執筆時点のバージョンを固定するため、ロックした版が最新でなくなった時点で
バイナリが引けなくなり、`renv::restore()` はソースからのビルドに切り替わります。
実測(2026-08-19): lock が固定している `vctrs` は 0.6.5 だが、CRAN が R 4.5 向けに配布している
Windows バイナリは 0.7.3 で、0.6.5 はソースビルドの対象になる。

この開発環境では **Rtools45 が導入済みであるにもかかわらず**、その `vctrs` 0.6.5 の
ソースビルドが `lazy loading failed` で失敗した。**原因は未特定**であり、
`renv::restore()` がこの環境で完走することは確認できていない。

**レンダリング自体は renv に依存しません。** `scripts/render_handson.R` は
リポジトリのルートから起動するため `analysis/.Rprofile`(renv の自動 activate)を読まず、
システムライブラリのパッケージで動きます。`renv::restore()` が通らない環境でも、
`renv.lock` に記録されたのと同じバージョンがシステムライブラリに入っていれば
レンダリングはできます。`renv.lock` は「どのバージョンで生成したか」の記録として
第一に機能します。

## レンダリングの実行方法

**リポジトリのルートから**実行します(`analysis/` の中からではありません)。

```bash
Rscript scripts/render_handson.R              # analysis/handson/*.Rmd を全部
Rscript scripts/render_handson.R 00-setup      # 1本だけ(拡張子なしのファイル名)
```

このスクリプトが行うこと:

1. `analysis/handson/<name>.Rmd` を `knit_root_dir` = リポジトリのルートとして
   `rmarkdown::render(output_format = "md_document")` でレンダリングする(Rmd 側は
   `data/simulated/toy10_areas.csv` のようにルート相対でデータを読める)
2. 生成した md を `docs/handson/<name>.md` に、図を
   `docs/handson/figures/<name>-*.png` に書く(図の device は `ragg_png`。Windows で
   日本語が化けないようにするため)
3. `.Rmd` ソースを `docs/handson/rmd/<name>.Rmd` にコピーする(サイトの各ページから
   ダウンロードできるようにするため)
4. 生成した md の末尾に、その `.Rmd` コピーへのダウンロードリンクを自動で付け足す
5. `analysis/render_manifest.json` に、レンダリングした各ファイルの SHA-256 を書く
   (`scripts/check_handson_fresh.py` が R を実行せずに生成物の鮮度を検査するための
   入力。詳細はリポジトリ直下の `CLAUDE.md` とそのスクリプト自身のコメントを参照)

### 新しい `.Rmd` を書くときの注意(図のチャンク)

図を出すチャンクには **`fig.alt` を付けてください**(付けないと生成ページの `<img>`
の `alt` が空になり、教材として望ましくありません)。図の内容を、図を見られない
読者にも伝わるように日本語で書いてください(`analysis/handson/00-setup.Rmd` の
`toy10-rate` チャンクが実例です)。

**`fig.cap` は付けないでください。** `fig.cap` を付けると knitr/pandoc が画像を
`<div class="figure">...</div>` ごと生の HTML として出力し、`fig.alt` 用の後処理
(下記)の変換対象が `<img>` 単体より広がってしまうため、今のところスコープ外に
しています。キャプションを付けたい場合は、画像の直後に地の文として書いてください。

`fig.alt` を付けると、knitr/pandoc はその画像を生の HTML(`<img ... alt="..."
src="..." ... />`)として出力します。MkDocs はディレクトリURL
(`docs/handson/00-setup.md` → `site/handson/00-setup/index.html`)を使っているため、
ページの深さに応じた相対パスの書き換えが必要ですが、これは通常の Markdown 画像記法
(`![alt](path)`)にしか効きません。そのため `scripts/render_handson.R` は、
図パスの書き換えを行う前に、生の HTML `<img>` を `![alt](path)` の Markdown
画像記法に**後処理で変換**しています(属性の順序には依存しない実装。実測で
確認済み)。この変換のおかげで `fig.alt` は安全に使えますが、`fig.cap` は
上記の理由でこの変換の対象にしていません。

## 個別の `.Rmd` を自分で knit する場合

各ハンズオンページ末尾から `.Rmd` をダウンロードして手元で実行する読者向けに、
`00-setup.Rmd` 本文にも同じ手順を書いています。**作業ディレクトリをリポジトリの
ルートにすること**(`data/simulated/...` のようなルート相対パスでデータを読む
前提のため)。

## この R プロジェクトが避けていること(既知の罠)

リポジトリ直下の `CLAUDE.md`(「環境」節)に記載の通り、この開発環境では
`spdep::poly2nb()` と `spdep::mat2listw()` を呼ぶと R プロセスが終了時に異常終了
します。`00-setup.Rmd` は空間統計を一切扱わないため無関係ですが、issue #18 以降で
これらの関数を使うハンズオンを書く際は、`scripts/build_geo.R` /
`scripts/verify_simulation.R` の回避策(子プロセスへの切り出し、または `nb` を
エッジ一覧から直接組み立てる)を踏襲してください。
