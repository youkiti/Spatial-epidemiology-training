# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このリポジトリの現状

**Phase0 と概念パート6章が完了（2026-08-18）。** 設計文書・サイト骨格・クイズエンジン・概念パート全6章が main に入り、GitHub Pages で公開されている。

公開先: <https://youkiti.github.io/Spatial-epidemiology-training/>

残っている issue は3系統。**着手前に必ず GitHub の issue 本文を読むこと**（受け入れ条件と cloud 可否がそこに書いてある）。

| 系統 | issue | この環境で動かせるか |
|---|---|---|
| Phase1 データ整備 | #4・#7・#8 完了。#9（施設の二次医療圏割付）も完了（診療の場のみ・主系列の割付率85.9%、詳細は下記）。**#5（人口）は年齢階級別人口が未取得のため未完了**（総人口のみ取得済み。詳細は下記「Phase1のデータ整備状況」） | e-Stat からの年齢階級別人口取得が要る |
| Phase2 引用の裏取り | #16 実例論文2本の一次資料での確認 | 論文全文にアクセスできれば可 |
| Phase3 ハンズオン | #17 Rmd 配管 → #18〜#20 | **不可**。R が要る。#17 が #18〜#20 の前提 |

クラウドセッションで単独で進められるのは #16 だけ。

```
documents/       設計の正本3文書。実装より先にここを読む
docs/            MkDocs のサイトソース。ここに置いたものは公開される
  concepts/      概念パート6章（issue #10〜#15 で執筆済み。各章に自己チェック3問＋章末クイズ10問。章4のみ12問）
  handson/       Rハンズオン4本（プレースホルダ）
  assets/js/     クイズエンジン（storage.js → quiz.js → progress.js）
  assets/data/   クイズJSON（全6章分。`quiz-chN-selfcheck.json` と `quiz-chN.json`）
  memo.md        ユーザーとの対話ログ。exclude_docs でサイトからは除外している
scripts/         quiz_lint.py（作問の機械チェック）、simulate_spatial_data.py と
                 verify_simulation.py（合成データの生成と検証。issue #6）、
                 fetch_meibo.py / parse_meibo.py（専門医名簿PDFの取得と抽出。issue #7・#8）、
                 build_geo.R（境界データと隣接関係の生成。issue #4）、
                 build_population.py（人口データの取得。issue #5）、
                 build_facility_reference.py / link_facilities.py /
                 verify_facility_linkage.py / lib_facility_name.py /
                 propose_crosswalk.py（施設の名寄せと二次医療圏割付。issue #9）
data/simulated/  上記生成器の出力CSV（合成データなのでコミットしている）
data/geo/        二次医療圏・都道府県の境界データと queen contiguity。詳細は data/geo/README.md
data/processed/  専門医数CSV（都道府県別・施設別・二次医療圏別）と人口CSV
                 （詳細は「Phase1のデータ整備状況」と data/processed/README.md）
data/curated/    施設名寄せの人手判断（facility_crosswalk.csv）。詳細は data/curated/README.md
overrides/       404.html のテーマオーバーライド
```

### Phase1のデータ整備状況

- **都道府県別の専門医数**（`data/processed/specialists_prefecture.csv`）は名簿PDFの
  公式集計（1ページ目）由来で完全
- **二次医療圏レベルの分子**（`data/processed/specialists_iryoken2.csv`）は名簿本体
  （施設ベース、`specialists_facility.csv`）の施設名を医療情報ネット・国土数値情報P04の
  参照点テーブルに突合し、座標割付済み（issue #9）。**「診療の場かどうか」（`care_setting`
  列）に応じて2系列を出す**（ユーザー指摘: 国立感染症研究所は診療機関ではない、を受けた
  設計変更）。主系列 `n_specialists_care`（診療の場のみ）の全国合計は1,626名（割付率
  85.9%）、`n_specialists_all`（勤務地ベース。care+non_care）は1,654名（割付率87.3%）。
  施設名自体を特定できたのは1,656名（87.4%）だが、うち2名（長崎県の施設）は参照点の座標が
  どの二次医療圏ポリゴンにも入らないため地図には反映されない（この差はcare/all両系列に
  共通）。残り163名は施設名が公表データに見つからず未割付、59名は名簿に施設の記載が無い・
  国外で割付不可、16名は診療を行わない勤務先（`non_care_workplace`）で所在の参照点も
  特定できず割付不可、28名は所在は判明したが診療を行わない勤務先（研究機関・保健所・
  製薬企業等）なので主系列には含まれない。欠測が地図の模様を作っていないこと（県別の
  割付率(care基準)と専門医密度の相関が弱いこと）を `scripts/verify_facility_linkage.py`
  が検算している。詳細は `data/processed/README.md` と
  [docs/handson/04-case-study.md](docs/handson/04-case-study.md) 「データの制約」節
