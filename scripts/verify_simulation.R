#!/usr/bin/env Rscript
# -*- coding: utf-8 -*-
#
# verify_simulation.R — spdep を使った合成データの再確認スクリプト(R側)。
#
# R 4.5.2 / spdep 1.4.1 で実行して動作確認済み(2026-08-18)。
# scripts/verify_simulation.py(Python版)と出力が一致することを確認した実測値:
#   Global Moran's I = 0.3921418, ランダム化の期待値 = -0.0029325513,
#   moran.mc 疑似p値 = 0.0010, LISA の HH 9/9・LL 9/9・HL 1/1,
#   area_id=269 の Gi* z = 0.152。
#
# 【注意】spdep::mat2listw() は使わない。この環境では mat2listw() を呼ぶと、
# 出力自体は最後まで正常に出るのにプロセス終了時にスタックオーバーフロー
# (Windows 0xC00000FD、Git Bash では終了コード127)で異常終了する。行列サイズに
# よらず再現し、rm()/gc()/明示的なquit()でも回避できない。隣接はもともとエッジ
# 一覧のCSVで与えられているので、nb オブジェクトを直接組み立てて回避している。
#
# scripts/verify_simulation.py(標準ライブラリのみで自前実装したPython版)と
# 同じ検証を、spdep::moran.test / spdep::localmoran / spdep::localG を使って
# 行う。Python版が「自前実装」であるのに対し、本スクリプトは実績のあるRパッケージ
# による再確認という位置づけなので、あくまで短く保つ。
#
# 使い方(想定):
#   Rscript scripts/verify_simulation.R
#   Rscript scripts/verify_simulation.R --data-dir data/simulated --permutations 999

suppressPackageStartupMessages({
  library(spdep)
})

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(flag, default) {
  idx <- which(args == flag)
  if (length(idx) == 0 || idx == length(args)) return(default)
  args[idx + 1]
}

data_dir <- get_arg("--data-dir", "data/simulated")
permutations <- as.integer(get_arg("--permutations", "999"))
hotspot_threshold <- 1.96

areas_path <- file.path(data_dir, "lattice_areas.csv")
neighbors_path <- file.path(data_dir, "lattice_neighbors.csv")

areas <- read.csv(areas_path, stringsAsFactors = FALSE)
nb_edges <- read.csv(neighbors_path, stringsAsFactors = FALSE)

n <- nrow(areas)
areas <- areas[order(areas$area_id), ]
ids <- areas$area_id

# area_id -> 1..n の連番位置に変換した隣接リストを組み立てる。
# spdep::mat2listw は使わない(この環境では呼ぶだけでプロセスがスタックオーバーフローで
# 異常終了するため。詳細は上のコメント参照)。隣接はもともとエッジ一覧の CSV で
# 与えられているので、nb オブジェクトを直接作るほうが素直でもある。
pos <- setNames(seq_len(n), as.character(ids))
nb <- split(
  unname(pos[as.character(nb_edges$neighbor_id)]),
  factor(unname(pos[as.character(nb_edges$area_id)]), levels = seq_len(n))
)
# 隣が0個の地域は spdep の約束どおり 0L で表す
nb <- lapply(nb, function(v) if (!length(v)) 0L else as.integer(sort(v)))
names(nb) <- NULL
class(nb) <- "nb"
attr(nb, "region.id") <- as.character(ids)
attr(nb, "sym") <- TRUE

listw <- nb2listw(nb, style = "W")  # 行標準化(row-standardized)

x <- areas$rate_per_100k

# --- 条件1: Global Moran's I ------------------------------------------------
cat("== Global Moran's I ==\n")
mt <- moran.test(x, listw, randomisation = TRUE)
print(mt)

mc <- moran.mc(x, listw, nsim = permutations)
cat(sprintf("moran.mc 疑似p値(nsim=%d): %.4f\n\n", permutations, mc$p.value))

# --- 条件2・3: Local Moran's I(LISA) ----------------------------------------
cat("== Local Moran's I(LISA) ==\n")
lm <- localmoran(x, listw)
quadrant <- attr(lm, "quadr")$mean  # spdepの4象限分類(High-High/Low-Low/High-Low/Low-High)

truth <- areas$truth_label
cat("truth_label=HH のうち LISA=High-High:", sum(quadrant[truth == "HH"] == "High-High"),
    "/", sum(truth == "HH"), "\n")
cat("truth_label=LL のうち LISA=Low-Low:", sum(quadrant[truth == "LL"] == "Low-Low"),
    "/", sum(truth == "LL"), "\n")

hl_idx <- which(truth == "HL")
cat("truth_label=HL のうち LISA=High-Low:", sum(quadrant[hl_idx] == "High-Low"),
    "/", length(hl_idx), "\n\n")

# --- 条件3: Getis-Ord Gi*(自分を含む近傍) -----------------------------------
cat("== Getis-Ord Gi* ==\n")
listw_incl_self <- nb2listw(include.self(listw$neighbours), style = "B")  # 二値重み・自分を含む
gi <- localG(x, listw_incl_self)

for (i in hl_idx) {
  cat(sprintf(
    "area_id=%d: rate=%.1f / Gi* z=%.3f (hot spot閾値%.2fを%s)\n",
    ids[i], x[i], gi[i], hotspot_threshold,
    ifelse(gi[i] >= hotspot_threshold, "超過", "超過せず")
  ))
}
