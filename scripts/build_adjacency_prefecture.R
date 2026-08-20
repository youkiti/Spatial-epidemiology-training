#!/usr/bin/env Rscript
# -*- coding: utf-8 -*-
#
# build_adjacency_prefecture.R — data/geo/prefecture.geojson(このリポジトリに
# コミット済みの47都道府県境界)から、queen contiguity による都道府県の隣接
# リストを作る(issue #20 の前工程)。
#
# scripts/build_geo.R は隣リポジトリ(visualize-regional-medical-care-for-2040)の
# 生の境界データを入力にしているが、本スクリプトは **このリポジトリに既にある
# data/geo/prefecture.geojson だけ**を入力にする(読者が別リポジトリを持って
# いなくても再現できるようにするため)。二次医療圏の隣接
# (data/geo/adjacency_iryoken2.csv)は既に build_geo.R が生成済みだが、都道府県の
# 隣接ファイルは存在しないため、issue #20(ハンズオン③ MAUP)の Global Moran's I
# を都道府県単位で計算するために本スクリプトで新規に作る。
#
# ## poly2nb() をサブプロセスで実行する理由(この環境固有の罠)
#
# build_geo.R と同じ罠がここにも当てはまる: この開発環境では spdep::poly2nb() を
# 呼ぶと、計算自体は最後まで正しく終わるのに、**Rプロセスの終了時に異常終了する**
# (リポジトリ直下の CLAUDE.md「環境」節、および build_geo.R のコメント参照)。
# 47都道府県という小さいフィーチャ数でも同種のクラッシュを避けるため、
# build_geo.R と同じく **poly2nb() の呼び出しだけを子プロセスの Rscript に
# 切り出し、結果をCSVに書かせてから親が読み戻す**。終了コードでは成否を
# 判定せず、子プロセスが最後に出力する完了マーカー("child: 完了")の有無で
# 判定する(ファイルの存在チェックだけだと、書き込み途中で切れたCSVを
# 黙って読んでしまうため)。
#
# 使い方:
#   Rscript scripts/build_adjacency_prefecture.R
#   Rscript scripts/build_adjacency_prefecture.R --prefecture-boundaries <path> --out-dir data/geo
#
# 終了コード: 成功=0、フィーチャ数不一致・入力ファイル不在などは非ゼロ。

suppressPackageStartupMessages({
  library(sf)
})

# poly2nb 呼び出しに伴うプロセス終了時クラッシュを避けるため、ジオメトリの
# 読み込み・妥当性チェックは本プロセスで行うが、隣接計算(poly2nb)は
# 後段で別プロセスに切り出す(上の docstring 参照)。
sf::sf_use_s2(FALSE)

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(flag, default) {
  idx <- which(args == flag)
  if (length(idx) == 0 || idx == length(args)) return(default)
  args[idx + 1]
}

default_pref_path <- "data/geo/prefecture.geojson"
default_rscript_bin <- file.path(
  R.home("bin"),
  if (.Platform$OS.type == "windows") "Rscript.exe" else "Rscript"
)

pref_path <- get_arg("--prefecture-boundaries", default_pref_path)
out_dir <- get_arg("--out-dir", "data/geo")
rscript_bin <- get_arg("--rscript-bin", default_rscript_bin)

fail <- function(msg) {
  message(msg)
  quit(status = 1)
}

if (!file.exists(pref_path)) {
  fail(paste0(
    "エラー: 都道府県境界の入力ファイルが見つかりません: ", pref_path, "\n",
    "data/geo/prefecture.geojson(scripts/build_geo.R の既存生成物)を",
    "--prefecture-boundaries <path> で指定してください。"
  ))
}
if (!file.exists(rscript_bin)) {
  fail(paste0(
    "エラー: poly2nb をサブプロセスで実行するための Rscript.exe が見つかりません: ", rscript_bin, "\n",
    "--rscript-bin <path> で Rscript.exe のフルパスを指定してください。"
  ))
}

if (!dir.exists(out_dir)) {
  dir.create(out_dir, recursive = TRUE)
}

