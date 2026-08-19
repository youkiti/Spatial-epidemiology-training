# analysis/

Rハンズオン(`docs/handson/` に公開される各ページ)の **ソース**を置く R プロジェクトです。
サイトに載る md・図・配布用 `.Rmd` は、このディレクトリの `.Rmd` を
`scripts/render_handson.R` でレンダリングして生成します。CI には R を入れない方針
(リポジトリ直下の `CLAUDE.md` 参照)のため、**レンダリングは常にローカルで行い、
生成物をコミットします**。

## 依存パッケージを揃える(`renv::restore()`)

依存パッケージのバージョンは `analysis/renv.lock` に固定してあります。

```r
# リポジトリのどこから呼んでもよい(setwd() は不要)
renv::load("analysis")
renv::restore()
```

**`setwd("analysis")` してから `renv::restore()` を呼ぶだけでは不十分です。** `setwd()` は
`analysis/.Rprofile`(renv の自動有効化スクリプト)を読み込まないため renv が有効化されず、
`renv::restore()` は `.libPaths()` に残ったシステムのライブラリへ直接インストールしてしまいます
(このプロジェクト専用のライブラリではなく、マシン上の他のRプロジェクトにも影響する版が
書き換わります)。**`renv::restore(project = "analysis")` も同じ理由で不十分です**——
`restore()` は `library` 引数が省略されたとき現在のセッションの `.libPaths()` をそのまま使う
(`project` はロックファイルの場所を特定するためだけに使われ、ライブラリの決定には使われない)
ため、有効化していないセッションから呼ぶとやはりシステムのライブラリにインストールされます
(実測で確認済み: `renv:::renv_libpaths_resolve(NULL)[1]` は有効化前後で
`C:/Users/.../win-library/4.5` → `.../renv/library/analysis-.../...` のように変わり、
`renv::restore(project = "analysis")` を呼ぶ**前**の時点でこれが `restore()` の使う値になる)。
上記のように先に `renv::load("analysis")` を呼んで有効化してから `renv::restore()` を
実行すれば、作業ディレクトリを変えずに正しいプロジェクト専用ライブラリへインストールされます。

`renv.lock` は `DESCRIPTION` の `Imports` に書かれたパッケージ(と、その再帰的な依存)
だけを対象にした `explicit` スナップショットです。issue #17 の時点では
`analysis/handson/00-setup.Rmd` 1本と `scripts/render_handson.R` が使うパッケージ
(`rmarkdown`, `knitr`, `ggplot2`, `dplyr`, `ragg`, `digest`, `jsonlite`)のみが対象です。
issue #18〜#20 でハンズオンの中身(地図・Moran's I・LISA・Gi\*・CAR/BYM・MAUP・
ケーススタディ)を書く際に、`sf`・`spdep`・`spatialreg` 等を `DESCRIPTION` に足して
`renv::snapshot()` し直す想定です。**このとき `analysis/.Rprofile` が有効化された
セッション(= `analysis/` を作業ディレクトリにして起動した R)から実行してください。**
`analysis/.Rprofile` は `options(renv.lockfile.version = 1)` を設定しており、これが
無いセッションから `renv::snapshot()` すると既定の lockfile version 2 に戻り、
`analysis/renv.lock` が(51本→変わらないが)`Hash`/`Requirements` を失って
再び1,950行前後まで膨れる(下記参照)。これは飾りの注意書きではなく、外すと
静かに壊れる設定なので必ず守ってください。

