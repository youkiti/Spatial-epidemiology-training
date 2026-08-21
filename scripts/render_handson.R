#!/usr/bin/env Rscript
# -*- coding: utf-8 -*-
#
# render_handson.R — analysis/handson/*.Rmd を docs/handson/ 以下の md + 図に
# レンダリングする(issue #17)。「CI に R を入れない」方針(リポジトリ直下の
# CLAUDE.md)のため、レンダリングは常にローカルで行い、生成物(md・図・配布用
# .Rmd コピー)をリポジトリにコミットする。CI 側は R を実行せず
# scripts/check_handson_fresh.py で生成物の鮮度だけを検査する。
#
# 使い方(必ずリポジトリのルートから実行すること):
#   Rscript scripts/render_handson.R              # analysis/handson/*.Rmd を全部
#   Rscript scripts/render_handson.R 00-setup      # 1本だけ(拡張子なしのファイル名)
#
# 【マニフェストの扱い】引数なし(全件)実行時は analysis/render_manifest.json を
# 「今 analysis/handson/ に存在する Rmd と完全に一致」するよう作り直す(削除された
# Rmd のエントリは落ちる)。引数ありの一部レンダリング時は、既存のマニフェストを
# 読み込み、指定した Rmd のエントリだけを上書きし、他のエントリはそのまま残す
# (レンダリングしていない Rmd のエントリまで消してしまうと、
# scripts/check_handson_fresh.py がそれらを「未レンダリング」「孤児」として
# 誤検出してしまうため)。
#
# 前提: analysis/ を作業ディレクトリにして起動した R セッション(renv が
# 自動有効化される)で renv::restore() 済みであること(手順は analysis/README.md 参照。
# setwd("analysis") してから呼ぶだけでは有効化されないので注意)。
# 通常の(--vanilla でない)Rscript 起動であれば analysis/.Rprofile がなくても
# 問題ない。本スクリプトはリポジトリのルートから起動するため analysis/.Rprofile
# (renv の自動 activate)を読まず、renv を使わずシステムライブラリのパッケージで
# 動く(このレンダリングは renv に依存しない)。analysis/renv.lock は
# 「renv::restore() で再現できる依存関係の組」を記録するものであり、レンダリングに
# 実際使われるシステムライブラリの版とは独立に管理されている(現に ggplot2 は
# lock 上 4.0.0、コミット済みの図を生成したシステムライブラリは 4.0.1 で一致しない)。
# 詳細は analysis/README.md が正本。
#
# 【注意: この環境固有の罠】ragg / systemfonts を読み込んだ R プロセスは、
# 出力自体は最後まで正常に完了するにもかかわらず、プロセス終了時に異常終了する
# (Git Bash 経由で終了コード127)。CLAUDE.md に記載の spdep::mat2listw() /
# spdep::poly2nb() と同種の「終了時クラッシュ」であり、原因は別(ragg 側)だが
# 症状は同じ。したがって本スクリプトの成否を `Rscript scripts/render_handson.R`
# の終了コードで判定してはいけない。本スクリプトは正常終了時に必ず最後の行として
# "RENDER_HANDSON_OK" を標準出力に書く。呼び出し側はこの文字列の有無と、
# 生成物(docs/handson/*.md 等)の存在で成否を確認すること。

suppressPackageStartupMessages({
  library(rmarkdown)
  library(knitr)
  library(digest)
})

repo_root <- getwd()
handson_src_dir <- file.path(repo_root, "analysis", "handson")
docs_handson_dir <- file.path(repo_root, "docs", "handson")
figures_dir <- file.path(docs_handson_dir, "figures")
rmd_copy_dir <- file.path(docs_handson_dir, "rmd")
manifest_path <- file.path(repo_root, "analysis", "render_manifest.json")

if (!dir.exists(handson_src_dir)) {
  stop(
    "analysis/handson/ が見つかりません。リポジトリのルートから実行してください",
    "(現在の作業ディレクトリ: ", repo_root, ")"
  )
}

