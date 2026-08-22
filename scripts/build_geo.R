#!/usr/bin/env Rscript
# -*- coding: utf-8 -*-
#
# build_geo.R — 隣リポジトリ(visualize-regional-medical-care-for-2040)の
# 境界GeoJSONから、このリポジトリで使う二次医療圏・都道府県の境界と、
# queen contiguity による隣接リストを作る(issue #4)。
#
# ## 主ジオメトリに area_boundaries_R7.geojson(339区域)を採る理由
#
# issue #4 本文は iryoken2_A38-20.geojson(335圏、生のA38属性)を起点にする
# 前提で書かれているが、本スクリプトは area_boundaries_R7.geojson(339区域)を
# 主に採用する。理由: 属性が area_code/pref_code として既に整理されており、
# issue #5 の人口CSV(area_basic.csv、339区域)とそのまま area_code で結合できる。
# 335圏版は令和2年度時点の生のA38属性(A38b_003 等)のままで、結合キーを
# 自分で作り直す必要がある。339 と 335 の差は三重県の構想区域細分化に由来する
# (隣リポの tools/build_area_boundaries.py docstring 参照)。
#
# ## これ以上の簡略化をしない理由
#
# issue #4 は「目標1MB級」への追加簡略化を求めているが、本スクリプトは
# st_simplify() 等の追加簡略化を行わない。この教材の中心概念は queen
# contiguity(隣接の定義)そのものであり、追加の簡略化は隣接関係を変えうる。
# 入力の area_boundaries_R7.geojson は既に約4.5MBで、GitHub の100MB制限に
# 対して十分小さい。削って得る容量の利益より、隣接を壊すリスクのほうが大きい
# と判断した。
#
# ## この境界データは「表示専用」と明記されている
#
# 隣リポの doc/DATA_SOURCES.md は、この境界データについて「1km2未満の
# 離島リング除去・Visvalingam加重2%簡略化・座標0.0001度(約11m)丸め」を行い、
# 「面積計算等の解析には使わず表示専用とする」と明記している。この教材の
# 骨格が空間重み行列(隣接の定義)である以上、「この表示専用データで queen
# contiguity を導いてよいか」を実測で確かめる必要がある。本スクリプトは
# その診断(フィーチャ数・妥当性・孤立区域・snap感度・隣接数・連結成分・
# ブリッジ)を実行し、stdout と data/geo/adjacency_diagnostics.md の両方に
# 出力する。
#
# ## poly2nb() をサブプロセスで実行する理由(この環境固有の罠)
#
# この開発環境では、339区域のジオメトリに対して spdep::poly2nb() を呼ぶと、
# 計算自体は最後まで正しく終わる(結果を表示できる)のに、**Rプロセスの終了時に
# 異常終了する**(Git Bashからは終了コード127相当で観測される)。
# scripts/verify_simulation.R が spdep::mat2listw() について記録している
# 「計算は成功するがプロセス終了時にクラッシュする」現象と同種のもので、
# 今回は mat2listw ではなく poly2nb 自体がトリガーになっている(実測で切り分け
# 済み: st_read/st_make_valid だけなら異常終了しないが、直後に poly2nb を
# 呼ぶと異常終了する)。poly2nb を丸ごと避けることはできない(隣接をポリゴンから
# 導くのがこの issue の目的そのもののため)ので、**poly2nb の呼び出しだけを
# 子プロセスの Rscript に切り出し、結果をCSVに書き出させてから読み戻す**
# ことで回避する。子プロセスが終了時に異常終了しても、計算結果は既にディスクに
# 書き出し済みなので影響しない(system2() の戻り値・終了コードは診断目的でのみ
# 参照し、失敗の判定には使わない)。ただし「CSVが存在する」だけでは書き込み
# 途中でクラッシュして切り詰められた場合を検出できないため、子プロセスが最後に
# 出力する完了マーカー("child: 完了")の有無で成否を判定する(詳細は下記)。
#
# 使い方:
#   Rscript scripts/build_geo.R
#   Rscript scripts/build_geo.R --area-boundaries <path> --prefecture-boundaries <path> --out-dir data/geo
#
# 終了コード: 成功=0、フィーチャ数不一致・入力ファイル不在などは非ゼロ。