- **人口**（`data/processed/population_iryoken2.csv` / `population_prefecture.csv`）は
  総人口のみ。年齢階級別は未取得（issue #5 の残り）

### コマンド

```bash
pip install -r requirements.txt
mkdocs build --strict                      # CI と同じ検査。警告ゼロ・exit 0 で通ること
mkdocs serve                               # クイズは fetch を使うので file:// 直開きでは動かない
python scripts/quiz_lint.py                # クイズJSONの testwiseness cue 検査
python scripts/verify_facility_linkage.py  # 施設の名寄せ・二次医療圏割付（issue #9）の受け入れ条件検査
```

ビルド出力の読み方に罠がある:

- 出力に出る "Warning from the Material for MkDocs team"（MkDocs 2.0 の告知）は**ビルド警告ではない**。警告ゼロの判定に数えない
- `git-revision-date-localized` の `has no git logs` も同様で、プラグインが直接 print しており `--strict` を落とさない。つまり **CI から `fetch-depth: 0` を外してもビルドは緑のまま、各ページの更新日時だけが静かに壊れる**。外さないこと
- Windows では出力をパイプに繋ぐと `$?` が `tail` 側の終了コードになる。ログにリダイレクトして終了コードを直接見ること

### データ整備側の罠

- **医療情報ネットの一括公開ファイルは都道府県ごとに網羅性が大きく違う**（実測で沖縄県は診療所91件、京都府は626件しか無い）。P04（国土数値情報）を併用しないと、医療情報ネットに載っていない大病院（`島根県立中央病院`など）が座標を持てず未割付になる。詳細は [documents/DATA_SOURCES.md](documents/DATA_SOURCES.md) の「施設の座標データ」節

### 設計の正本は documents/ にある

**新しい章・クイズ・ハンズオンを作る前に、必ずこの3文書を読むこと。** 以降の実装はここに拘束される。

| 文書 | 何が決まっているか |
|---|---|
| [documents/要件定義書.md](documents/要件定義書.md) | 目的・想定読者・設計原則・技術構成・非目標・TBD |
| [documents/カリキュラム設計.md](documents/カリキュラム設計.md) | 6章の学習目標とクイズ問数、**章↔issue 対応表**、ハンズオン4本 |
| [documents/作問ガイドライン.md](documents/作問ガイドライン.md) | 作問原則と lint 閾値。`scripts/quiz_lint.py` の正本 |

[docs/memo.md](docs/memo.md) はこの3文書の元になった対話ログ。一次資料として残してあるが、**食い違ったら documents/ が優先**。

### サイト実装で守ること（既知の罠）