# 診断結果を stdout と markdown の両方に貯める行バッファ
diag_lines <- character(0)
emit <- function(...) {
  line <- paste0(...)
  cat(line, "\n", sep = "")
  diag_lines <<- c(diag_lines, line)
}

emit("# 都道府県隣接データ診断(build_adjacency_prefecture.R)")
emit("")
emit(sprintf("- 実行日(ローカル): %s", format(Sys.Date(), "%Y-%m-%d")))
emit(sprintf("- 入力: %s(このリポジトリにコミット済み。scripts/build_geo.R の既存生成物)", pref_path))
emit("")

# --- 読み込み ---------------------------------------------------------------
pref_sf <- st_read(pref_path, quiet = TRUE)

# --- 診断1: フィーチャ数 -----------------------------------------------------
emit("## 1. フィーチャ数")
emit("")
n_pref <- nrow(pref_sf)
emit(sprintf("- 都道府県: %d 件(期待値 47)", n_pref))
emit("")
if (n_pref != 47) {
  fail(sprintf("エラー: 都道府県のフィーチャ数が47ではありません(実測 %d 件)。", n_pref))
}

# pref_code はゼロ埋め文字列のまま扱う(build_geo.R と同じ既知の罠: 数値化すると
# 先頭ゼロが落ちる)。
pref_sf$pref_code <- as.character(pref_sf$pref_code)

# 出力を決定的にするため pref_code 昇順に並べ替える
pref_sf <- pref_sf[order(pref_sf$pref_code), ]
rownames(pref_sf) <- NULL

# --- 診断2: ジオメトリ妥当性 -------------------------------------------------
emit("## 2. ジオメトリ妥当性(st_is_valid)")
emit("")

valid <- st_is_valid(pref_sf)
n_invalid <- sum(!valid)
emit(sprintf("- 都道府県: 不正なジオメトリ %d 件 / %d 件", n_invalid, nrow(pref_sf)))
if (n_invalid > 0) {
  bad <- pref_sf[!valid, ]
  emit(sprintf(
    "  - 修復対象: %s",
    paste(sprintf("%s(%s)", bad$pref_name, bad$pref_code), collapse = ", ")
  ))
  pref_sf <- st_make_valid(pref_sf)
  valid_after <- st_is_valid(pref_sf)
  emit(sprintf("  - st_make_valid() 後の不正件数: %d 件", sum(!valid_after)))
  if (sum(!valid_after) > 0) {
    fail(sprintf(
      "エラー: st_make_valid() 後もジオメトリが不正な都道府県が残っています(%d 件)。手動確認が必要です。",
      sum(!valid_after)
    ))
  }
}
emit("")

# --- 隣接(queen contiguity)。poly2nb は子プロセスで実行する -----------------
#
# snap=0 / 0.0001(座標丸め幅と同程度) / 0.001(その10倍、対照条件)の3通りで
# poly2nb を実行し、それぞれの隣接ペアをCSVに書き出す(build_geo.R と同じ設計)。

pref_tmp_geojson <- tempfile(fileext = ".geojson")
st_write(pref_sf[, c("pref_code", "pref_name")],
         pref_tmp_geojson, driver = "GeoJSON", quiet = TRUE)

child_out_dir <- tempfile(pattern = "poly2nb_pref_out_")
dir.create(child_out_dir)