# analysis/handson/*.Rmd は非再帰的にフラットに並んでいる前提(このスクリプトの
# 他の箇所 — 図の出力先の相対パス計算・マニフェストの構築 — も同じ前提に依存する)。
all_rmd_files <- sort(list.files(handson_src_dir, pattern = "\\.Rmd$", full.names = TRUE))

args <- commandArgs(trailingOnly = TRUE)
is_full_render <- length(args) == 0
if (is_full_render) {
  rmd_files <- all_rmd_files
} else {
  names_requested <- sub("\\.Rmd$", "", args)
  rmd_files <- file.path(handson_src_dir, paste0(names_requested, ".Rmd"))
  missing <- rmd_files[!file.exists(rmd_files)]
  if (length(missing) > 0) {
    stop("指定された Rmd が見つかりません: ", paste(missing, collapse = ", "))
  }
}

if (length(rmd_files) == 0) {
  stop("analysis/handson/ に .Rmd がありません。")
}

dir.create(figures_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(rmd_copy_dir, recursive = TRUE, showWarnings = FALSE)

# --- Rmd 名の衝突チェック ----------------------------------------------------
# 図ファイルは "<name>-<チャンクラベル>-<連番>.png" として figures_dir に
# 直接書き出され、レンダリング後に「figures_dir 内で <name>- から始まるファイル」
# を glob してこの Rmd の所属物だと判定する(下記)。ある Rmd の名前が別の Rmd の
# 名前の接頭辞になっていると("00-setup" と "00-setup-extra" のような組み合わせ)、
# glob が誤って他方の図まで拾ってしまう。analysis/handson/ がフラットな構成である
# 前提と合わせて、レンダリング対象が何であっても常に全件チェックする。
all_names <- sub("\\.Rmd$", "", basename(all_rmd_files))
for (i in seq_along(all_names)) {
  for (j in seq_along(all_names)) {
    if (i != j && startsWith(all_names[j], paste0(all_names[i], "-"))) {
      stop(sprintf(
        paste0(
          "[render_handson] Rmd 名 '%s' が '%s' の接頭辞になっています。",
          "図ファイル名(<name>-<チャンクラベル>-<連番>.png)の接頭辞だけでは",
          "所属する Rmd を一意に判別できなくなるため、どちらかの名前を変えてください。"
        ),
        all_names[i], all_names[j]
      ))
    }
  }
}

# --- ハッシュ計算 -----------------------------------------------------------
# テキストファイル(.Rmd / .md / データCSV)は改行を LF に正規化してからハッシュ
# する。.gitattributes は "* text=auto eol=lf" だが、作業コピーの改行コードは
# 環境によって CRLF になりうる(このリポジトリの CLAUDE.md に既知の罠として記載)。
# scripts/check_handson_fresh.py(Python側)も同じ正規化をする。ここが食い違うと
# CI が永久に赤になるので、正規化ルールを変えるときは両方一緒に直すこと。
normalize_newlines <- function(text) {
  text <- gsub("\r\n", "\n", text, fixed = TRUE)
  gsub("\r", "\n", text, fixed = TRUE)
}

sha256_text_file <- function(path) {
  raw <- readBin(path, what = "raw", n = file.info(path)$size)
  txt <- normalize_newlines(rawToChar(raw))
  digest::digest(txt, algo = "sha256", serialize = FALSE)
}

sha256_binary_file <- function(path) {
  digest::digest(file = path, algo = "sha256")
}

# writeLines(text, path, sep = "\n") は text 自体がすでに改行終端の文字列でも
# 無条件にもう1個 "\n" を足す。この関数はいったん末尾の改行をすべて剥がしてから
# ちょうど1個だけ付け直すことで、呼び出し側が渡す文字列の末尾改行の個数に関係なく
# 出力ファイルの末尾改行を常にちょうど1個にする。
write_text_lf <- function(text, path) {
  text <- sub("\n+$", "", text)
  writeLines(text, path, sep = "\n", useBytes = TRUE)
}

# --- 相対パス計算 ------------------------------------------------------------
# from_dir から to_dir への相対パスを "/" 区切りで返す(共通の祖先までさかのぼり、
# そこから下る)。fig.path の解決に使う(下記参照)。
relative_path <- function(from_dir, to_dir) {
  from_parts <- strsplit(normalizePath(from_dir, winslash = "/", mustWork = TRUE), "/", fixed = TRUE)[[1]]
  to_parts <- strsplit(normalizePath(to_dir, winslash = "/", mustWork = TRUE), "/", fixed = TRUE)[[1]]
  max_common <- min(length(from_parts), length(to_parts))
  common <- 0L
  while (common < max_common && from_parts[common + 1] == to_parts[common + 1]) {
    common <- common + 1L
  }
  ups <- rep("..", length(from_parts) - common)
  downs <- if (common < length(to_parts)) to_parts[(common + 1):length(to_parts)] else character(0)
  paste(c(ups, downs), collapse = "/")
}

to_repo_relative <- function(path) {
  full <- normalizePath(path, winslash = "/", mustWork = TRUE)
  root <- normalizePath(repo_root, winslash = "/", mustWork = TRUE)
  prefix <- paste0(root, "/")
  # sub() は第1引数を正規表現として扱うため、root にドットや+等の正規表現
  # メタ文字が含まれると静かに誤動作しうる(実測上は今のパスに含まれないが、
  # リテラルな前置詞の除去として書く方が安全)。substring() で先頭を切り落とす。
  if (!startsWith(full, prefix)) {
    # normalizePath() はシンボリックリンク・ジャンクション・8.3短縮名を解決する
    # ため、リポジトリの中にあるはずのファイルでもここに来ることがありうる
    # (ジャンクション越しにリポジトリへアクセスしている場合など)。誤って
    # 絶対パスをマニフェストに書いてしまうと、CI 側(REPO_ROOT / rel_path)が
    # 絶対パスを渡された pathlib の挙動で REPO_ROOT を無視し、実在するファイルを
    # 「存在しない」と誤検出する。フォールバックせず、ここで止める。
    stop(sprintf(
      "[render_handson] %s はリポジトリのルート(%s)の外にあります。マニフェストに絶対パスを書けません。",
      full, root
    ))
  }
  substring(full, nchar(prefix) + 1)
}

# --- fig.alt 由来の生HTML <img> を Markdown 画像記法に戻す -------------------
# fig.alt を付けた図チャンクは knitr/pandoc が <img ... alt="..." src="..." ... />
# という生HTMLとして出力する。生HTMLの src は MkDocs のディレクトリURL向け相対
# パス書き換え(下の図の後処理)が効かず、サイト上で画像が壊れる(fig.cap も同様に
# 生HTMLになるが、<div class="figure">...</div> でラップが広がるため fig.cap は
# 引き続きサポート対象外とする)。そのため生HTMLの <img> を後処理で
# Markdown 画像記法 ![alt](src) に戻し、既存のパス書き換えロジック(Markdown /
# 生HTML の区別をせず、パス文字列を md_text 中から探して置換する)がそのまま
# 効くようにする。属性の順序は knitr のバージョンで変わりうるため、順序に
# 依存せず属性ごとに正規表現で取り出す。
#
# 【フェンスコードブロックは変換しない】この変換は文書全体に対して機械的に
# かかるため、Rmd の地の文が(たとえば「生HTMLの <img> はこう書く」という
# 説明のために)```で囲んだコードサンプルとして <img> タグを含んでいる場合、
# それも誤って書き換えてしまう。```/~~~ フェンス(より長いフェンス・info
# string を含む)の内側の行は変換対象から外す。行頭4スペース以上のインデント
# コードブロックは検出コストに見合わないため対象外とする(このリポジトリの
# Rmd では使っていない)。
unescape_html_attr <- function(x) {
  x <- gsub("&quot;", "\"", x, fixed = TRUE)
  x <- gsub("&#39;", "'", x, fixed = TRUE)
  x <- gsub("&lt;", "<", x, fixed = TRUE)
  x <- gsub("&gt;", ">", x, fixed = TRUE)
  x <- gsub("&amp;", "&", x, fixed = TRUE)
  x
}

extract_html_attr <- function(tag, attr) {
  pat <- sprintf('\\b%s\\s*=\\s*"([^"]*)"', attr)
  m <- regmatches(tag, regexpr(pat, tag, perl = TRUE))
  if (length(m) == 0 || !nzchar(m)) return(NA_character_)
  unescape_html_attr(sub(pat, "\\1", m, perl = TRUE))
}

# 各行がフェンスコードブロックの内側(開始行・終了行を含む)かどうかを判定する。
mark_fenced_lines <- function(lines) {
  fence_re <- "^[ \t]{0,3}(`{3,}|~{3,})[ \t]*(.*)$"
  in_fence <- FALSE
  fence_char <- ""
  fence_len <- 0L
  is_fenced <- logical(length(lines))
  for (i in seq_along(lines)) {
    m <- regmatches(lines[i], regexec(fence_re, lines[i]))[[1]]
    has_marker <- length(m) >= 3 && nzchar(m[2])
    if (!in_fence) {
      if (has_marker) {
        in_fence <- TRUE
        fence_char <- substr(m[2], 1, 1)
        fence_len <- nchar(m[2])
        is_fenced[i] <- TRUE
      }
    } else {
      is_fenced[i] <- TRUE
      is_closing <- has_marker && substr(m[2], 1, 1) == fence_char &&
        nchar(m[2]) >= fence_len && !nzchar(trimws(m[3]))
      if (is_closing) in_fence <- FALSE
    }
  }
  is_fenced
}

convert_raw_img_tags <- function(text) {
  if (!grepl("<img", text, fixed = TRUE)) return(text)

  lines <- strsplit(text, "\n", fixed = TRUE)[[1]]
  is_fenced <- mark_fenced_lines(lines)

  convert_line <- function(line) {
    m <- gregexpr("<img\\b[^>]*/?>", line, perl = TRUE)
    tags <- regmatches(line, m)[[1]]
    if (length(tags) == 0) return(line)
    replacements <- vapply(tags, function(tag) {
      src <- extract_html_attr(tag, "src")
      if (is.na(src)) return(tag) # src が無い <img> には手を出さない
      alt <- extract_html_attr(tag, "alt")
      if (is.na(alt)) alt <- ""
      sprintf("![%s](%s)", alt, src)
    }, character(1), USE.NAMES = FALSE)
    regmatches(line, m) <- list(replacements)
    line
  }

  editable <- !is_fenced
  if (any(editable)) {
    lines[editable] <- vapply(lines[editable], convert_line, character(1), USE.NAMES = FALSE)
  }
  paste(lines, collapse = "\n")
}

# --- 図の出力先を fig.path で docs/handson/figures/ に直接向ける -------------
# 【罠】fig.path は rmarkdown::render() を呼ぶ前に knitr::opts_chunk$set() で
# 指定しても効かない。rmarkdown が knit 実行前に
# "<入力ファイル名>_files/figure-<形式>/" という既定の fig.path を内部で
# 再設定してしまうため(実測で確認済み)。
#
# 効くのは、output_format オブジェクト自身の $knitr$opts_chunk に書く方法
# (rmarkdown::md_document() 等が返す rmarkdown_output_format オブジェクトの
# 中身を直接書き換えて render() に渡す)。rmarkdown::output_format() ヘルパは
# 便利だが pandoc 引数が必須(省略するとエラーになる)なので、ここでは
# md_document() の戻り値をそのまま書き換える。
#
# 【もう一つの罠: fig.path の基準ディレクトリ】fig.path が相対パスのとき、
# knitr は knit_root_dir(chunk 実行時の作業ディレクトリ)ではなく、
# 「元の .Rmd が置かれているディレクトリ」を基準にファイルを書き出す(実測で
# 確認済み。knit_root_dir を repo_root にしていても影響しない)。そのため、
# analysis/handson/*.Rmd から docs/handson/figures/ を直接指すには、
# 「analysis/handson/ から docs/handson/figures/ への相対パス」を渡す必要が
# ある。analysis/handson/*.Rmd がフラットな構成である前提を使い、この相対
# パスはループの外で1回だけ計算する。
#
# この仕組みのおかげで、以前バージョンにあった「knitr の既定の場所に書き出させて
# から figures/ へ copy + remove する」処理は丸ごと不要になった(copy/remove の
# 戻り値を見ずに元PNGを消してしまう不具合や、書き換え候補が見つからず無言で
# 何もしない不具合は、この処理自体が無くなったことで解消している)。
fig_dir_token <- relative_path(handson_src_dir, figures_dir)

# --- 既存マニフェストの読み込み ----------------------------------------------
existing_manifest <- list()
if (file.exists(manifest_path)) {
  existing_raw <- tryCatch(
    jsonlite::fromJSON(manifest_path, simplifyVector = FALSE),
    error = function(e) NULL
  )
  if (is.null(existing_raw)) {
    cat("[render_handson] 既存マニフェストの読み込みに失敗しました(壊れたJSON)。空のマニフェストから作り直します。\n")
  } else if (is.null(existing_raw$handson)) {
    cat("[render_handson] 既存マニフェストに 'handson' がありません。空のマニフェストから作り直します。\n")
  } else {
    existing_manifest <- existing_raw$handson
  }
}

# --- 1本の Rmd をレンダリングし、マニフェストのエントリを返す -----------------
render_one_rmd <- function(rmd_path, name) {
  # name をエスケープせずそのまま正規表現(fig_pattern)/glob(下の Sys.glob 呼び出し)に
  # 埋め込んでいる。今の命名(00-setup, 01-map-moran-lisa-gi, ...)には正規表現・glob の
  # メタ文字が含まれないため実害は無いが、メタ文字を含む Rmd 名を付けると壊れうる。
  # 名前の衝突(上の all_names チェック)ほど深刻ではないため、ここでは検査を追加せず
  # 注意書きに留める。
  fig_pattern <- paste0("^", name, "-.+-[0-9]+\\.png$")

  # 既存の生成物(このRmd由来のもの)を先に削除してから作り直す。孤児ファイルが
  # 残らないようにするため(チャンクの削除・チャンクラベル変更などに追従させる)。
  stale_figs <- list.files(figures_dir, pattern = fig_pattern, full.names = TRUE)
  if (length(stale_figs) > 0) file.remove(stale_figs)

  # 【finding 8 対策】<name>_files/ はこの新しいパイプラインでは基本的に
  # 作られないはずだが(fig.path を figures_dir へ直接向けているため)、
  # knitr/rmarkdown のバージョン差やチャンクの書き方次第で既定の fig.path が
  # 復活するケースに備えて必ず掃除する。on.exit はこの関数の呼び出しが正常
  # 終了しても stop() で異常終了しても実行されるため、レンダリング途中で
  # エラーになって処理が止まった場合でも掃除が漏れない(以前のバージョンは
  # ループの終盤にしか掃除処理が無く、途中の stop() でスキップされていた)。
  files_dir <- file.path(docs_handson_dir, paste0(name, "_files"))
  if (dir.exists(files_dir)) unlink(files_dir, recursive = TRUE)
  on.exit({
    if (dir.exists(files_dir)) unlink(files_dir, recursive = TRUE)
  })

  fig_dir_prefix <- paste0(fig_dir_token, "/")
  fig_path_chunk_opt <- paste0(fig_dir_prefix, name, "-")

  fmt <- rmarkdown::md_document(
    variant = "gfm",
    preserve_yaml = FALSE,
    # pandoc の smart typography(直引用符→カーリークォート等の自動置換)を切る。
    # 既定で有効になっており、"Moran's" のような文中の引用符が無断で
    # "Moran’s" に変わってしまう(既存ページは素の直引用符で統一しているため
    # 不整合になる。実測で確認済み)。
    md_extensions = "-smart",
    # 既定(--wrap=auto)だと約72桁で強制改行が入り、地の文の途中で行が
    # 切れる(MkDocs 上の見た目には影響しないが、diff や生成された .md 自体の
    # 可読性が悪い)。折り返さない。
    pandoc_args = c("--wrap=none")
  )
  # dev/dpi は ragg_png を使う(Windows で日本語が化けないようにするため。
  # CLAUDE.md「環境」節)。fig.path と合わせてここで一括指定する。
  fmt$knitr$opts_chunk$fig.path <- fig_path_chunk_opt
  fmt$knitr$opts_chunk$dev <- "ragg_png"
  fmt$knitr$opts_chunk$dpi <- 150

  md_filename <- paste0(name, ".md")
  rendered_path <- rmarkdown::render(
    input = rmd_path,
    output_format = fmt,
    output_file = md_filename,
    output_dir = docs_handson_dir,
    knit_root_dir = repo_root,
    encoding = "UTF-8",
    quiet = TRUE
  )
  md_path <- file.path(docs_handson_dir, md_filename)
  if (!file.exists(md_path)) {
    stop(sprintf("レンダリング後に %s が見つかりません(render() の戻り値: %s)", md_path, rendered_path))
  }

  md_text <- normalize_newlines(rawToChar(readBin(md_path, "raw", n = file.info(md_path)$size)))
  # fig.alt 由来の生HTML <img> を Markdown 記法に戻す。これを図パスの
  # 書き換え(直後のブロック)より先に行うことで、書き換えロジックが
  # Markdown 記法だけを見ればよいようにする。
  md_text <- convert_raw_img_tags(md_text)

  # --- 図参照パスの書き換え ---------------------------------------------------
  # knitr は fig.path に渡した文字列(fig_path_chunk_opt)をそのまま連番付きの
  # ファイル名の接頭辞として使う(<fig_path_chunk_opt><チャンクラベル>-<連番>.png)。
  # md 中の画像参照も同じ文字列がそのまま(絶対パス化されずに)埋め込まれる
  # (実測で確認済み)。生成された図ファイルそれぞれについて、対応する参照が
  # md_text 中に見つかることを確認してから一括で書き換える。1件でも見つからな
  # ければ、knitr/rmarkdown 側の出力形式が想定と変わったということなので、
  # 静かに諦めず stop() する(壊れた画像参照が公開ページに残ることを防ぐ)。
  produced_pngs <- sort(Sys.glob(file.path(figures_dir, paste0(name, "-*.png"))))
  produced_pngs <- produced_pngs[grepl(fig_pattern, basename(produced_pngs))]
  for (p in produced_pngs) {
    old_ref <- paste0(fig_dir_prefix, basename(p))
    if (!grepl(old_ref, md_text, fixed = TRUE)) {
      stop(sprintf(
        paste0(
          "[render_handson] %s: 生成された図 %s への参照が %s 中に見つかりません。",
          "fig.path の解決結果が想定(接頭辞 %s)と異なる可能性があります",
          "(knitr/rmarkdown のバージョン差などで書き換えロジックが追従できていません)。"
        ),
        name, basename(p), md_filename, fig_dir_prefix
      ))
    }
  }
  md_text <- gsub(fig_dir_prefix, "figures/", md_text, fixed = TRUE)

  # --- data_inputs (issue #17 レビュー対応): この Rmd が読むデータファイルの
  # ハッシュをマニフェストに記録する。Rmd の YAML フロントマターに
  # data_inputs: [相対パス, ...] を書いてもらう(analysis/README.md 参照)。
  # 書かなくてもよい(空なら何も記録しない)。
  front_matter <- tryCatch(
    rmarkdown::yaml_front_matter(rmd_path, encoding = "UTF-8"),
    error = function(e) list()
  )
  data_input_rel_paths <- front_matter$data_inputs
  if (is.null(data_input_rel_paths)) data_input_rel_paths <- character(0)
  data_input_entries <- list()
  for (rel in data_input_rel_paths) {
    abs_path <- file.path(repo_root, rel)
    if (!file.exists(abs_path)) {
      stop(sprintf("[render_handson] %s: data_inputs に書かれた %s が見つかりません。", name, rel))
    }
    data_input_entries[[length(data_input_entries) + 1]] <- list(
      path = rel,
      sha256 = sha256_text_file(abs_path)
    )
  }

  # --- 配布用 .Rmd へのダウンロードリンクを末尾に付ける -----------------------
  # 各ハンズオンページから .Rmd をダウンロードできること(issue #17 の受け入れ
  # 条件)を、ページの著者が毎回書かなくても保証するため、レンダリングのたびに
  # 機械的に付与する。通常の Markdown リンク記法で書く(生の HTML <a> にすると
  # 画像と同じ理由でディレクトリURLの相対パス書き換えが効かず壊れるため)。
  download_rel <- file.path("rmd", paste0(name, ".Rmd"))
  md_text <- paste0(
    md_text,
    "\n\n---\n\nこのページのソース: [", name, ".Rmd をダウンロード](", download_rel, ")\n"
  )

  write_text_lf(md_text, md_path)

  # --- 配布用 .Rmd コピー -----------------------------------------------------
  rmd_copy_path <- file.path(rmd_copy_dir, paste0(name, ".Rmd"))
  src_rmd_text <- normalize_newlines(rawToChar(readBin(rmd_path, "raw", n = file.info(rmd_path)$size)))
  write_text_lf(src_rmd_text, rmd_copy_path)

  fig_entries <- list()
  for (p in produced_pngs) {
    fig_entries[[length(fig_entries) + 1]] <- list(
      path = to_repo_relative(p),
      sha256 = sha256_binary_file(p)
    )
  }

  list(
    source_rmd = list(path = to_repo_relative(rmd_path), sha256 = sha256_text_file(rmd_path)),
    output_md = list(path = to_repo_relative(md_path), sha256 = sha256_text_file(md_path)),
    distributed_rmd = list(path = to_repo_relative(rmd_copy_path), sha256 = sha256_text_file(rmd_copy_path)),
    data_inputs = data_input_entries,
    figures = fig_entries
  )
}

manifest <- existing_manifest
rendered_names <- character(0)
for (rmd_path in rmd_files) {
  name <- sub("\\.Rmd$", "", basename(rmd_path))
  cat(sprintf("[render_handson] %s をレンダリングします...\n", name))
  entry <- render_one_rmd(rmd_path, name)
  manifest[[name]] <- entry
  rendered_names <- c(rendered_names, name)
  cat(sprintf("[render_handson] %s 完了(図 %d 枚)\n", name, length(entry$figures)))
}

if (is_full_render) {
  # フル実行(引数なし)なら、マニフェストは「今 analysis/handson/ に存在する
  # Rmd」に完全に一致させる。削除された Rmd の残留エントリをここで落とす
  # (孤児になった図・配布用.Rmdコピー・生成mdは scripts/check_handson_fresh.py
  # の孤児検出に検出させる)。
  manifest <- manifest[rendered_names]
}

# --- マニフェスト全体をJSONで書く ------------------------------------------
pandoc_ver <- tryCatch(as.character(rmarkdown::pandoc_version()), error = function(e) NA_character_)
manifest_out <- list(
  meta = list(
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    pandoc_version = pandoc_ver
  ),
  handson = manifest
)

# jsonlite は analysis/DESCRIPTION の Imports に明示している(rmarkdown の推移的
# 依存として既にライブラリにはあったが、ここで直接呼ぶため明示した。digest と同じ扱い)。
# scripts/check_handson_fresh.py 側(Python)は標準ライブラリのみという制約だが、
# こちらは R 側なので無関係。
manifest_json <- jsonlite::toJSON(manifest_out, auto_unbox = TRUE, pretty = TRUE, null = "null")
writeLines(as.character(manifest_json), manifest_path, sep = "\n", useBytes = TRUE)

cat(sprintf("[render_handson] マニフェストを書きました: %s\n", to_repo_relative(manifest_path)))
cat("RENDER_HANDSON_OK\n")