- **`theme.features` に `navigation.instant` を入れない。** 全JSがフルページロード前提の初期化のため、SPA的ページ遷移では描画されなくなる
- **`extra_javascript` の読み込み順は依存順**（`storage.js` → `quiz.js` → `progress.js`）。変えない
- **クイズはページとJSをデータ属性で疎結合にする契約。** `data-quiz-gate` **無し**=自己チェック（合否は出すが保存しない）、**有り**=章末クイズ（合格を localStorage に保存）。`data-quiz-src` のパスは directory URL 基準の相対
- **クイズJSONスキーマは ai-kotohajime と同一に保つ**: `{title, passRatio, questions:[{q, choices[4], answer, explanation}]}`。**`answer` は 0-origin**
- **`extra.css` にハードコード色を足すときは、ダーク（slate）配色の上書きも必ず併せて書く。** 特に文字色は暗背景でコントラストが落ちる
- 404 は `docs/404.md` では機能しない。テーマの静的テンプレート `404.html` が常に優先され、GitHub Pages はルートの `404.html` しか配信しない。`overrides/404.html` のリンクは**ルート相対**（`/Spatial-epidemiology-training/...`）で書く
- 作問の lint 閾値を変えるときは、`documents/作問ガイドライン.md` §3 と `scripts/quiz_lint.py` を**同時に**改訂する
- **ページ間リンクはソース相対の `.md` で書く**（`ch2-spatial-weights.md`、`../handson/03-maup.md`）。ディレクトリURL形式（`../ch2-spatial-weights/`）はブラウザ上は動くが MkDocs がリンクとして解決できず、`INFO ... unrecognized relative link` が出るだけで **`--strict` でも落ちない**。リンク切れを検出できない状態になる
- **`pymdownx.arithmatex` は有効化していない**（`mkdocs.yml` のコメント参照）。`$W$` のような LaTeX 記法はドル記号ごとそのまま表示される。数式は書かず、`W` やコードブロックで表現する
- **inline SVG で `currentColor` の塗りの上に `currentColor` の文字を置くとき、`fill-opacity` は 0.45 まで**。それ以上だと地の色と文字色が同一になり、ライト/ダーク両方で**文字が消える**。濃淡は 0.05〜0.45 の範囲で付ける（`extra.css` を触らずにテーマ追従させるための制約とセット）
- **クイズJSONの文字列に Markdown 記法を書かない。** `quiz.js` は JSON 由来の文字列を `textContent` で DOM に入れる（JSON由来の文字列をHTMLとして解釈させないための意図的な設計。`quiz.js` 冒頭の実装方針に明記されている）ため、`Gi\*` のエスケープやバックティックが**そのまま文字として表示される**。本文（Markdown）では `Gi\*` が正しく、クイズJSONでは `Gi*` が正しい
- **`<figure>` 内の inline SVG には `width` 属性を必ず書く。** Material の `.md-typeset figure` は `width: fit-content` であり、SVG に `width` が無いと `width:auto` が「親幅の100%」に解決され、親が fit-content なので循環して 0×0 になり描画されない。figcaption があるとそのテキストが figure に幅を与えるため偶然描画できてしまい、気づきにくい。`mkdocs build --strict` でも `quiz_lint.py` でも検出できない
- **`fill="currentColor"` + `fill-opacity` の塗りは、ダークテーマで濃淡が反転する。** ライトテーマでは値が高いほど濃く見えるが、ダークでは値が高いほど明るく見える。図の凡例やキャプションに「濃い/薄い」と書くとダークで読む読者には逆の意味になるため、「塗りが強い/弱い」のような極性に依存しない語を使う。これも `mkdocs build --strict` や `quiz_lint.py` では検出できない

## プロジェクトの目的

**一定の疫学の素養がある読者向けの、空間疫学（地理疫学）教材。** 2つのパートからなる:

1. **概念パート** — 理論・ビジュアル・具体例を*並列に*提示し、クイズを解きながら進む。各概念に理解確認のクイズが紐づく
2. **Rハンズオン（Rmd）** — 同じ概念を R で手を動かして再現する

設計思想は <https://github.com/youkiti/ai-kotohajime> から輸入している（同一著者。クイズエンジンの移植元でもある）。

### 題材（ケーススタディ）

**感染症専門医の地域偏在の可視化。** データ源は日本感染症学会の専門医名簿 PDF（2026-07-01 版）:
<https://www.kansensho.or.jp/uploads/files/senmoni/meibo_260701.pdf>

**このPDFはリポジトリにまだ無い。** 取り込む際の注意:

- 名簿は個人名と所属を含むが公開データであるため処理してよい。**リポジトリには加工過程のコードと出力図表のみを保持する**（`data/raw/` と `data/interim/` は `.gitignore` 済み）
- データにアクセスできなくなったときのため、**シミュレーションデータでも全章が走る**ようにする
- **分子（専門医数）だけを地図にしてはいけない** — 教材自身が「落とし穴」で戒めている誤りそのもの。人口（分母）と対にして人口10万対専門医数を出す。医師偏在の文脈では需要指標（高齢者割合など）での標準化も検討対象
- PDF は改訂されうる。取得日をファイル名かメタデータに残す

## 教材の骨格

章立て・学習目標・クイズ問数の確定版は [documents/カリキュラム設計.md](documents/カリキュラム設計.md) にある。以下はその要点。