child_script_path <- tempfile(fileext = ".R")
child_code <- c(
  "args <- commandArgs(trailingOnly = TRUE)",
  "in_path <- args[1]",
  "out_dir <- args[2]",
  "suppressPackageStartupMessages({ library(sf); library(spdep) })",
  "sf::sf_use_s2(FALSE)",
  "pref_sf <- st_read(in_path, quiet = TRUE)",
  "codes <- as.character(pref_sf$pref_code)",
  "snap_values <- list(snap0 = 0, snap1 = 0.0001, snap10 = 0.001)",
  "write_edges <- function(nb, codes, out_path) {",
  "  rows <- list()",
  "  for (i in seq_along(nb)) {",
  "    nbrs <- nb[[i]]",
  "    if (identical(nbrs, 0L)) next",
  "    for (j in nbrs) rows[[length(rows) + 1]] <- c(codes[i], codes[j])",
  "  }",
  "  con <- file(out_path, open = 'wb')",
  "  writeLines('area_code,neighbor_code', con, sep = '\\n')",
  "  if (length(rows) > 0) {",
  "    m <- do.call(rbind, rows)",
  "    writeLines(paste(m[, 1], m[, 2], sep = ','), con, sep = '\\n')",
  "  }",
  "  close(con)",
  "}",
  "for (nm in names(snap_values)) {",
  "  nb <- poly2nb(pref_sf, queen = TRUE, snap = snap_values[[nm]])",
  "  write_edges(nb, codes, file.path(out_dir, paste0(nm, '.csv')))",
  "  cat(sprintf('poly2nb(snap=%s): 有向隣接ペア %d 件\\n', nm, sum(sapply(nb, function(x) if (identical(x, 0L)) 0L else length(x)))))",
  "}",
  "cat('child: 完了\\n')"
)
writeLines(child_code, child_script_path, sep = "\n")

child_stdout <- system2(
  rscript_bin,
  args = c(shQuote(child_script_path), shQuote(pref_tmp_geojson), shQuote(child_out_dir)),
  stdout = TRUE, stderr = TRUE
)
child_status <- attr(child_stdout, "status")
if (is.null(child_status)) child_status <- 0L

# 子プロセスが最後まで書き切ったかどうかは終了コードでは判定できない(上の
# docstring のとおり)。完了マーカー("child: 完了")の有無で判定する。
child_completed <- any(grepl("child: 完了", child_stdout, fixed = TRUE))
if (!child_completed) {
  fail(sprintf(
    paste0(
      "エラー: poly2nb 子プロセスが完了マーカー(child: 完了)を出力しませんでした。\n",
      "CSVが存在していても書き込み途中で切り詰められている可能性があるため、",
      "読み進めずに停止します。子プロセスのログ全文:\n%s"
    ),
    paste(child_stdout, collapse = "\n")
  ))
}

read_edges <- function(nm) {
  path <- file.path(child_out_dir, paste0(nm, ".csv"))
  if (!file.exists(path)) {
    fail(sprintf(
      "エラー: poly2nb 子プロセスが %s を書き出せませんでした(子プロセスのログ:\n%s\n)。",
      path, paste(child_stdout, collapse = "\n")
    ))
  }
  read.csv(path, colClasses = c("character", "character"))
}

edges_snap0 <- read_edges("snap0")
edges_snap1 <- read_edges("snap1")
edges_snap10 <- read_edges("snap10")

pair_key <- function(df) paste(df$area_code, df$neighbor_code, sep = "->")

set_snap0 <- pair_key(edges_snap0)
set_snap1 <- pair_key(edges_snap1)
set_snap10 <- pair_key(edges_snap10)

diff_0_1 <- length(union(setdiff(set_snap0, set_snap1), setdiff(set_snap1, set_snap0)))
diff_1_10 <- length(union(setdiff(set_snap1, set_snap10), setdiff(set_snap10, set_snap1)))
diff_0_10 <- length(union(setdiff(set_snap0, set_snap10), setdiff(set_snap10, set_snap0)))

# 本採用の snap の決定は diff_0_1(snap=0 と snap=0.0001 の差)だけで行う。
# build_geo.R と同じ理由で snap=0.001 は対照条件として扱い、採否には使わない。
if (diff_0_1 == 0) {
  main_edges <- edges_snap0
  main_snap_label <- "snap=0(spdepの既定相当。snap=0.0001と隣接ペアの集合差が無かったため、人為的な結合を一切入れない値を採用)"
} else {
  main_edges <- edges_snap1
  main_snap_label <- "snap=0.0001(座標丸め幅と同程度。snap=0との間に集合差が生じたため丸め由来の隙間を吸収する値を採用)"
}