suppressPackageStartupMessages({
  library(sf)
})

# poly2nb 呼び出しに伴うプロセス終了時クラッシュを避けるため、ジオメトリの
# 読み込み・妥当性チェック・修復は本プロセスで行うが、隣接計算(poly2nb)は
# 後段で別プロセスに切り出す(上の docstring 参照)。
sf::sf_use_s2(FALSE)

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(flag, default) {
  idx <- which(args == flag)
  if (length(idx) == 0 || idx == length(args)) return(default)
  args[idx + 1]
}

# 境界データの入力は隣リポジトリ(visualize-regional-medical-care-for-2040)の
# 出力。置き場所は利用者ごとに違うので既定値は持たせず、環境変数 NEIGHBOR_REPO
# か個別の引数で受け取る(issue #51。開発機の絶対パスにフォールバックしない)。
neighbor_area_boundaries <- "data/processed/area_boundaries_R7.geojson"
neighbor_prefecture_boundaries <- "data/processed/prefecture_boundaries_R7.geojson"

fail <- function(msg) {
  message(msg)
  quit(status = 1)
}

# 入手手順の案内。scripts/lib_neighbor_repo.py の guidance() と同じ文面を保つ。
neighbor_guidance <- function(relative, option) {
  paste0(
    "隣リポジトリ visualize-regional-medical-care-for-2040 の\n",
    "  ", relative, "\n",
    "が必要です。次のどちらかで場所を指定してください。\n",
    "  1. 環境変数 NEIGHBOR_REPO に隣リポジトリのルートを設定する\n",
    "     (例: NEIGHBOR_REPO=../visualize-regional-medical-care-for-2040)\n",
    "  2. ", option, " <path> でファイルを直接指定する\n",
    "隣リポジトリの入手元と、この入力の生成手順は\n",
    "  https://github.com/youkiti/visualize-regional-medical-care-for-2040\n",
    "および documents/DATA_SOURCES.md を参照。"
  )
}

# 個別指定 → $NEIGHBOR_REPO の順に解決する。どちらも無ければ案内して exit 1
# (黙って存在しないパスのまま先へ進み、空の出力を作らない)。
resolve_neighbor_path <- function(flag, relative) {
  given <- get_arg(flag, NULL)
  if (!is.null(given)) return(given)
  root <- Sys.getenv("NEIGHBOR_REPO", unset = "")
  if (nzchar(root)) return(file.path(root, relative))
  fail(paste0("エラー: ", neighbor_guidance(relative, flag)))
}

area_path <- resolve_neighbor_path("--area-boundaries", neighbor_area_boundaries)
pref_path <- resolve_neighbor_path("--prefecture-boundaries", neighbor_prefecture_boundaries)
out_dir <- get_arg("--out-dir", "data/geo")
# poly2nb() を切り出す子プロセスの Rscript。既定はこのプロセス自身の R
# (開発機固有の絶対パスを既定にしない。別の R を使いたいときは --rscript-bin)。
default_rscript_bin <- file.path(
  R.home("bin"),
  if (.Platform$OS.type == "windows") "Rscript.exe" else "Rscript"
)
rscript_bin <- get_arg("--rscript-bin", default_rscript_bin)