| 段階 | 質問 | 手法 |
|---|---|---|
| 1 記述 | どこで多い？ | 率・有病率・標準化率、SIR/SMR、choropleth map |
| 2 パターン | 集まっている？ | Global Moran's I、Local Moran's I (LISA)、Getis-Ord Gi*、spatial scan statistic |
| 3 説明 | なぜそこに多い？ | 通常回帰、spatial regression、CAR / BYM |

### 教材が最重要視している論点

- **「地図を描く」と「空間統計」は別物。** 色を塗っただけでは「本当に集まっている」とは言えない、という区別が教材全体の出発点
- **Gi\* / LISA / SaTScan の違い**（memo.md 635行目以降がまるごとこの説明＝ユーザーが明示した躓きポイント）。Gi\* は「塊探し」、LISA は「自分と周囲の関係の分類」（High-High / Low-Low / High-Low / Low-High）、SaTScan は「異常に患者が多い地理的範囲の探索」。特に **「値が高い」と「hot spot である」は別**（周囲が低ければ単独の高値は High-Low の空間的アウトライヤーであって hot spot ではない）という区別を、必ず具体的な数値グリッドで示すこと
- **空間重み行列（「隣」の定義）を先に決める。** 普通の統計に無い発想として強調する。queen contiguity / 距離閾値
- **5つの落とし穴** — 人口の多さの無視、小地域の少数例による率の不安定、MAUP、生態学的誤謬、「隣」の定義の事後決定

### 教材として使う実例論文

- Blazel MM, et al. *JAMA Netw Open.* 2024;7:e2429764 — 高血圧。地図 → Moran's I → Bayesian CAR Poisson model。**Moran → 空間回帰**まで通す例
- Pradhan P, Iyer HS, Rebbeck TR. *JAMA Netw Open.* 2025;8:e2537905 — 米国 counties のがん検診。queen contiguity → Global Moran's I → LISA。**Global → Local の対比**を見せる例
- 総説4本: Elliott & Wartenberg 2004 (EHP)、Auchincloss et al. 2012 (Annu Rev Public Health)、Beale et al. 2008 (EHP)、Hu et al. 2025 (Front Public Health)

**これらの統計値・書誌情報は対話ログ由来で、一次資料での裏取りが済んでいない（issue #16 の担当）。** 具体的な数値を断定的に書かないこと。

## 環境（検証済み・2026-08-18）

| ツール | バージョン |
|---|---|
| R | 4.5.2 |
| Quarto | 1.8.26 |
| Pandoc | 3.8.3 |
| Node / npm | 22.21.0 / 10.9.4 |
| Python | 3.11.9 |

サイト側の依存は `requirements.txt` にピン留め済み（mkdocs 1.6.1 / mkdocs-material 9.7.6 / mkdocs-git-revision-date-localized-plugin 1.5.3）。**CI に R は入れない** — Rmd は事前レンダリングして成果物をコミットする。

R パッケージ:

- **導入済み**: `sf` 1.0.21, `spdep` 1.4.1, `spatialreg` 1.4.2, `ggplot2` 4.0.1, `dplyr` 1.1.4, `rmarkdown` 2.30, `knitr` 1.50
- **未導入**: `tmap`, `sfdep`, `leaflet`, `SpatialEpi`, `CARBayes`, `INLA`, `jpndistrict`, `NipponMap`

Global/Local Moran's I と Gi\* は `spdep` だけで完結する（`moran.test` / `localmoran` / `localG`）ので、段階1〜2 は追加インストールなしで書ける。CAR/BYM に進む時点で `CARBayes` か `INLA` の選択が必要。**`INLA` は CRAN ではなく専用リポジトリからの導入**で、読者に要求するハードルが `CARBayes` より高い。

**`spdep::mat2listw()` はこの環境でプロセス終了時にクラッシュする。** R の出力自体は最後まで正常に出るが、終了時にスタックオーバーフローで異常終了する（Windows 終了コード 0xC00000FD、Git Bash 経由では 127）。行列サイズによらず再現し、`rm()` / `gc()` / `quit(status=0)` でも回避できないため、`Rscript foo.R && echo ok` が決して成功しない。**どうするか**: `nb` オブジェクトを隣接エッジ一覧から直接組み立てて `nb2listw()` に渡す（密な隣接行列を経由しない）。`scripts/verify_simulation.R` がその実装例。