# --- 診断3: 孤立都道府県の列挙(本採用の隣接関係で判定) ----------------------
all_codes <- pref_sf$pref_code
degree_tbl <- table(factor(main_edges$area_code, levels = all_codes))
degrees <- as.integer(degree_tbl)
names(degrees) <- names(degree_tbl)

isolated_codes <- names(degrees)[degrees == 0]

# --- 診断4: 連結成分(幅優先探索。igraph 等の新規パッケージは使わない) --------
component_of <- setNames(rep(NA_integer_, length(all_codes)), all_codes)
adj_list <- split(main_edges$neighbor_code, main_edges$area_code)
next_component <- 0L
for (code in all_codes) {
  if (!is.na(component_of[[code]])) next
  next_component <- next_component + 1L
  queue <- code
  component_of[[code]] <- next_component
  while (length(queue) > 0) {
    cur <- queue[1]
    queue <- queue[-1]
    nbrs <- adj_list[[cur]]
    if (!is.null(nbrs)) {
      for (nb in nbrs) {
        if (is.na(component_of[[nb]])) {
          component_of[[nb]] <- next_component
          queue <- c(queue, nb)
        }
      }
    }
  }
}
component_ids <- sort(unique(component_of))
components <- lapply(component_ids, function(cid) names(component_of)[component_of == cid])
comp_sizes <- sapply(components, length)
comp_order <- order(comp_sizes, decreasing = TRUE)
components <- components[comp_order]
comp_sizes <- comp_sizes[comp_order]

singleton_codes <- sort(as.character(unlist(components[comp_sizes == 1])))
components_match_isolated <- identical(singleton_codes, sort(as.character(isolated_codes)))

# --- 出力(1→2→3→4→5→6 の順に並べる。子プロセスのログは付録として最後に出す) --

emit("## 3. 孤立都道府県(隣接0件)の列挙")
emit("")
if (length(isolated_codes) == 0) {
  emit("- 孤立都道府県は無し(全47都道府県が1件以上の隣接を持つ)。")
} else {
  emit(sprintf("- 孤立都道府県: %d 件", length(isolated_codes)))
  for (code in isolated_codes) {
    idx <- which(pref_sf$pref_code == code)
    emit(sprintf("  - %s(%s)", pref_sf$pref_name[idx], code))
  }
  emit("- 陸上で他都道府県と接していない(海で隔てられている)都道府県であれば妥当。")
}
emit("")

emit("## 4. snap 感度テスト")
emit("")
emit(sprintf("- snap=0(頂点完全一致のみ): 有向隣接ペア %d 件", nrow(edges_snap0)))
emit(sprintf("- snap=0.0001(座標丸め幅と同程度、約11m): 有向隣接ペア %d 件", nrow(edges_snap1)))
emit(sprintf("- snap=0.001(座標丸め幅の10倍、約111m): 有向隣接ペア %d 件", nrow(edges_snap10)))
emit(sprintf("- snap=0 と snap=0.0001 の集合差: %d 件", diff_0_1))
emit(sprintf("- snap=0.0001 と snap=0.001 の集合差: %d 件", diff_1_10))
emit(sprintf("- snap=0 と snap=0.001 の集合差: %d 件", diff_0_10))
emit("")
if (diff_0_1 == 0) {
  emit(sprintf(
    "- 結論: snap=0とsnap=0.0001で隣接ペアの集合は完全に一致した(%d件、集合差%d件)。",
    nrow(edges_snap0), diff_0_1
  ))
  emit("  座標丸めによって生じた隙間で隣接が失われている形跡は無い。")
  if (diff_1_10 > 0) {
    emit(sprintf(
      "  snapを丸め幅の10倍(0.001度、約111m)まで緩めると%d件増えるが、これは",
      diff_1_10
    ))
    emit("  本来隣接していないポリゴンを許容幅で結合してしまう過剰結合であり、")
    emit("  丸めの影響を示すものではない(対照条件で差が出たことを理由に本採用の")
    emit("  snapを緩めてはいけない)。")
  }
} else {
  emit(sprintf(
    "- 結論: snap=0とsnap=0.0001の間で隣接ペアの集合に%d件の差が生じた。",
    diff_0_1
  ))
  emit("  丸め幅と同程度のsnap=0.0001を採用し、丸め由来の隙間を吸収する。")
}
emit("")
emit(sprintf("- 本採用(adjacency_prefecture.csv): %s", main_snap_label))
emit("")

