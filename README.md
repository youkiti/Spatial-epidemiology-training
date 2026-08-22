# 空間疫学入門(Spatial-epidemiology-training)

一定の疫学の素養がある読者(公衆衛生大学院生、臨床疫学を学ぶ医療者、行政・研究機関で保健統計を扱う担当者)を対象にした、空間疫学(地理疫学)の教材です。

**公開サイト: <https://youkiti.github.io/Spatial-epidemiology-training/>**

この教材の出発点は「**地図を描くことと空間統計を行うことは別物である**」という区別です。choropleth map で色を塗るところまでは多くの教材が扱いますが、その先の「本当に集まっているのか」を検定する発想 — 空間自己相関、空間重み行列 — までを一続きで扱います。

## 何が入っているか

| パート | 内容 |
|---|---|
| 概念パート(全6章) | 記述 / 空間重み行列 / Global Moran's I / LISA・Gi\*・SaTScan / 説明(空間回帰・CAR/BYM) / 落とし穴。各章に自己チェック3問と章末クイズ10問(章4のみ12問) |
| R ハンズオン(3本+環境準備) | ⓪環境準備、①地図→Moran's I→LISA→Gi\*、②CAR/BYM、③MAUP の実演(都道府県 vs 二次医療圏) |
| ケーススタディ資料 | 感染症専門医の地域偏在データが何を数えていて何を数えていないか(ハンズオン②③が使う実データの制約) |

クイズはブラウザ内で完結し、採点結果を外部に送信しません(進捗は `localStorage` にのみ保存)。

## ディレクトリ

```
documents/       設計の正本3文書(要件定義書・カリキュラム設計・作問ガイドライン)と
                 データ出典(DATA_SOURCES.md)・引用検証の記録
docs/            MkDocs のサイトソース(ここに置いたものが公開される)
  concepts/      概念パート6章
  handson/       R ハンズオン。md と図は analysis/handson/*.Rmd からの生成物
  assets/        クイズエンジン(JS)とクイズJSON
analysis/        ハンズオンの .Rmd ソースと renv.lock
scripts/         データ整備・検算・レンダリングのスクリプト
data/            合成データ、境界データ、加工済みCSV(生データはコミットしない)
```

## 動かす

サイトのビルドとチェック(Python のみ。R は不要):

```bash
pip install -r requirements.txt

mkdocs serve                                # ローカルプレビュー(file:// 直開きではクイズが動かない)
mkdocs build --strict                       # CI と同じ検査。警告ゼロ・exit 0 で通ること

python -m compileall -q scripts             # scripts/ 配下の Python の構文検査
python scripts/quiz_lint.py                 # クイズJSONの作問チェック
python scripts/check_links.py               # 内部リンク・画像パスの検査(site/ をビルドしてから)
python scripts/check_handson_fresh.py       # ハンズオン生成物が Rmd と一致しているか
python scripts/verify_facility_linkage.py   # 施設名寄せ・二次医療圏割付の受け入れ条件
python scripts/verify_simulation.py --sweep # 合成データの受け入れ条件と Moran's I の単調性
```

上の7つはすべて CI の必須ゲートです(`.github/workflows/ci.yml`)。いずれも標準ライブラリだけで動きます。

データを取り直す・作り直すときだけ追加の依存が要ります:

```bash
pip install -r requirements-data.txt
```

R ハンズオンを再レンダリングする(ローカル専用。**CI に R は入れません**):

```bash
Rscript scripts/render_handson.R
```

Windows では `pip install` に `PYTHONUTF8=1` を付けてください(requirements ファイルの日本語コメントを cp932 で読もうとして失敗し、しかも終了コード0を返すことがあります)。

## 再現性について

- **R の依存は `analysis/renv.lock` が正本**です。`analysis/` を作業ディレクトリにして R を起動し、`renv::restore()` を実行してください。空のプロジェクトライブラリから完走することを実測で確認しています(Posit Public Package Manager の 2025-11-01 スナップショットに固定)。
- **`renv.lock` は「`renv::restore()` で再現できる依存関係の組」の記録であり、コミット済みの図を生成した環境の記録ではありません。** 図はシステムライブラリ(`ggplot2` 4.0.1)で生成されており、lock 側は `ggplot2` 4.0.0 です。理由と経緯は [analysis/README.md](analysis/README.md) に書いてあります。
- ハンズオンの md・図・配布用 `.Rmd` は生成物で、`analysis/render_manifest.json` に SHA-256 が記録されています。`scripts/check_handson_fresh.py` が R を実行せずに照合するため、Rmd だけ直して再生成し忘れると CI が落ちます。

## データの出典

出典・取得日・利用条件・生成コマンドは [documents/DATA_SOURCES.md](documents/DATA_SOURCES.md) が正本です。

専門医名簿(日本感染症学会)の**生データと中間生成物はコミットしていません**(個人名と所属を含むため)。リポジトリが保持するのは加工過程のコードと、氏名を含まない集計値(都道府県別・二次医療圏別に加え、施設単位の集計値を含みます)です。氏名を含まないことは、施設名と公開名簿を突合した個人単位の推定が一切できないことを意味しません。詳細と利用上の注意は [data/processed/README.md](data/processed/README.md) を参照してください。データにアクセスできない環境でも学習が止まらないよう、概念パートと⓪①のハンズオンは合成データだけで完結します。

## ライセンス

| 対象 | ライセンス |
|---|---|
| 教材(`docs/` の文章・図・クイズ、`documents/`、この README、`analysis/` の .Rmd の地の文とそこから生成される図) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) |
| コード(`scripts/`、`analysis/` の .Rmd(コードチャンク)、`docs/assets/js/`、`.github/`) | [MIT](LICENSE-CODE) |
| 外部データに由来するファイル(`data/` の一部) | 各出典の利用条件([documents/DATA_SOURCES.md](documents/DATA_SOURCES.md)) |

詳細と表示例は [LICENSE](LICENSE) を参照してください。

クイズエンジンは同一著者による [ai-kotohajime](https://github.com/youkiti/ai-kotohajime) からの移植です。