if (!file.exists(area_path)) {
  fail(paste0(
    "エラー: 二次医療圏境界の入力ファイルが見つかりません: ", area_path, "\n",
    neighbor_guidance(neighbor_area_boundaries, "--area-boundaries")
  ))
}
if (!file.exists(pref_path)) {
  fail(paste0(
    "エラー: 都道府県境界の入力ファイルが見つかりません: ", pref_path, "\n",
    neighbor_guidance(neighbor_prefecture_boundaries, "--prefecture-boundaries")
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

emit("# 境界データ診断(build_geo.R)")
emit("")
# 秒まで入れると再生成のたびにコミット差分が出るため、日付のみ記録する。
emit(sprintf("- 実行日(ローカル): %s", format(Sys.Date(), "%Y-%m-%d")))
emit(sprintf("- 二次医療圏の入力: %s", area_path))
emit(sprintf("- 都道府県の入力: %s", pref_path))
emit("")

# --- 読み込み ---------------------------------------------------------------
area_sf <- st_read(area_path, quiet = TRUE)
pref_sf <- st_read(pref_path, quiet = TRUE)

# --- 診断1: フィーチャ数 -----------------------------------------------------
emit("## 1. フィーチャ数")
emit("")
n_area <- nrow(area_sf)
n_pref <- nrow(pref_sf)
emit(sprintf("- 二次医療圏: %d 件(期待値 339)", n_area))
emit(sprintf("- 都道府県: %d 件(期待値 47)", n_pref))
emit("")
if (n_area != 339) {
  fail(sprintf("エラー: 二次医療圏のフィーチャ数が339ではありません(実測 %d 件)。", n_area))
}
if (n_pref != 47) {
  fail(sprintf("エラー: 都道府県のフィーチャ数が47ではありません(実測 %d 件)。", n_pref))
}

# area_code・pref_code はゼロ埋め文字列のまま扱う(issue #4 の既知の罠:
# 数値化すると先頭ゼロが落ちる)。st_read は GeoJSON の文字列値をそのまま
# character として読むため、ここでは明示的に as.character() で念押しする。
area_sf$area_code <- as.character(area_sf$area_code)
area_sf$pref_code <- as.character(area_sf$pref_code)
pref_sf$pref_code <- as.character(pref_sf$pref_code)

# 出力を決定的にするため area_code / pref_code 昇順に並べ替える
area_sf <- area_sf[order(area_sf$area_code), ]
pref_sf <- pref_sf[order(pref_sf$pref_code), ]
rownames(area_sf) <- NULL
rownames(pref_sf) <- NULL

# --- 診断2: ジオメトリ妥当性 -------------------------------------------------
emit("## 2. ジオメトリ妥当性(st_is_valid)")
emit("")

repair_report <- function(sf_obj, code_col, name_col, label) {
  valid <- st_is_valid(sf_obj)
  n_invalid <- sum(!valid)
  emit(sprintf("- %s: 不正なジオメトリ %d 件 / %d 件", label, n_invalid, nrow(sf_obj)))
  if (n_invalid > 0) {
    bad <- sf_obj[!valid, ]
    emit(sprintf(
      "  - 修復対象(%s): %s",
      label,
      paste(sprintf("%s(%s)", bad[[name_col]], bad[[code_col]]), collapse = ", ")
    ))
    sf_obj <- st_make_valid(sf_obj)
    valid_after <- st_is_valid(sf_obj)
    emit(sprintf("  - st_make_valid() 後の不正件数: %d 件", sum(!valid_after)))
    if (sum(!valid_after) > 0) {
      fail(sprintf(
        "エラー: %s で st_make_valid() 後もジオメトリが不正な区域が残っています(%d 件)。手動確認が必要です。",
        label, sum(!valid_after)
      ))
    }
  }
  sf_obj
}

area_sf <- repair_report(area_sf, "area_code", "area_name", "二次医療圏")
pref_sf <- repair_report(pref_sf, "pref_code", "pref_name", "都道府県")
emit("")

# --- 隣接(queen contiguity)。poly2nb は子プロセスで実行する -----------------
#
# 上の docstring のとおり、この環境では poly2nb() の呼び出し自体が計算後の
# プロセス終了時クラッシュを引き起こすため、子プロセスに切り出す。子プロセスは
# snap=0 / 0.0001(座標丸め幅と同程度) / 0.001(その10倍)の3通りで poly2nb を
# 実行し、それぞれの隣接ペアをCSVに書き出す。

area_tmp_geojson <- tempfile(fileext = ".geojson")
st_write(area_sf[, c("area_code", "area_name", "pref_code", "pref_name")],
         area_tmp_geojson, driver = "GeoJSON", quiet = TRUE)

child_out_dir <- tempfile(pattern = "poly2nb_out_")
dir.create(child_out_dir)

child_script_path <- tempfile(fileext = ".R")
child_code <- c(
  "args <- commandArgs(trailingOnly = TRUE)",
  "in_path <- args[1]",
  "out_dir <- args[2]",
  "suppressPackageStartupMessages({ library(sf); library(spdep) })",
  "sf::sf_use_s2(FALSE)",
  "area_sf <- st_read(in_path, quiet = TRUE)",
  "codes <- as.character(area_sf$area_code)",
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
  "  nb <- poly2nb(area_sf, queen = TRUE, snap = snap_values[[nm]])",
  "  write_edges(nb, codes, file.path(out_dir, paste0(nm, '.csv')))",
  "  cat(sprintf('poly2nb(snap=%s): 有向隣接ペア %d 件\\n', nm, sum(sapply(nb, function(x) if (identical(x, 0L)) 0L else length(x)))))",
  "}",
  "cat('child: 完了\\n')"
)
writeLines(child_code, child_script_path, sep = "\n")

child_stdout <- system2(
  rscript_bin,
  args = c(shQuote(child_script_path), shQuote(area_tmp_geojson), shQuote(child_out_dir)),
  stdout = TRUE, stderr = TRUE
)
child_status <- attr(child_stdout, "status")
if (is.null(child_status)) child_status <- 0L

# 子プロセスが最後まで書き切ったかどうかは終了コードでは判定できない(上の
# docstring のとおり)。子プロセスは正常終了時に必ず最後の行として
# "child: 完了" を出力するので、これが無ければ「CSVは存在するが書き込み途中
# でクラッシュして切り詰められている」可能性があるとみなし、子のログ全文を
# 添えて exit 1 する(不完全な隣接リストを黙って読み進めない)。
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
# snap=0.001(丸め幅の10倍、約111m)は「本来隣接していないポリゴンを許容幅で
# 結合してしまう過剰結合」を検出するための対照条件であり、ここで差が出ても
# 座標丸めが隣接を壊した証拠にはならない。対照条件で差が出たことを理由に
# 本採用の snap を緩めてはいけないため、diff_1_10 は採否の条件に入れない。
if (diff_0_1 == 0) {
  main_edges <- edges_snap0
  main_snap_label <- "snap=0(spdepの既定相当。snap=0.0001と隣接ペアの集合差が無かったため、人為的な結合を一切入れない値を採用)"
} else {
  main_edges <- edges_snap1
  main_snap_label <- "snap=0.0001(座標丸め幅と同程度。snap=0との間に集合差が生じたため丸め由来の隙間を吸収する値を採用)"
}

# --- 診断3: 孤立区域の列挙(本採用の隣接関係で判定) --------------------------
all_codes <- area_sf$area_code
degree_tbl <- table(factor(main_edges$area_code, levels = all_codes))
degrees <- as.integer(degree_tbl)
names(degrees) <- names(degree_tbl)

isolated_codes <- names(degrees)[degrees == 0]

# --- 診断6: 連結成分(幅優先探索。igraph 等の新規パッケージは使わない) --------
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

singleton_codes <- sort(unlist(components[comp_sizes == 1]))
components_match_isolated <- identical(singleton_codes, sort(isolated_codes))

# --- 出力(1→2→3→4→5→6 の順に並べる。子プロセスのログは付録として最後に出す) --

emit("## 3. 孤立区域(隣接0件)の列挙")
emit("")
if (length(isolated_codes) == 0) {
  emit("- 孤立区域は無し(全339区域が1件以上の隣接を持つ)。")
} else {
  emit(sprintf("- 孤立区域: %d 件", length(isolated_codes)))
  for (code in isolated_codes) {
    idx <- which(area_sf$area_code == code)
    emit(sprintf("  - %s(%s, %s)", area_sf$area_name[idx], code, area_sf$pref_name[idx]))
  }
  emit("- 離島のみで構成される医療圏(隠岐・対馬・五島等)であれば妥当。内陸の区域が")
  emit("  含まれる場合は簡略化・座標丸めの副作用を疑うこと。")
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
    "- 結論: 座標が0.0001度(約11m)に丸められているにもかかわらず、snap=0とsnap=0.0001で"
  ))
  emit(sprintf(
    "  隣接ペアの集合は完全に一致した(%d件、集合差%d件)。丸めによって生じた隙間で",
    nrow(edges_snap0), diff_0_1
  ))
  emit("  隣接が失われている形跡は無い。これは mapshaper の簡略化が共有アークを")
  emit("  1度だけ処理する(トポロジ保存)ことと整合する。")
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
    "- 結論: snap=0とsnap=0.0001の間で隣接ペアの集合に%d件の差が生じた。これまでの",
    diff_0_1
  ))
  emit("  実測(差0件)と食い違っている(入力データが差し替わった可能性がある)。")
  emit("  丸め幅と同程度のsnap=0.0001を採用し、丸め由来の隙間を吸収する。")
}
emit("")
emit(sprintf("- 本採用(adjacency_iryoken2.csv): %s", main_snap_label))
emit("")

