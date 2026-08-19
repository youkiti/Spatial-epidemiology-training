# renv のロックファイル形式を明示的に version 1(Hash/Requirements 付きの旧・圧縮形式)
# に固定する。既定(version 2)は再スナップショットのたびに CRAN 由来レコードの Hash を
# 書き出さない仕様(analysis/README.md 参照)なので、ここで固定しないと issue #18〜#20 で
# renv::snapshot() し直した瞬間に analysis/renv.lock が黙って version 2 へ戻り、Hash が
# 全部消える。activate.R より先に設定すること(activate.R 自体は解釈しないが、その後の
# renv::snapshot() 等の呼び出しがこのオプションを見る)。
options(renv.lockfile.version = 1)

source("renv/activate.R")