**`spdep::poly2nb()` も同じくプロセス終了時に落ちる**（Git Bash 経由で終了コード 255）。`mat2listw()` と同種だが、今回は `poly2nb()` 自体がトリガー。実ポリゴンから隣接を導くのに `poly2nb()` は避けられないため、**呼び出しだけを子プロセスの `Rscript` に切り出し、結果をCSVに書かせてから親が読み戻す**のが回避策（`scripts/build_geo.R` が実装例）。**終了コードで成否を判定しないこと** — 代わりに (a) 出力先が毎回新しい tempdir か、(b) 子が完了マーカーを stdout に出したか、で判定する。ファイルの存在チェックだけだと、書き込み途中で切れたCSVを黙って読んでしまう。

**実ポリゴンを扱うときは `sf::sf_use_s2(FALSE)` が要る。** s2 有効のままだと `st_make_valid()` が一部ジオメトリを修復しきれず（実測: 新宮 3007）、`poly2nb()` がさらに強く落ちる。A38 由来の339区域では7件が `st_is_valid()` で不正、s2 を切れば `st_make_valid()` で全件修復できる。

**`pip install -r requirements.txt` は Windows ローカルで失敗する。** `requirements.txt` に日本語コメントがあるため pip が locale（cp932）で読もうとして `UnicodeDecodeError`。**`PYTHONUTF8=1` を付ければ通る。** CI（ubuntu-latest）は UTF-8 locale なので起きない。**しかも pip が終了コード0を返すことがあり**、あとで `No module named mkdocs` で気づくことになる。

`scripts/verify_simulation.R` は R 4.5.2 / spdep 1.4.1 で実行・検証済み（2026-08-18）で、Python 版と出力が一致することを確認済み。

**R側の依存マニフェスト（`renv.lock` 等）はまだ無い。** Rハンズオン（issue #17〜#20）に着手する時点で入れる。

## 決定済み（もう議論しない）

過去に未決定だった項目のうち、以下は決着している。詳細と理由は [documents/要件定義書.md](documents/要件定義書.md)。

- **公開ページの実装手段** = Material for MkDocs + GitHub Pages（Quarto Website ではない）
- **地域単位** = 二次医療圏をメイン、都道府県も併走（MAUP の実演を兼ねる）
- **記述言語** = 日本語のみ（i18n は入れない）
- **境界データの入手元** = 国土数値情報の医療圏データ（A38）。隣接リポジトリ <https://github.com/youkiti/visualize-regional-medical-care-for-2040> の `doc/DATA_SOURCES.md` に取得手順と罠が文書化されている
- **架空データと実データの役割分担** = 架空の10市町村データは概念導入用、専門医名簿はケーススタディ専用
- **簡略化済み（表示専用）GeoJSON を隣接判定に使ってよいか** = 使ってよい。`snap=0` と `snap=0.0001`（座標丸め幅と同程度）で queen contiguity の隣接ペアが完全一致した（1,558件、集合差0件）ため、0.0001度丸めは隣接判定に影響していない。本採用は `snap=0`。測定手順と全診断は `scripts/build_geo.R` と `data/geo/adjacency_diagnostics.md`

## 未決定事項（実装前にユーザーに確認する）

1. **ライセンス**（CC BY 4.0 が候補）
2. **修了証（目録）を出すか** — ai-kotohajime には `certificate.js` があるが移植していない
3. **SaTScan を実演するか、概念紹介にとどめるか** — 章4で考え方は必ず扱うが、別ソフトウェアを動かすハンズオンにするかは未決
4. **CAR/BYM の実装を `CARBayes` にするか `INLA` にするか** — issue #19 着手時に確定する

## 執筆上の注意

- 読者は疫学の素養がある前提。率・標準化・交絡の基礎説明は省いてよいが、**空間統計に固有の概念**（空間自己相関、空間重み行列、MAUP、空間的アウトライヤー）は丁寧に扱う
- 公開ページに載せる数値（Moran's I の値、prevalence ratio、論文の書誌情報など）は**原著で確認する**。memo.md 由来の数値をそのまま載せない。`verify-slide-citations` スキルが引用検証に使える
- クイズを書いたら `python scripts/quiz_lint.py` を通す。**閾値を緩めて通すのではなく、設問と選択肢の方を直す**。日本語の四択では L3（選択肢の最長/最短比 1.5 以内）と L2（正答肢長/平均 0.8〜1.3）が特に効く