emit("## 5. 隣接数の要約")
emit("")
emit(sprintf("- 平均: %.3f", mean(degrees)))
emit(sprintf("- 最小: %d", min(degrees)))
emit(sprintf("- 最大: %d", max(degrees)))
emit("")

emit("## 6. 連結成分")
emit("")
emit("- 空間重み行列(隣接グラフ)が連結しているかどうかは、章5(空間回帰・")
emit("  CAR/BYM)で必ず問題になる論点のため、実測して記録する。")
emit(sprintf("- 連結成分の個数: %d", length(components)))
emit("- サイズ(降順)と代表都道府県:")
for (i in seq_along(components)) {
  comp <- components[[i]]
  size <- comp_sizes[i]
  idxs <- match(comp, area_sf$area_code)
  if (size == 1) {
    emit(sprintf(
      "  - 成分%d: 1区域(孤立: %s, %s)",
      i, area_sf$area_name[idxs], area_sf$pref_name[idxs]
    ))
  } else {
    prefs <- unique(area_sf$pref_name[idxs])
    if (length(prefs) > 6) {
      pref_label <- sprintf("%s ほか%d県", paste(prefs[1:6], collapse = "、"), length(prefs) - 6)
    } else {
      pref_label <- paste(prefs, collapse = "、")
    }
    emit(sprintf("  - 成分%d: %d区域(代表: %s)", i, size, pref_label))
  }
}
emit("")
emit(sprintf(
  "- サイズ1の成分(孤立区域)は%d件で、診断3で列挙した孤立区域%d件と%s。",
  sum(comp_sizes == 1), length(isolated_codes),
  if (components_match_isolated) "一致した" else "一致しなかった(要確認)"
))
if (!components_match_isolated) {
  fail("エラー: 連結成分から求めた孤立区域(サイズ1の成分)が診断3の孤立区域と一致しません。main_edgesの対称性を確認してください。")
}
emit("")

