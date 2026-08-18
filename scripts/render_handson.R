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
# 前提: analysis/ で renv::restore() 済みであること(analysis/README.md 参照)。
# 通常の(--vanilla でない)Rscript 起動であれば analysis/.Rprofile がなくても
# 問題ない。renv を使わずシステムライブラリのパッケージで動かすことも想定している
# (analysis/renv.lock はシステムライブラリの実バージョンをそのまま記録したものなので、
# renv::restore() してもしなくても同じバージョンが使われる)。
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

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
  rmd_files <- sort(list.files(handson_src_dir, pattern = "\\.Rmd$", full.names = TRUE))
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

# --- ハッシュ計算 -----------------------------------------------------------
# テキストファイル(.Rmd / .md)は改行を LF に正規化してからハッシュする。
# .gitattributes は "* text=auto eol=lf" だが、作業コピーの改行コードは環境に
# よって CRLF になりうる(このリポジトリの CLAUDE.md に既知の罠として記載)。
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

convert_raw_img_tags <- function(text) {
  m <- gregexpr("<img\\b[^>]*/?>", text, perl = TRUE)
  tags <- regmatches(text, m)[[1]]
  if (length(tags) == 0) return(text)

  replacements <- vapply(tags, function(tag) {
    src <- extract_html_attr(tag, "src")
    if (is.na(src)) return(tag) # src が無い <img> には手を出さない
    alt <- extract_html_attr(tag, "alt")
    if (is.na(alt)) alt <- ""
    sprintf("![%s](%s)", alt, src)
  }, character(1), USE.NAMES = FALSE)

  regmatches(text, m) <- list(replacements)
  text
}

to_repo_relative <- function(path) {
  full <- normalizePath(path, winslash = "/", mustWork = TRUE)
  root <- normalizePath(repo_root, winslash = "/", mustWork = TRUE)
  prefix <- paste0(root, "/")
  # sub() は第1引数を正規表現として扱うため、root にドットや+等の正規表現
  # メタ文字が含まれると静かに誤動作しうる(実測上は今のパスに含まれないが、
  # リテラルな前置詞の除去として書く方が安全)。substring() で先頭を切り落とす。
  if (startsWith(full, prefix)) {
    substring(full, nchar(prefix) + 1)
  } else {
    full
  }
}

manifest <- list()