**上の `restore()` の節で勧めている `renv::load("analysis")` は、`snapshot()` の
ためのセッション有効化としては不十分です。** `renv::load()` はライブラリパスを
切り替えるだけで `analysis/.Rprofile` を source しないため、
`options(renv.lockfile.version = 1)` が設定されません。`renv::load("analysis")` を
呼んだだけのセッションで `renv::snapshot()` すると、作業ディレクトリを変えていなくても
version 2 の lockfile に戻ります(2026-08-19、issue #18 で実際に踏みました)。
`snapshot()` するときは `renv::load()` に頼らず、`analysis/` を作業ディレクトリにして
R(`Rscript` 含む)そのものを起動してください。

### `renv::restore()` は Windows でソースビルドに落ちる(2026-08-19 時点で未解決)

CRAN が Windows 向けのバイナリを配布しているのは、基本的に**各パッケージの最新版だけ**です。
`renv.lock` は執筆時点のバージョンを固定するため、ロックした版が最新でなくなった時点で
バイナリが引けなくなり、`renv::restore()` はソースからのビルドに切り替わります。
実測(2026-08-19): lock が固定している `vctrs` は 0.6.5 だが、CRAN が R 4.5 向けに配布している
Windows バイナリは 0.7.3 で、0.6.5 はソースビルドの対象になる。

この開発環境では **Rtools45 が導入済みであるにもかかわらず**、その `vctrs` 0.6.5 の
ソースビルドが失敗した。ツールチェーンの問題ではなく、C のコンパイルは最後まで通ったうえで
`** byte-compile and prepare package for lazy loading` の段で
`ERROR: lazy loading failed for package 'vctrs'` になる。

**これは vctrs 固有の問題ではない。** `renv.lock` の51本中30本が CRAN 最新とズレており
(`ggplot2` 4.0.1→4.0.3、`rlang` 1.1.7→1.3.0 ほか)、全部がソースビルド対象になる。
個別のパッケージを上げても直らない。

**`renv.lock` は `Hash`/`Requirements` 付きの正規の `renv::snapshot()` 産物である
(issue #17 レビューで再生成・確認済み)。** `renv::hydrate()` でシステムライブラリの
実体をプロジェクトライブラリへリンクし、`renv::snapshot(type = "explicit")` で書き直しても
パッケージの集合・バージョンは(51本とも)一致し、版のズレは無かった。ただし既定の
lockfile version 2(`RENV_LOCKFILE_VERSION` 未設定)は各パッケージの `Hash` を
**書き出さない**仕様であることが分かった(renv 1.1.0 の変更で、`DESCRIPTION` の主要フィールドを
そのまま lockfile に埋め込み、必要なら読む側で再計算する設計に変わったため)。CRAN 由来
(`Repository` ソース)のレコードはこの再計算対象からも外れるため、version 2 のままでは
実質的に `Hash` を持てない。`RENV_LOCKFILE_VERSION=1`(圧縮された旧形式。`renv` が現在も
公式にサポートしている切替えオプション)を指定して同じ手順で再生成すると、51本すべてに
`Hash`(と該当する場合は `Requirements`)が入った、行数も1/3程度に小さい lockfile が
得られたため、これを採用した。**ただし `Hash` の有無は `renv::restore()` が
ソースビルドに落ちる根本原因(CRAN が古い版のバイナリを配らない)とは無関係で、
このフォーマット変更だけでは restore は直らない。** `Hash` はパッケージが既に
renv のキャッシュに存在するときの高速な参照に使われるだけで、キャッシュに無いものは
結局ソースからビルドされ、上記の `vctrs` と同じ理由で失敗する。直し方(リポジトリを
日付スナップショットへ切り替える)は次の段落のまま、issue #19 に持ち越す。

**直し方は分かっている（実施は issue #19、2026-08-19 決定）。** `renv.lock` に `>=` のような
範囲指定は書けない(lock は常に厳密固定)ので、直すのはバージョン制約ではなく**リポジトリ**の方。
過去版のバイナリを配る [Posit Public Package Manager](https://packagemanager.posit.co/) の
日付スナップショット(例: `https://packagemanager.posit.co/cran/2025-12-01`)を
`renv.lock` の `Repositories` に指定すれば、厳密固定のままバイナリで引ける。
`CARBayes` を入れて R 環境を触る issue #19 の中でまとめて行う。それまでは
`renv.lock` は「どの版で生成したか」の記録として機能させる。

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

**1本だけレンダリングしたときも、`analysis/render_manifest.json` の他のエントリは
消えません**(既存のマニフェストを読み込んで、指定した Rmd のエントリだけを
上書きする)。マニフェストが「今存在する Rmd と完全に一致」するのは、引数なしで
全部レンダリングしたときだけです(削除した Rmd のエントリはこのときに落ちます)。

このスクリプトが行うこと:

1. `analysis/handson/<name>.Rmd` を `knit_root_dir` = リポジトリのルートとして
   `rmarkdown::render(output_format = "md_document")` でレンダリングする(Rmd 側は
   `data/simulated/toy10_areas.csv` のようにルート相対でデータを読める)
2. 生成した md を `docs/handson/<name>.md` に、図を
   `docs/handson/figures/<name>-<チャンクラベル>-<連番>.png` に書く(図の device は
   `ragg_png`。Windows で日本語が化けないようにするため。`fig.path` を
   `docs/handson/figures/` へ直接向けているため、knitr の既定の出力先
   `<name>_files/figure-*/` へは書き出されない)
3. `.Rmd` ソースを `docs/handson/rmd/<name>.Rmd` にコピーする(サイトの各ページから
   ダウンロードできるようにするため)
4. 生成した md の末尾に、その `.Rmd` コピーへのダウンロードリンクを自動で付け足す
5. `analysis/render_manifest.json` に、レンダリングした各ファイル(と `data_inputs`
   で宣言したデータファイル。下記参照)の SHA-256 を書く(`scripts/check_handson_fresh.py`
   が R を実行せずに生成物の鮮度を検査するための入力。詳細はリポジトリ直下の
   `CLAUDE.md` とそのスクリプト自身のコメントを参照)

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

### 新しい `.Rmd` を書くときの注意(データの入力ファイル)

Rmd が `data/simulated/toy10_areas.csv` のようなリポジトリ内のデータファイルを読む場合、
YAML フロントマターに `data_inputs` としてそのファイルの(リポジトリルートからの)相対パスを
書いてください(`analysis/handson/00-setup.Rmd` が実例です)。

```yaml
---
title: "..."
data_inputs:
  - data/simulated/toy10_areas.csv
---
```

`scripts/render_handson.R` がこれを読み、ファイルの SHA-256 を
`analysis/render_manifest.json` に記録します。`scripts/check_handson_fresh.py` は
このハッシュを実ファイルと照合するため、**Rmd 自体は変えずにデータだけを書き換えて
再レンダリングを忘れた場合**(コードは古いデータのままだが `.Rmd` のハッシュは
一致しているので、Rmd 自体のハッシュ照合では検出できないケース)を検出できます。
省略可能です(データファイルを読まない Rmd は `data_inputs` を書かなくても
問題なく動きます)。

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