# --- 診断7: ブリッジ(この1本で連結が決まるエッジ) --------------------------
#
# 除去すると連結成分数が増えるエッジ(グラフ理論の bridge)を、本採用の隣接
# 関係(main_edges、無向グラフとして扱う)から求める。素朴に「1本ずつ外して
# BFSし直す」方式は 1,558/2 本 × BFS で重くなりうるため、DFS 1回(Tarjan の
# ブリッジ検出)で O(V+E) にとどめる。新規パッケージはインストールしない。
# R のコールスタック上限を避けるため再帰ではなく明示スタックで書く。
find_bridges <- function(nodes, adj_list) {
  disc <- setNames(rep(NA_integer_, length(nodes)), nodes)
  low <- setNames(rep(NA_integer_, length(nodes)), nodes)
  parent <- setNames(rep(NA_character_, length(nodes)), nodes)
  visited <- setNames(rep(FALSE, length(nodes)), nodes)
  timer <- 0L
  bridges <- list()

  for (start in nodes) {
    if (visited[[start]]) next
    stack <- list(list(node = start, idx = 1L))
    visited[[start]] <- TRUE
    timer <- timer + 1L
    disc[[start]] <- timer
    low[[start]] <- timer
    while (length(stack) > 0) {
      top <- stack[[length(stack)]]
      u <- top$node
      nbrs <- adj_list[[u]]
      if (is.null(nbrs)) nbrs <- character(0)
      if (top$idx <= length(nbrs)) {
        v <- nbrs[top$idx]
        stack[[length(stack)]]$idx <- top$idx + 1L
        if (!visited[[v]]) {
          visited[[v]] <- TRUE
          timer <- timer + 1L
          disc[[v]] <- timer
          low[[v]] <- timer
          parent[[v]] <- u
          stack[[length(stack) + 1]] <- list(node = v, idx = 1L)
        } else if (!identical(v, parent[[u]])) {
          # 逆辺(バックエッジ)。単純グラフを前提とする(同一ペアの多重辺は無い)。
          low[[u]] <- min(low[[u]], disc[[v]])
        }
      } else {
        # u の子を全て見終わった。親に low を伝播し、ブリッジ条件を判定してpop。
        stack[[length(stack)]] <- NULL
        p <- parent[[u]]
        if (!is.na(p)) {
          low[[p]] <- min(low[[p]], low[[u]])
          if (low[[u]] > disc[[p]]) {
            bridges[[length(bridges) + 1]] <- c(p, u)
          }
        }
      }
    }
  }
  bridges
}