for (rmd_path in rmd_files) {
  name <- sub("\\.Rmd$", "", basename(rmd_path))
  cat(sprintf("[render_handson] %s をレンダリングします...\n", name))

  # 既存の生成物(このRmd由来のもの)を先に削除してから作り直す。孤児ファイルが
  # 残らないようにするため(チャンクの削除・fig.cap変更などに追従させる)。
  stale_figs <- list.files(figures_dir, pattern = paste0("^", name, "-[0-9]+\\.png$"), full.names = TRUE)
  if (length(stale_figs) > 0) file.remove(stale_figs)
  stale_files_dir <- file.path(docs_handson_dir, paste0(name, "_files"))
  if (dir.exists(stale_files_dir)) unlink(stale_files_dir, recursive = TRUE)

  # dev/dpi は rmarkdown::render() の前に knitr::opts_chunk$set() で指定すれば
  # そのまま効く。ragg_png を使うのは Windows で日本語が化けないようにするため
  # (CLAUDE.md 「環境」節)。
  #
  # 【罠】fig.path はここで knitr::opts_chunk$set() しても効かない。
  # rmarkdown::render() が knit 実行前に "<入力ファイル名>_files/figure-<形式>/"
  # という既定の fig.path を内部で再設定してしまうため(Rmd 内のチャンクで
  # 明示的に上書きしない限り、外から事前に仕込んだ値は knit 開始と同時に
  # 上書きされて消える。実測で確認済み)。そのため fig.path は既定のまま
  # レンダリングさせ、生成された画像ファイルをレンダリング後に
  # figures/<name>-<連番>.png へリネーム・移動し、md 内の参照パスも
  # 書き換える(下記の後処理)。
  knitr::opts_chunk$set(dev = "ragg_png", dpi = 150)

  md_filename <- paste0(name, ".md")
  rendered_path <- rmarkdown::render(
    input = rmd_path,
    output_format = rmarkdown::md_document(
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
    ),
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

  # --- 図の後処理: <name>_files/figure-*/ から figures/<name>-<連番>.png へ ----
  files_dir_candidates <- Sys.glob(file.path(docs_handson_dir, paste0(name, "_files"), "figure-*"))
  md_text <- normalize_newlines(rawToChar(readBin(md_path, "raw", n = file.info(md_path)$size)))
  # fig.alt 由来の生HTML <img> を Markdown 記法に戻す。これを図パスの
  # 書き換え(直後のブロック)より先に行うことで、書き換えロジックが
  # Markdown 記法だけを見ればよいようにする。
  md_text <- convert_raw_img_tags(md_text)

  if (length(files_dir_candidates) > 0) {
    src_figure_dir <- files_dir_candidates[[1]]
    src_pngs <- sort(list.files(src_figure_dir, pattern = "\\.png$", full.names = TRUE))
    for (i in seq_along(src_pngs)) {
      old_abs <- normalizePath(src_pngs[[i]], winslash = "/", mustWork = TRUE)
      old_rel <- to_repo_relative(old_abs)
      new_name <- sprintf("%s-%d.png", name, i)
      new_path <- file.path(figures_dir, new_name)
      file.copy(old_abs, new_path, overwrite = TRUE)
      file.remove(old_abs)
      new_rel_from_md <- file.path("figures", new_name)
      # md 中の画像参照は絶対パスで書かれている場合と、docs/handson/ からの相対
      # パスで書かれている場合の両方がありうる(knit_root_dir と output_dir が
      # 一致しないため rmarkdown が絶対パスにフォールバックすることを実測で確認
      # 済みだが、将来のバージョン差やパス構成の変化に備えて両方を試す)。
      docs_handson_prefix <- paste0(gsub("\\\\", "/", docs_handson_dir), "/")
      old_from_docs_handson <- if (startsWith(old_abs, docs_handson_prefix)) {
        substring(old_abs, nchar(docs_handson_prefix) + 1)
      } else {
        old_abs
      }
      for (candidate in unique(c(old_abs, old_from_docs_handson))) {
        if (nzchar(candidate) && grepl(candidate, md_text, fixed = TRUE)) {
          md_text <- gsub(candidate, new_rel_from_md, md_text, fixed = TRUE)
        }
      }
    }
    unlink(file.path(docs_handson_dir, paste0(name, "_files")), recursive = TRUE)
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

  writeLines(md_text, md_path, sep = "\n", useBytes = TRUE)

  # --- 配布用 .Rmd コピー -----------------------------------------------------
  rmd_copy_path <- file.path(rmd_copy_dir, paste0(name, ".Rmd"))
  src_rmd_text <- normalize_newlines(rawToChar(readBin(rmd_path, "raw", n = file.info(rmd_path)$size)))
  writeLines(src_rmd_text, rmd_copy_path, sep = "\n", useBytes = TRUE)

  # --- マニフェストへの記録 ---------------------------------------------------
  fig_entries <- list()
  new_pngs <- sort(list.files(figures_dir, pattern = paste0("^", name, "-[0-9]+\\.png$"), full.names = TRUE))
  for (p in new_pngs) {
    fig_entries[[length(fig_entries) + 1]] <- list(
      path = to_repo_relative(p),
      sha256 = sha256_binary_file(p)
    )
  }

  manifest[[name]] <- list(
    source_rmd = list(path = to_repo_relative(rmd_path), sha256 = sha256_text_file(rmd_path)),
    output_md = list(path = to_repo_relative(md_path), sha256 = sha256_text_file(md_path)),
    distributed_rmd = list(path = to_repo_relative(rmd_copy_path), sha256 = sha256_text_file(rmd_copy_path)),
    figures = fig_entries
  )

  cat(sprintf("[render_handson] %s 完了(図 %d 枚)\n", name, length(fig_entries)))
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
