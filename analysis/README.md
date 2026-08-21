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
ケーススタディ)を書く際に、`sf`・`spdep`・`CARBayes` を実際に `DESCRIPTION` に足して
`renv::snapshot()` し直しました(#18 で `spdep`、#20 で `sf`、#19 で `CARBayes`。
`spatialreg` は CARBayes のみで CAR/BYM が完結したため結局 `Imports` には入っていません)。
**このとき `analysis/.Rprofile` が有効化された
セッション(= `analysis/` を作業ディレクトリにして起動した R)から実行してください。**
`analysis/.Rprofile` は `options(renv.lockfile.version = 1)` を設定しており、これが
無いセッションから `renv::snapshot()` すると既定の lockfile version 2 に戻り、
`analysis/renv.lock` が(パッケージの本数自体は変わらないが)`Hash`/`Requirements` を失って
再び行数が数倍に膨れます(理由は下記『なぜ lockfile version 1 か』を参照)。これは
飾りの注意書きではなく、外すと静かに壊れる設定なので必ず守ってください。

**上の `restore()` の節で勧めている `renv::load("analysis")` は、`snapshot()` の
ためのセッション有効化としては不十分です。** `renv::load()` はライブラリパスを
切り替えるだけで `analysis/.Rprofile` を source しないため、
`options(renv.lockfile.version = 1)` が設定されません。`renv::load("analysis")` を
呼んだだけのセッションで `renv::snapshot()` すると、作業ディレクトリを変えていなくても
version 2 の lockfile に戻ります(2026-08-19、issue #18 で実際に踏みました)。
`snapshot()` するときは `renv::load()` に頼らず、`analysis/` を作業ディレクトリにして
R(`Rscript` 含む)そのものを起動してください。

### `renv::restore()` は Windows でソースビルドに落ちる問題を P3M の日付スナップショットで解決した(issue #19、2026-08-20)

CRAN が Windows 向けのバイナリを配布しているのは、基本的に**各パッケージの最新版だけ**です。
`renv.lock` は執筆時点のバージョンを固定するため、ロックした版が最新でなくなった時点で
バイナリが引けなくなり、`renv::restore()` はソースからのビルドに切り替わります。
実測(2026-08-19): lock が固定していた `vctrs` は 0.6.5 だが、CRAN が R 4.5 向けに配布している
Windows バイナリは 0.7.3 で、0.6.5 はソースビルドの対象になる。

この開発環境では **Rtools45 が導入済みであるにもかかわらず**、その `vctrs` 0.6.5 の
ソースビルドが失敗した。ツールチェーンの問題ではなく、C のコンパイルは最後まで通ったうえで
`** byte-compile and prepare package for lazy loading` の段で
`ERROR: lazy loading failed for package 'vctrs'` になる。

**これは vctrs 固有の問題ではなかった。** issue #17 時点の `renv.lock`(51本)のうち30本が
CRAN 最新とズレており(`ggplot2` 4.0.1→4.0.3、`rlang` 1.1.7→1.3.0 ほか)、全部がソースビルド
対象になっていた。#18 で `spdep` を足して69本に増えた時点でも事情は同じだった。個別の
パッケージを上げても直らない。`renv.lock` に `>=` のような範囲指定は書けない
(lock は常に厳密固定)ため、直すべきはバージョン制約ではなく**リポジトリ**だった。

**なぜ lockfile version 1 か。** `renv.lock` は `Hash`/`Requirements` 付きの正規の
`renv::snapshot()` 産物です(issue #17 レビューで再生成・確認済み)。既定の lockfile
version 2(`RENV_LOCKFILE_VERSION` 未設定)は各パッケージの `Hash` を**書き出さない**仕様
(renv 1.1.0 の設計変更で、`DESCRIPTION` の主要フィールドをそのまま lockfile に埋め込み、
必要なら読む側で再計算する方式に変わったため)なので、`RENV_LOCKFILE_VERSION=1`(圧縮された
旧形式。`renv` が現在も公式にサポートしている切替えオプション)を指定して、`Hash`/
`Requirements` 付きの小さい lockfile を生成しています。**ただし `Hash` の有無は
`renv::restore()` がソースビルドに落ちる根本原因(CRAN が古い版のバイナリを配らないこと)
とは無関係で、フォーマットを直しただけでは restore は直りません。** `Hash` はパッケージが
既に renv のキャッシュに存在するときの高速な参照に使われるだけで、キャッシュに無いものは
結局ソースからビルドされ、上記の `vctrs` と同じ理由で失敗します(直し方は下記の通り)。

**直し方: `renv.lock` の `Repositories` を [Posit Public Package Manager](https://packagemanager.posit.co/) の
日付スナップショットに向けた。** 過去版のバイナリをそのまま配布しているため、厳密固定のまま
バイナリで引ける。採用したのは `https://packagemanager.posit.co/cran/2025-11-01`。

**なぜ 11-01 か。** `sf` 1.0-21 / `spdep` 1.4-1 を据え置ける最も新しい日付だから。この2本は
`poly2nb()` / `mat2listw()` のプロセス終了時クラッシュ(上の「環境」節、および
リポジトリ直下の `CLAUDE.md`)という、リポジトリ全体の回避策設計が依存している挙動を
確認した版であり、版を動かすとこの挙動の再確認が挟まる。実測(2026-08-20):

| 日付 | sf | spdep | CARBayes | ggplot2 |
|---|---|---|---|---|
| **2025-11-01(採用)** | **1.0-21** | **1.4-1** | 6.1.1 | 4.0.0 |
| 2025-11-15 | 1.0-22 | 1.4-1 | 6.1.1 | 4.0.0 |
| 2025-11-22 | 1.0-22 | 1.4-1 | 6.1.1 | 4.0.1 |
| 2025-12-01 | 1.0-23 | 1.4-1 | 6.1.1 | 4.0.1 |

**`sf` 1.0-21 と `ggplot2` 4.0.1 が両立する日付は存在しない。** 11-01 を採ったことで
`ggplot2` は lock 上 4.0.1 → 4.0.0 に下がった(代償については本節末尾を参照)。

**lock の変化: 69本 → 126本。** 増えた57本は `CARBayes` の(推移的な)Imports が重いため
(`mapview`・`leaflet`・`GGally`・`glmnet`・`igraph`・`CARBayesdata`・`MCMCpack` など)。
削除されたパッケージは0本。**版が動いたのは既存69本のうち7本だけ**:
`ggplot2` 4.0.1→4.0.0、`rlang` 1.1.7→1.1.6、`lifecycle` 1.0.5→1.0.4、`fs` 1.6.7→1.6.6、
`xfun` 0.55→0.54、`textshaping` 1.0.3→**1.0.4(上がった)**、`renv` 1.1.6→1.1.5(下記(a)参照)。
`sf` 1.0.21 / `spdep` 1.4.1 は据え置き。126本すべてに `Hash` があり、lockfile version 1
形式(上記「なぜ lockfile version 1 か」の段落参照)は維持している。

**検証結果:**

1. 126本すべてが P3M 2025-11-01 の Windows バイナリ(`bin/windows/contrib/4.5/PACKAGES`)に
   バージョン完全一致で実在する。つまり renv のキャッシュが空の環境でも、ソースビルドは
   1件も発生しない
2. プロジェクトライブラリを空にした状態から `renv::restore()` が完走した。117本をインストール
   (残り9本は `Matrix`・`survival` など R 同梱の base/recommended で既に存在)。
   **ソースビルド0件・エラー0件**、すべて `linked from cache` / `installed binary`
3. `DESCRIPTION` の Imports 11本が復元後に揃うことを `packageVersion()` で確認:
   `rmarkdown` 2.30 / `knitr` 1.50 / `ggplot2` 4.0.0 / `dplyr` 1.1.4 / `ragg` 1.5.0 /
   `systemfonts` 1.3.1 / `digest` 0.6.37 / `jsonlite` 2.0.0 / `spdep` 1.4.1 / `sf` 1.0.21 /
   `CARBayes` 6.1.1

**途中で踏んだ罠(次に lock を触る人のために書いておく):**

**(a) lockfile を日付スナップショットに向けると、renv 自身のブートストラップが壊れうる。**
`analysis/renv/activate.R` の `renv_bootstrap_repos()` は、**lockfile の `Repositories` を
最優先で読む**。`activate.R` は自分が要求する renv の版を先頭で固定している(`version <- "..."`)。
lockfile を 2025-11-01 に向けた時点で、`activate.R` が要求していた renv **1.1.6** はその
スナップショットに存在せず(あるのは **1.1.5**)、**空のプロジェクトライブラリから R を
起動すると renv がロードされる前に落ちた**:

```
# Bootstrapping renv 1.1.6 ---------------------------------------------------
- Downloading renv ... FAILED
h(simpleError(msg, call)) でエラー: failed to download:
All download methods failed
```

**日付スナップショットを採用するときは、renv 自身もそのスナップショットに存在する版へ
揃える必要がある。** `renv::install("renv@1.1.5")` して `renv::activate()` で `activate.R` を
書き直し、`renv::snapshot()` で lock にも反映した。修正後は同じ空ライブラリから

```
# Bootstrapping renv 1.1.5 ---------------------------------------------------
- Downloading renv ... OK
- Installing renv  ... OK
```

となり、restore まで通る。

**(b) `renv::activate()` は「いまロードされている renv の版」で `activate.R` を書く。**
`renv::install("renv@1.1.5")` の直後に同じセッションで `renv::activate()` を呼んでも、
`activate.R` の version は 1.1.6 のままだった(renv 自身が「Restart your R session to use
the new versions」と出す通り)。`Rscript --vanilla` で `.Rprofile` を読ませず、`.libPaths()`
にプロジェクトライブラリを足して `library(renv)` で 1.1.5 をロードしてから
`renv::activate(project = ...)` を呼ぶ必要がある。

**(c) renv 1.1.x のプロジェクトライブラリは `analysis/renv/library/` に無い。** 実体は
`%LOCALAPPDATA%/R/cache/R/renv/library/<プロジェクト名>-<ハッシュ>/windows/R-4.5/x86_64-w64-mingw32/`。
`analysis/renv/library` を消しても何も起きず、`renv::restore()` は「The library is already
synchronized with the lockfile.」と言って**何もせずに成功する**。restore を実測で検証する
ときは、この実体の方を退避すること(消さずに `mv` すれば戻せる)。

**代償: コミット済みの図と `renv.lock` の版が一致しなくなった。** `ggplot2` は lock 上
4.0.1 → 4.0.0 に下がったが、**コミット済みの図はシステムライブラリの `ggplot2` 4.0.1 で
生成されている**(下記「レンダリング自体は renv に依存しない」節の通り、レンダリングは
renv 経由ではなくシステムライブラリで行うため)。つまり `renv.lock` は「`restore()` で
復元できる、厳密固定された組」であって、「コミット済みの成果物を生成した版そのもの」とは
もう一致しない。以前この節は「`renv.lock` は『どのバージョンで生成したか』の記録として
第一に機能する」と書いていたが、11-01 への切り替え後は正確ではないため訂正する。

**レンダリング自体は renv に依存しません。** `scripts/render_handson.R` は
リポジトリのルートから起動するため `analysis/.Rprofile`(renv の自動 activate)を読まず、
システムライブラリのパッケージで動きます。`renv::restore()` が通らない環境でも、
システムライブラリに必要なバージョンが入っていればレンダリングはできます。
`renv.lock` は「`renv::restore()` で再現できる依存関係の組」を記録するものであり、
システムライブラリ(レンダリングに実際使われる版)とは独立に管理されている、という
前提で読んでください。

## 生成済みの md を R 無しで直す場合（例外手順）

`docs/handson/00〜03.md` は生成物であり、`analysis/render_manifest.json` の SHA-256 に
縛られている。R が使えない環境（クラウドセッション）で**地の文だけ**を直す必要が出た
ときに限り、リポジトリルートの `CLAUDE.md`「生成済みの `docs/handson/*.md` を R 無しで
直したくなったときは」の手順（3ファイル同時置換＋マニフェストのハッシュ再計算）に従う
こと。コードチャンク・図・表に関わる変更をこの方法でやってはいけない。次にローカルで
`Rscript scripts/render_handson.R` を回したときに差分が出ないことを必ず確認する。

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