# adj_list は診断6で作成済み(main_edges から split したもの)。探索順序への
# 依存を無くすため近傍を昇順に揃える(ブリッジの集合自体は探索順序に依存しない
# グラフの性質だが、出力の決定性のため揃えておく)。
bridge_adj_list <- lapply(adj_list, function(x) sort(unique(x)))
bridges <- find_bridges(all_codes, bridge_adj_list)

code_to_pref_code <- setNames(area_sf$pref_code, area_sf$area_code)
code_to_pref_name <- setNames(area_sf$pref_name, area_sf$area_code)
code_to_area_name <- setNames(area_sf$area_name, area_sf$area_code)

order_edge <- function(e) if (e[1] <= e[2]) e else rev(e)
bridges <- lapply(bridges, order_edge)

is_cross_pref <- function(e) code_to_pref_code[[e[1]]] != code_to_pref_code[[e[2]]]
cross_pref_bridges <- Filter(is_cross_pref, bridges)
same_pref_bridges <- Filter(Negate(is_cross_pref), bridges)

# area_code 昇順で安定させる
if (length(cross_pref_bridges) > 0) {
  cross_pref_bridges <- cross_pref_bridges[order(sapply(cross_pref_bridges, function(e) e[1]))]
}

okayama_shikoku_key <- c("3301", "3706")
okayama_shikoku_found <- any(vapply(bridges, function(e) setequal(e, okayama_shikoku_key), logical(1)))