emit("## 5. 隣接数の要約")
emit("")
emit(sprintf("- 平均: %.3f", mean(degrees)))
emit(sprintf("- 最小: %d", min(degrees)))
emit(sprintf("- 最大: %d", max(degrees)))
emit("")

emit("## 6. 連結成分")
emit("")
emit("- 都道府県単位の空間重み行列(隣接グラフ)が連結しているかどうかは、")
emit("  ハンズオン③(MAUP)で都道府県単位のGlobal Moran's Iを計算する際に")
emit("  直接効く論点のため、実測して記録する。")
emit(sprintf("- 連結成分の個数: %d", length(components)))
emit("- サイズ(降順)と代表都道府県:")
for (i in seq_along(components)) {
  comp <- components[[i]]
  size <- comp_sizes[i]
  idxs <- match(comp, pref_sf$pref_code)
  if (size == 1) {
    emit(sprintf(
      "  - 成分%d: 1都道府県(孤立: %s)",
      i, pref_sf$pref_name[idxs]
    ))
  } else {
    names_label <- pref_sf$pref_name[idxs]
    if (length(names_label) > 6) {
      label <- sprintf("%s ほか%d件", paste(names_label[1:6], collapse = "、"), length(names_label) - 6)
    } else {
      label <- paste(names_label, collapse = "、")
    }
    emit(sprintf("  - 成分%d: %d都道府県(%s)", i, size, label))
  }
}
emit("")
emit(sprintf(
  "- サイズ1の成分(孤立都道府県)は%d件で、診断3で列挙した孤立都道府県%d件と%s。",
  sum(comp_sizes == 1), length(isolated_codes),
  if (components_match_isolated) "一致した" else "一致しなかった(要確認)"
))
if (!components_match_isolated) {
  fail("エラー: 連結成分から求めた孤立都道府県(サイズ1の成分)が診断3の孤立都道府県と一致しません。main_edgesの対称性を確認してください。")
}
emit("")

emit("## 付録: poly2nb 子プロセスの実行ログ")
emit("")
emit(paste(child_stdout, collapse = "\n"))
emit(sprintf(
  "(子プロセスの終了コード: %s — 計算後のプロセス終了時クラッシュにより非ゼロになりうる。完了マーカーの有無で成否を判定する。)",
  child_status
))
emit("")

# --- 出力: 診断markdown ------------------------------------------------------
diag_md_path <- file.path(out_dir, "adjacency_prefecture_diagnostics.md")
con <- file(diag_md_path, open = "wb")
writeLines(enc2utf8(diag_lines), con, useBytes = TRUE, sep = "\n")
close(con)
cat(sprintf("診断結果を書き出しました: %s\n", diag_md_path))

# --- 出力: adjacency_prefecture.csv(area_code昇順・neighbor_code昇順) -------
adj_df <- main_edges[order(main_edges$area_code, main_edges$neighbor_code), ]
adj_csv_path <- file.path(out_dir, "adjacency_prefecture.csv")
con <- file(adj_csv_path, open = "wb")
writeLines("area_code,neighbor_code", con, sep = "\n")
if (nrow(adj_df) > 0) {
  writeLines(paste(adj_df$area_code, adj_df$neighbor_code, sep = ","), con, sep = "\n")
}
close(con)
cat(sprintf("書き出しました: %s(%d 行)\n", adj_csv_path, nrow(adj_df)))

# 一時ファイルの片付け
unlink(pref_tmp_geojson)
unlink(child_script_path)
unlink(child_out_dir, recursive = TRUE)

cat("build_adjacency_prefecture.R 完了。\n")
quit(status = 0)