emit("## 7. ブリッジ(この1本で連結が決まるエッジ)")
emit("")
emit("- ブリッジとは、除去すると連結成分の数が増えるエッジのこと。空間重み行列")
emit("  (隣接グラフ)において、その1本の隣接判定だけで全体の連結構造が決まる")
emit("  急所であり、「隣とは何か」の判断が結果を大きく変える具体例になる。")
emit(sprintf("- ブリッジ総数: %d 件(無向グラフとして判定)", length(bridges)))
emit(sprintf("- うち都道府県をまたぐもの: %d 件", length(cross_pref_bridges)))
emit(sprintf("- うち同一都道府県内: %d 件(詳細は割愛)", length(same_pref_bridges)))
emit("")
if (length(cross_pref_bridges) > 0) {
  emit("都道府県をまたぐブリッジの一覧:")
  emit("")
  for (e in cross_pref_bridges) {
    emit(sprintf(
      "  - %s(%s, %s) <-> %s(%s, %s)",
      code_to_area_name[[e[1]]], e[1], code_to_pref_name[[e[1]]],
      code_to_area_name[[e[2]]], e[2], code_to_pref_name[[e[2]]]
    ))
  }
  emit("")
}
if (okayama_shikoku_found) {
  emit("- 3301<->3706(岡山県 県南東部 <-> 香川県 東部)はブリッジとして検出された。")
  # 断定を避けるため、このエッジを除いたときに実際に分かれる連結成分の大きさを
  # 実測する(「本州側n区域」のような未確認の数字を書かないため)。
  edges_wo_bridge <- main_edges[
    !((main_edges$area_code == "3301" & main_edges$neighbor_code == "3706") |
      (main_edges$area_code == "3706" & main_edges$neighbor_code == "3301")),
  ]
  adj_list_wo_bridge <- split(edges_wo_bridge$neighbor_code, edges_wo_bridge$area_code)
  reach_from <- function(start) {
    seen <- setNames(rep(FALSE, length(all_codes)), all_codes)
    seen[[start]] <- TRUE
    queue <- start
    while (length(queue) > 0) {
      cur <- queue[1]
      queue <- queue[-1]
      nbrs <- adj_list_wo_bridge[[cur]]
      if (!is.null(nbrs)) {
        for (nb in nbrs) {
          if (!seen[[nb]]) {
            seen[[nb]] <- TRUE
            queue <- c(queue, nb)
          }
        }
      }
    }
    names(seen)[seen]
  }
  side_3301 <- reach_from("3301")
  side_3706 <- reach_from("3706")
  emit(sprintf(
    "  このエッジを除くと、3301側は%d区域、3706側は%d区域に分かれる(実測)。",
    length(side_3301), length(side_3706)
  ))
  emit("  この1本が両側の連結・非連結を決めている(診断6参照)。")
} else {
  emit("- **3301<->3706(岡山県 県南東部 <-> 香川県 東部)がブリッジとして検出")
  emit("  されなかった。実装かグラフの扱いのどちらかが誤っている可能性が高いため、")
  emit("  そのまま報告する。**")
}
emit("")

emit("## 付録: poly2nb 子プロセスの実行ログ")
emit("")
emit(paste(child_stdout, collapse = "\n"))
emit(sprintf(
  "(子プロセスの終了コード: %s — 上の docstring のとおり、計算後のプロセス終了時クラッシュにより非ゼロになりうる。完了マーカーの有無で成否を判定する。)",
  child_status
))
emit("")

# --- 出力: 診断markdown ------------------------------------------------------
diag_md_path <- file.path(out_dir, "adjacency_diagnostics.md")
con <- file(diag_md_path, open = "wb")
writeLines(enc2utf8(diag_lines), con, useBytes = TRUE, sep = "\n")
close(con)
cat(sprintf("診断結果を書き出しました: %s\n", diag_md_path))

# --- 出力: iryoken2.geojson(属性を絞る) -------------------------------------
area_out <- area_sf[, c("area_code", "area_name", "pref_code", "pref_name", "boundary_source")]
area_geojson_path <- file.path(out_dir, "iryoken2.geojson")
if (file.exists(area_geojson_path)) unlink(area_geojson_path)
st_write(area_out, area_geojson_path, driver = "GeoJSON", quiet = TRUE)
cat(sprintf("書き出しました: %s\n", area_geojson_path))

# --- 出力: prefecture.geojson ------------------------------------------------
pref_geojson_path <- file.path(out_dir, "prefecture.geojson")
if (file.exists(pref_geojson_path)) unlink(pref_geojson_path)
st_write(pref_sf, pref_geojson_path, driver = "GeoJSON", quiet = TRUE)
cat(sprintf("書き出しました: %s\n", pref_geojson_path))

# --- 出力: adjacency_iryoken2.csv(area_code昇順・neighbor_code昇順) --------
adj_df <- main_edges[order(main_edges$area_code, main_edges$neighbor_code), ]
adj_csv_path <- file.path(out_dir, "adjacency_iryoken2.csv")
con <- file(adj_csv_path, open = "wb")
writeLines("area_code,neighbor_code", con, sep = "\n")
if (nrow(adj_df) > 0) {
  writeLines(paste(adj_df$area_code, adj_df$neighbor_code, sep = ","), con, sep = "\n")
}
close(con)
cat(sprintf("書き出しました: %s(%d 行)\n", adj_csv_path, nrow(adj_df)))

# 一時ファイルの片付け
unlink(area_tmp_geojson)
unlink(child_script_path)
unlink(child_out_dir, recursive = TRUE)

cat("build_geo.R 完了。\n")
quit(status = 0)
