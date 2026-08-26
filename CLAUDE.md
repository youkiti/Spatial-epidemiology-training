# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このリポジトリの現状

**Phase0〜Phase3 が完了し、GitHub Pages で公開されている（2026-08-22時点）。** 設計文書・サイト骨格・クイズエンジン・概念パート全6章・Phase1のデータ整備・引用の一次資料での裏取り・Rハンズオン本編3本が main に入っている。**納品前監査（2026-08-21）で起票された issue #44〜#55 の12件（監査 F-01〜F-12 対応）のうち11件はクローズ済み。** その後のコントラスト関連 issue #64・#65・#66・#68・#71 もクローズ済み。**現在 open な issue は #54（監修体制。独立監修は置かない方針は 2026-08-21 のユーザーコメントで決着済みで、正本文書への反映も済んでいる。残るのはユーザー自身が #54 に承認コメントを残してクローズすること）と #73（修了証（目録）機能の移植）の2件だけ。**

公開先: <https://youkiti.github.io/Spatial-epidemiology-training/>

| issue | 内容 | 状態 |
|---|---|---|
| #17 | Rmd レンダリング配管（Rmd → md + 図 → `docs/handson/`）、`renv.lock`、成果物の鮮度CIチェック | クローズ |
| #18 | ハンズオン1〜2「地図 → Global Moran's I → LISA → Gi\*」 | クローズ |
| #19 | ハンズオン3「CAR / BYM」 | クローズ（`CARBayes` で確定。renv も解決済み） |
| #20 | ハンズオン4「MAUP の実演 — 都道府県 vs 二次医療圏」 | クローズ |
| #33, #37〜#40 | レビュー由来の追加対応（リンクのコントラスト、ハンズオン③の整合、Gi\* 図の色差、隣接生成の後片付け） | クローズ |

**新しい issue に着手する前に必ず GitHub の issue 本文を読むこと**（受け入れ条件と cloud 可否がそこに書いてある）。

**R を使う作業（Rmd の変更・再レンダリング・renv）はクラウドセッションでは完結しない。** サイト側（Markdown・クイズ・CI・データ検算）はクラウドで進められる。

### 納品前の整備（2026-08-21、ブランチ `claude/pre-delivery-checklist-129zeq`）

公開前チェックで挙がった6点に対応した。**この節の内容は上の各節にも反映済みなので、詳細はそちらを読むこと。**

1. **ハンズオン④を資料ページに改題**した。`docs/handson/04-case-study.md` は「4本目のハンズオン」ではなく、②③が使う実データの制約をまとめた**資料**。ナビゲーションも「資料」グループに分けた（[カリキュラム設計](documents/カリキュラム設計.md) §4.4 が経緯の正本）
2. **ライセンスを確定**した。教材は CC BY 4.0、コードは MIT。`LICENSE` / `LICENSE-CODE` / `README.md` / `docs/about.md` が対応する
3. **利用者向け文書の古い記述を更新**した（`CARBayes` か `INLA` か未決定 → `CARBayes` 採用で確定、SaTScan の扱い、`renv.lock` と図の版の関係）
4. **データ整備用の依存を `requirements-data.txt` に固定**した（`pandas` / `requests` / `openpyxl` / `pdfplumber`）。`requirements.txt` はサイト用のまま
5. **`renv.lock` と図の生成環境の食い違いを文書化**した（版を揃えるのではなく、何を保証するものかを明示する方針。`analysis/README.md` と `docs/handson/00-setup.md`）
6. **CI の必須ゲートを5つに増やした**（下記「コマンド」節と `.github/workflows/ci.yml`）。**その後 issue #52 で7つになっている** — 現在の数と並びは下記「コマンド」節が正

```
documents/       設計の正本3文書。実装より先にここを読む
docs/            MkDocs のサイトソース。ここに置いたものは公開される
  concepts/      概念パート6章（issue #10〜#15 で執筆済み。各章に自己チェック3問＋章末クイズ10問。章4のみ12問）
  handson/       Rハンズオン。00〜03 は analysis/handson/*.Rmd からの生成物
                 （#17〜#20）。04-case-study.md だけは Rmd 由来ではない手書きの
                 「資料」ページ（ハンズオン本編ではない）
    figures/     Rmd から生成した図。コミット対象
    rmd/         配布用 .Rmd コピー。ページ末尾からダウンロードできる。生成物
  assets/js/     クイズエンジン（storage.js → quiz.js → progress.js）
  assets/data/   クイズJSON（全6章分。`quiz-chN-selfcheck.json` と `quiz-chN.json`）
  memo.md        ユーザーとの対話ログ。exclude_docs でサイトからは除外している
scripts/         quiz_lint.py（作問の機械チェック）、simulate_spatial_data.py と
                 verify_simulation.py（合成データの生成と検証。issue #6）、
                 fetch_meibo.py / parse_meibo.py（専門医名簿PDFの取得と抽出。issue #7・#8）、
                 build_geo.R（境界データと隣接関係の生成。issue #4）、
                 build_population.py（人口データの取得。issue #5）、
                 render_handson.R と check_handson_fresh.py（Rmd のレンダリングと
                 生成物の鮮度チェック。issue #17）、
                 build_facility_reference.py / link_facilities.py /
                 verify_facility_linkage.py / lib_facility_name.py /
                 propose_crosswalk.py（施設の名寄せと二次医療圏割付。issue #9）
data/simulated/  上記生成器の出力CSV（合成データなのでコミットしている）
data/geo/        二次医療圏・都道府県の境界データと queen contiguity。詳細は data/geo/README.md
data/processed/  専門医数CSV（都道府県別・施設別・二次医療圏別）と人口CSV
                 （詳細は「Phase1のデータ整備状況」と data/processed/README.md）
data/curated/    施設名寄せの人手判断（facility_crosswalk.csv）。詳細は data/curated/README.md
analysis/        Rハンズオンの .Rmd ソースと renv.lock。詳細は analysis/README.md
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
  総人口（`population_2020`）に加え、**5歳階級・65歳以上の列を持つ**（`pop_0_4` 〜
  `pop_85plus` / `pop_65plus` ほか24列。issue #28 で e-Stat から直接取得。男女別は
  `population_*_age_sex.csv` が別に持つ）。医師偏在の文脈で需要指標による標準化を
  するときはこれを使う。出典と取得経路は
  [documents/DATA_SOURCES.md](documents/DATA_SOURCES.md) の「年齢階級別人口」節

### コマンド

```bash
pip install -r requirements.txt
mkdocs build --strict                       # CI と同じ検査。警告ゼロ・exit 0 で通ること
mkdocs serve                                # クイズは fetch を使うので file:// 直開きでは動かない
python -m compileall -q scripts             # scripts/ 配下の Python の構文検査
python scripts/quiz_lint.py                 # クイズJSONの testwiseness cue 検査
python scripts/verify_facility_linkage.py   # 施設の名寄せ・二次医療圏割付（issue #9）の受け入れ条件検査
python scripts/verify_simulation.py --sweep # 合成データの受け入れ条件と Moran's I の単調性（issue #6）
python scripts/check_links.py               # 内部リンク・画像パスの検査（先に mkdocs build が要る）
Rscript scripts/render_handson.R            # Rmd → docs/handson/ の md + 図（ローカル専用。CI には R を入れない）
python scripts/check_handson_fresh.py       # 生成物が最新か（R を実行せずハッシュ照合。CI が回す）

pip install -r requirements-data.txt        # データを取り直す・作り直すときだけ（pandas ほか）
```

**CI の必須ゲートは7つ**（`compileall` → `quiz_lint.py` → `verify_facility_linkage.py` → `verify_simulation.py --sweep` → `check_handson_fresh.py` → `mkdocs build --strict` → `check_links.py`）。いずれも標準ライブラリだけで動くので、CI は `requirements.txt`（mkdocs 一式）しか install しない。**外部リンクの生存確認は必須ゲートに入れていない** — リンク先の一時的な不調で PR がブロックされるため、`external-links.yml` が週次で lychee を回す。同様に、`requirements.txt` / `requirements-data.txt` の既知脆弱性の検査（pip-audit）と `requirements-data.txt` のクリーンインストール試験も `weekly-deps.yml` が週次で回し、PR はブロックしない。

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
| [documents/カリキュラム設計.md](documents/カリキュラム設計.md) | 6章の学習目標とクイズ問数、**章↔issue 対応表**、ハンズオン本編3本＋資料ページの役割分担（§4） |
| [documents/作問ガイドライン.md](documents/作問ガイドライン.md) | 作問原則と lint 閾値。`scripts/quiz_lint.py` の正本 |

[docs/memo.md](docs/memo.md) はこの3文書の元になった対話ログ。一次資料として残してあるが、**食い違ったら documents/ が優先**。

### サイト実装で守ること（既知の罠）

- **`theme.features` に `navigation.instant` を入れない。** 全JSがフルページロード前提の初期化のため、SPA的ページ遷移では描画されなくなる
- **`extra_javascript` の読み込み順は依存順**（`storage.js` → `quiz.js` → `progress.js`）。変えない
- **クイズはページとJSをデータ属性で疎結合にする契約。** `data-quiz-gate` **無し**=自己チェック（合否は出すが保存しない）、**有り**=章末クイズ（合格を localStorage に保存）。`data-quiz-src` のパスは directory URL 基準の相対
- **クイズJSONスキーマは ai-kotohajime と同一に保つ**: `{title, passRatio, questions:[{q, choices[4], answer, explanation}]}`。**`answer` は 0-origin**
- **`extra.css` にハードコード色を足すときは、ダーク（slate）配色の上書きも必ず併せて書く。** 特に文字色は暗背景でコントラストが落ちる
- **Material のスキーム別 CSS 変数を上書きするときは特異度を先に測る。** ライトの `--md-typeset-a-color` は `:root,[data-md-color-scheme=default]` が特異度 (0,1,0) で定義するが、**ダークは `[data-md-color-scheme=slate][data-md-color-primary=teal]` で (0,2,0)**。つまり上の「slate 側も併記する」に従って `[data-md-color-scheme="slate"] { ... }` とだけ書くと Material に負けて**無言で効かない**（ビルドも通るし警告も出ない）。primary 属性まで書いて特異度を合わせること。issue #33 で実測（`site/assets/stylesheets/palette.*.min.css` を grep すれば実際の定義が読める）
- **`primary` / `accent` を変えると `extra.css` のリンク色上書きが静かに外れる。** issue #33 の上書きはセレクタに `[data-md-color-primary="teal"]` を含むため、`mkdocs.yml` の `theme.palette.primary` を teal 以外にすると発動しなくなり、ライトのリンクが WCAG AA 未達（3.77:1）に戻る。パレットを触るときは `extra.css` 末尾のリンク色セクションも必ず見直す
- **コントラストの実測は「ページの先頭1リンク」で済ませない。** 白地でないところに乗ったリンク（クイズの採点結果ボックス内の `.spepi-quiz-incorrect-list a` など、`extra.css` が独自色を当てている経路）は `--md-typeset-a-color` の上書きが効かないため、地色ごと変わる。Playwright では `query_selector_all` で全リンクを走査し、**ページ×スキームごとの最小値**を見ること。クイズのボックスは解答→採点まで進めないと DOM に現れない。またホバー色は Material が約 0.25 秒かけて遷移するので、`hover()` 直後に読むと遷移途中の色を掴む（400ms 待つ）
- 404 は `docs/404.md` では機能しない。テーマの静的テンプレート `404.html` が常に優先され、GitHub Pages はルートの `404.html` しか配信しない。`overrides/404.html` のリンクは**ルート相対**（`/Spatial-epidemiology-training/...`）で書く
- 作問の lint 閾値を変えるときは、`documents/作問ガイドライン.md` §3 と `scripts/quiz_lint.py` を**同時に**改訂する
- **ページ間リンクはソース相対の `.md` で書く**（`ch2-spatial-weights.md`、`../handson/03-maup.md`）。ディレクトリURL形式（`../ch2-spatial-weights/`）はブラウザ上は動くが MkDocs がリンクとして解決できず、`INFO ... unrecognized relative link` が出るだけで **`--strict` でも落ちない**。リンク切れを検出できない状態になる
- **`pymdownx.arithmatex` は有効化していない**（`mkdocs.yml` のコメント参照）。`$W$` のような LaTeX 記法はドル記号ごとそのまま表示される。数式は書かず、`W` やコードブロックで表現する
- **inline SVG で `currentColor` の塗りの上に `currentColor` の文字を置くとき、`fill-opacity` は 0.45 まで**。それ以上だと地の色と文字色が同一になり、ライト/ダーク両方で**文字が消える**。濃淡は 0.05〜0.45 の範囲で付ける（`extra.css` を触らずにテーマ追従させるための制約とセット）
- **クイズJSONの文字列に Markdown 記法を書かない。** `quiz.js` は JSON 由来の文字列を `textContent` で DOM に入れる（JSON由来の文字列をHTMLとして解釈させないための意図的な設計。`quiz.js` 冒頭の実装方針に明記されている）ため、`Gi\*` のエスケープやバックティックが**そのまま文字として表示される**。本文（Markdown）では `Gi\*` が正しく、クイズJSONでは `Gi*` が正しい
- **`<figure>` 内の inline SVG には `width` 属性を必ず書く。** Material の `.md-typeset figure` は `width: fit-content` であり、SVG に `width` が無いと `width:auto` が「親幅の100%」に解決され、親が fit-content なので循環して 0×0 になり描画されない。figcaption があるとそのテキストが figure に幅を与えるため偶然描画できてしまい、気づきにくい。`mkdocs build --strict` でも `quiz_lint.py` でも検出できない
- **インライン SVG の中に HTML コメント（`<!-- ... -->`）を書かない。** Python-Markdown がコメントを生 HTML ブロックの終端とみなし、以降を別ブロックとして `<p>` で包むことがある。`<p>` は HTML パーサが foreign content（SVG）から抜け出す breakout タグなので、そこで `<svg>` が閉じられ、**残りの `<rect>` / `<text>` が SVG の外の未知の HTML 要素になる** — マス目が描画されず、セルの中身だけが `1 1 1 1 ● 1 1 1 1` のような平文の行として並ぶ。`mkdocs build --strict` も `quiz_lint.py` も通り、コメントより前にある要素は正しく描画されるため気づきにくい。2026-08-26 に `docs/concepts/ch2-spatial-weights.md` の queen/rook 図が公開状態でこうなっていた（ビルド出力を `--></p>` や `<p><g` で grep すれば検出できる）。座標や意図はタグの属性から読めるので、コメントは付けずに書く。**`<figure>` の中や `<g>` の中にネストしたコメントは分割されない実例もあるが（`ch5-explanatory.md` / `ch6-pitfalls.md`）、条件は自明ではないので書かないのが安全**
- **生の HTML の `<img src>` / `<a href>` は MkDocs が相対パスを書き換えない。** ディレクトリURL形式（`docs/handson/00-setup.md` → `site/handson/00-setup/index.html`）のため、ページ内の相対パスはビルド時に1階層分ずらす必要があるが、この書き換えが効くのは **Markdown 記法（`![alt](path)` / `[text](path)`）だけ**。生の HTML はそのまま残り、実サイトで画像やリンクが壊れる。しかも `mkdocs build --strict` は警告を出さない（issue #17 で実測。`markdown` → `<img alt="alt" src="../figures/x.png">`、生HTML → `<img src="figures/x.png">` のまま）。**Rmd の図チャンクに `fig.cap` を付けないこと** — knitr が `<div class="figure">` ごと生 HTML で出す。`fig.alt` は付けてよい（`scripts/render_handson.R` が後処理で Markdown 記法に戻している）。詳細は `analysis/README.md`
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
| 1 記述 | どこで多い？ | 累積罹患割合・有病割合・標準化割合、SIR/SMR、choropleth map |
| 2 パターン | 集まっている？ | Global Moran's I、Local Moran's I (LISA)、Getis-Ord Gi*、spatial scan statistic |
| 3 説明 | なぜそこに多い？ | 通常回帰、spatial regression、CAR / BYM |

### 教材が最重要視している論点

- **「地図を描く」と「空間統計」は別物。** 色を塗っただけでは「本当に集まっている」とは言えない、という区別が教材全体の出発点
- **Gi\* / LISA / SaTScan の違い**（memo.md 635行目以降がまるごとこの説明＝ユーザーが明示した躓きポイント）。Gi\* は「塊探し」、LISA は「自分と周囲の関係の分類」（High-High / Low-Low / High-Low / Low-High）、SaTScan は「異常に患者が多い地理的範囲の探索」。特に **「値が高い」と「hot spot である」は別**（周囲が低ければ単独の高値は High-Low の空間的アウトライヤーであって hot spot ではない）という区別を、必ず具体的な数値グリッドで示すこと
- **空間重み行列（「隣」の定義）を先に決める。** 普通の統計に無い発想として強調する。queen contiguity / 距離閾値
- **5つの落とし穴** — 人口の多さの無視、小地域の少数例による推定値の不安定、MAUP、生態学的誤謬、「隣」の定義の事後決定

### 教材として使う実例論文

- Blazel MM, et al. *JAMA Netw Open.* 2024;7(8):e2429764 — 高血圧。地図 → Moran's I → Bayesian CAR Poisson model。**Moran → 空間回帰**まで通す例
- Pradhan P, Iyer HS, Rebbeck TR. *JAMA Netw Open.* 2025;8(10):e2537905 — 米国3,142 counties のがん検診。queen contiguity → Global Moran's I → LISA。**Global → Local の対比**を見せる例
- 総説4本: Elliott & Wartenberg 2004 (EHP)、Auchincloss et al. 2012 (Annu Rev Public Health)、Beale et al. 2008 (EHP)、Hu et al. 2025 (Front Public Health)

**これらの統計値・書誌情報は一次資料で裏取り済み（2026-08-18、issue #16）。確認した数値と原文の該当箇所は [documents/引用検証.md](documents/引用検証.md) が正本。** 教材本文に数値を足すときは、まずこの文書に原著の該当箇所を引いてから足すこと（memo.md 由来の数値をそのまま載せない、という原則は変わらない）。

裏取りで出た、書くときに間違えやすい2点:

- **Pradhan 2025 の LISA は bivariate LISA** で、high/high・high/low は「自分と周囲」ではなく**時点間の推移**（一貫して高い／高から低へ変化した）を意味する。章4が教える univariate LISA の4分類とは語義が違う。この論文の LISA 結果を引くときは必ず違いに触れる
- **Blazel 2024 は隣接（空間重み行列）の定義を明示していない。** 「queen contiguity を使った」と書かない（それは Pradhan 側）

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

- **導入済み**: `sf` 1.0.21, `spdep` 1.4.1, `spatialreg` 1.4.2, `ggplot2` 4.0.1, `dplyr` 1.1.4, `rmarkdown` 2.30, `knitr` 1.50, `CARBayes` 6.1.1（issue #19 で導入。この版一覧はシステムライブラリの版で、`analysis/renv.lock` が固定する版とは独立に管理されている。`ggplot2` は lock 側だと 4.0.0 — 理由は下記「`renv::restore()`」節と `analysis/README.md` 参照）
- **未導入**: `tmap`, `sfdep`, `leaflet`, `SpatialEpi`, `INLA`, `jpndistrict`, `NipponMap`

Global/Local Moran's I と Gi\* は `spdep` だけで完結する（`moran.test` / `localmoran` / `localG`）ので、段階1〜2 は追加インストールなしで書ける。CAR/BYM に進む時点で `CARBayes` か `INLA` の選択が必要。**`INLA` は CRAN ではなく専用リポジトリからの導入**で、読者に要求するハードルが `CARBayes` より高い。

**`spdep::mat2listw()` はこの環境でプロセス終了時にクラッシュする。** R の出力自体は最後まで正常に出るが、終了時にスタックオーバーフローで異常終了する（Windows 終了コード 0xC00000FD、Git Bash 経由では 127）。行列サイズによらず再現し、`rm()` / `gc()` / `quit(status=0)` でも回避できないため、`Rscript foo.R && echo ok` が決して成功しない。**どうするか**: `nb` オブジェクトを隣接エッジ一覧から直接組み立てて `nb2listw()` に渡す（密な隣接行列を経由しない）。`scripts/verify_simulation.R` がその実装例。

**`spdep::poly2nb()` も同じくプロセス終了時に落ちる**（Git Bash 経由で終了コード 255）。`mat2listw()` と同種だが、今回は `poly2nb()` 自体がトリガー。実ポリゴンから隣接を導くのに `poly2nb()` は避けられないため、**呼び出しだけを子プロセスの `Rscript` に切り出し、結果をCSVに書かせてから親が読み戻す**のが回避策（`scripts/build_geo.R` が実装例）。**終了コードで成否を判定しないこと** — 代わりに (a) 出力先が毎回新しい tempdir か、(b) 子が完了マーカーを stdout に出したか、で判定する。ファイルの存在チェックだけだと、書き込み途中で切れたCSVを黙って読んでしまう。

この制約は Phase3（issue #17〜#20）の Rmd に直接効く。**ハンズオンの Rmd から `poly2nb()` / `mat2listw()` を直接呼ばない**。`data/geo/adjacency_iryoken2.csv`（issue #4 で生成済みの queen contiguity エッジ一覧）を読んで `nb` を組み立て、`nb2listw()` に渡す構成にする（`scripts/verify_simulation.R` が組み立ての実装例）。読者の環境では `poly2nb()` が通る可能性はあるが、その場合でも**隣接の定義を再現可能な成果物として固定しておく方が教材として正しい**（章2の「『隣』を先に決める」と対応する）。

**生成済みの `docs/handson/*.md` を R 無しで直したくなったときは、3ファイル同時＋マニフェスト再計算でしかやってはいけない。** `docs/handson/00〜03.md` は `analysis/handson/*.Rmd` からの生成物で、`analysis/render_manifest.json` の SHA-256 に縛られている（`check_handson_fresh.py` が CI で照合する）。R が無いクラウドセッションで**地の文だけ**を直す必要が出た場合に限り、次の3点を守れば整合を保てる（2026-08-21 の納品前整備で実際にこの手順を使い、②③のケーススタディ参照文と⓪の renv 説明を直した）:

1. `analysis/handson/X.Rmd` と `docs/handson/rmd/X.Rmd`（配布用コピー。ソースとバイト単位で同一）と `docs/handson/X.md` の**3つとも同じ文字列に**置換する
2. 対象は**コードチャンクの外の地の文だけ**。`--wrap=none` でレンダリングしているため、地の文は Rmd → md で1行のまま素通りする（チャンクの出力・図・表は R を動かさない限り触ってはいけない）
3. `analysis/render_manifest.json` の該当エントリの `source_rmd` / `distributed_rmd` / `output_md` の `sha256` を、`check_handson_fresh.py` の `sha256_text_file()`（CRLF を LF に正規化してからハッシュ）で再計算して書き換える

**これは鮮度チェックの保証を人手で肩代わりする操作なので、次にローカルで `Rscript scripts/render_handson.R` を回したときに差分が出ないことを確認すること。** コードや図に関わる変更は絶対にこの方法でやらない。

**`ragg` / `systemfonts` を読み込んだ R プロセスも終了時に落ちる**（Git Bash 経由で終了コード127。issue #17 で実測）。`mat2listw()` / `poly2nb()` と同種で、出力自体は最後まで正常に完了する。図の device に `ragg_png` を使うのは Windows で図中の日本語が豆腐にならないためで、避けられない。**`scripts/render_handson.R` の成否を終了コードで判定しないこと** — 正常終了時に stdout の最後へ `RENDER_HANDSON_OK` を出すので、その有無で判定する。

**`renv::restore()` は P3M の日付スナップショットに向けることで完走するようになった（issue #19、2026-08-20）。** CRAN が配布する Windows バイナリは各パッケージの**最新版だけ**なので、`analysis/renv.lock` が固定する版が最新でなくなるとソースビルドになる。実測（2026-08-19）: `vctrs` は lock が 0.6.5、CRAN の R 4.5 向けバイナリは 0.7.3。Rtools45 は入っているのでツールチェーンの問題ではなく、C のコンパイルは最後まで通ったうえで `** byte-compile and prepare package for lazy loading` の段で `ERROR: lazy loading failed for package 'vctrs'` になった（独立に再現済み）。これは vctrs 固有ではなく、issue #17 時点の lock（51本）のうち30本が CRAN 最新とズレていた（#18 で `spdep` を足して69本になった時点でも事情は同じだった）。**`renv.lock` に `>=` は書けない**（lock は常に厳密固定）ため、直すべきはバージョン制約ではなく**リポジトリ**だった。

**`analysis/renv.lock` は `Hash`/`Requirements` 付きの正規の `renv::snapshot()` 産物（issue #17 レビューで再生成・確認済み。手順と詳細は `analysis/README.md` 参照）。** 再 snapshot するときは `renv::load()` では不十分（`.Rprofile` が読まれず lockfile version が既定の2に戻る）なので、必ず `analysis/` を作業ディレクトリにして R を起動すること。詳細は `analysis/README.md` 参照。

**直し方: `Repositories` を Posit Public Package Manager (P3M) の日付スナップショット `https://packagemanager.posit.co/cran/2025-11-01` に向けた。** `sf` 1.0-21 / `spdep` 1.4-1（`poly2nb()` / `mat2listw()` のプロセス終了時クラッシュを確認した版）を据え置ける最も新しい日付で、`sf` 1.0-21 と `ggplot2` 4.0.1 が両立する日付は存在しないため、代償として `ggplot2` は lock 上 4.0.1 → 4.0.0 に下がった。lock は 69本 → **126本**（`CARBayes` の推移的依存で57本増、削除は0本、版が動いたのは既存69本のうち7本のみ）。**空のプロジェクトライブラリから `renv::restore()` が完走し、ソースビルド0件・エラー0件を実測で確認した。** 実測の全数値・restore 検証の手順・踏んだ罠（日付スナップショットに向けると `analysis/renv/activate.R` が固定する renv 自身の版もそのスナップショットに存在する版へ揃える必要がある、など）は `analysis/README.md` の該当節が正本。

**レンダリングは renv に依存しない** — `scripts/render_handson.R` はリポジトリのルートから起動するため `analysis/.Rprofile`（renv の自動 activate）を読まず、システムライブラリで動く。**ただし `renv.lock` はもう「どのバージョンで生成したか」の記録ではない** — 11-01 への切り替えで `ggplot2` が lock 上 4.0.0 になった一方、コミット済みの図はシステムライブラリの `ggplot2` 4.0.1 で生成されている。`renv.lock` は「`renv::restore()` で再現できる依存関係の組」を記録するものとして読むこと。

**実ポリゴンを扱うときは `sf::sf_use_s2(FALSE)` が要る。** s2 有効のままだと `st_make_valid()` が一部ジオメトリを修復しきれず（実測: 新宮 3007）、`poly2nb()` がさらに強く落ちる。A38 由来の339区域では7件が `st_is_valid()` で不正、s2 を切れば `st_make_valid()` で全件修復できる。

**`pip install -r requirements.txt` は Windows ローカルで失敗する。** `requirements.txt` に日本語コメントがあるため pip が locale（cp932）で読もうとして `UnicodeDecodeError`。**`PYTHONUTF8=1` を付ければ通る。** CI（ubuntu-latest）は UTF-8 locale なので起きない。**しかも pip が終了コード0を返すことがあり**、あとで `No module named mkdocs` で気づくことになる。

`scripts/verify_simulation.R` は R 4.5.2 / spdep 1.4.1 で実行・検証済み（2026-08-18）で、Python 版と出力が一致することを確認済み。

**R側の依存マニフェストは `analysis/renv.lock` が正本（issue #17 で導入、issue #19 で P3M 2025-11-01 に固定し直した）。** バージョンの経緯・restore が通ることの実測は上記「`renv::restore()`」節と `analysis/README.md` を参照。

## 決定済み（もう議論しない）

過去に未決定だった項目のうち、以下は決着している。詳細と理由は [documents/要件定義書.md](documents/要件定義書.md)。

- **公開ページの実装手段** = Material for MkDocs + GitHub Pages（Quarto Website ではない）
- **地域単位** = 二次医療圏をメイン、都道府県も併走（MAUP の実演を兼ねる）
- **記述言語** = 日本語のみ（i18n は入れない）
- **境界データの入手元** = 国土数値情報の医療圏データ（A38）。隣接リポジトリ <https://github.com/youkiti/visualize-regional-medical-care-for-2040> の `doc/DATA_SOURCES.md` に取得手順と罠が文書化されている
- **架空データと実データの役割分担** = 架空の10市町村データは概念導入用、専門医名簿はケーススタディ専用
- **`renv::restore()` の修正は issue #19 の中で実施済み**（2026-08-19 決定 → 2026-08-20 実施）。決定時の方針どおり、#18 は先に版を動かさず現行の検証済み環境のまま進め（先に動かすと `sf` 1.0.21 / `spdep` 1.4.1 で確認した `poly2nb()` / `mat2listw()` の終了時クラッシュを再確認する手間が #18 の前に挟まるため）、#19 で `CARBayes` を入れて R 環境を触るタイミングでリポジトリを P3M の日付スナップショット（`2025-11-01`）へ切り替えてまとめて直した。`sf` 1.0.21 / `spdep` 1.4.1 は据え置いたまま、空のプロジェクトライブラリから `renv::restore()` が完走することを実測で確認済み。詳細は「環境」節と `analysis/README.md`
- **CAR/BYM の実装** = `CARBayes`（issue #19 本文で確定）。`INLA` は CRAN ではなく専用リポジトリからの導入で読者に要求するハードルが高いため、章5で違いに触れるに留める（`docs/concepts/ch5-explanatory.md` に反映済み）
- **ライセンス** = 教材（`docs/` の文章・図・クイズ、`documents/`、`README.md`、`analysis/` の `.Rmd` の地の文とそこから生成される図）は **CC BY 4.0**、コード（`scripts/`、`analysis/` の `.Rmd`（コードチャンク）、`docs/assets/js/`、`.github/`）は **MIT**。`.Rmd` はファイル単体では区分できず、コードチャンクと地の文でライセンスが分かれる（issue #46 で確定）。外部データ由来のファイルは各出典の利用条件に従う。正本は `LICENSE` / `LICENSE-CODE`、読者向けの記載は `docs/about.md`。**CC BY 4.0 の legal code 全文はリポジトリに収録していない**（URL で参照する形にした。クラウドセッションからは creativecommons.org が egress proxy で遮断されており全文を取得できなかったため。全文を同梱したくなったらローカルで貼ること）
- **統合ケーススタディ（旧ハンズオン④）は作らない** = `docs/handson/04-case-study.md` は実データの制約を開示する**資料ページ**であり、ハンズオン本編ではない。3段階の型は①〜③が段階ごとに扱う（[カリキュラム設計](documents/カリキュラム設計.md) §4.4 が経緯の正本）
- **簡略化済み（表示専用）GeoJSON を隣接判定に使ってよいか** = 使ってよい。`snap=0` と `snap=0.0001`（座標丸め幅と同程度）で queen contiguity の隣接ペアが完全一致した（1,558件、集合差0件）ため、0.0001度丸めは隣接判定に影響していない。本採用は `snap=0`。測定手順と全診断は `scripts/build_geo.R` と `data/geo/adjacency_diagnostics.md`
- **施設単位CSV（`specialists_facility.csv` / `facility_geo_audit.csv`）は公開リポジトリに保持し続ける**（issue #47 で A に確定、2026-08-21 の issue コメントが承認記録）。理由: 名簿自体が公開情報であり、これらのファイルによる集計は公開情報の再掲という整理。氏名列は含まないが、氏名が無いことは再識別リスクが無いことと同義ではない（施設名と公開名簿PDFを突合すれば個人単位の推定が可能な場合がある）ため、**再識別に関する注意は定性的にとどめ、`n_specialists=1` の行数・割合のような定量値は文書に追加しない**方針とした。正本は `data/processed/README.md`「施設単位データの公開範囲と利用上の注意」節と `LICENSE` §3
- **修了証（目録）機能を輸入する**（2026-08-22 決定）。ai-kotohajime の `certificate.js` を移植し、章末クイズの合格を条件に、学習者がブラウザ上で氏名（ニックネーム可）を入力して Canvas に描画・PNG で発行できるようにする。氏名は Canvas 描画にのみ使い、**localStorage にも保存せず、サーバにも送信しない**。自己申告であり公式な修了証明ではない旨を発行ページ・免責ページに明記する。**実装は issue #73。発行単位（全6章合格で1枚か、章ごとに出すか）は issue #73 で確認する未確定事項として残る。**
- **SaTScan の実演ハンズオンは将来も追加しない**（2026-08-22 決定）。理由は従来どおり: SaTScan は R のパッケージではなく Windows 専用の独立したソフトウェアで、導入と操作の説明だけで独立した教材相当の分量になる。章4本文（`docs/concepts/ch4-lisa-gi-satscan.md`）は既に概念紹介にとどめる理由を書いてあり変更不要
- **監修体制** = 独立監修は置かず、著者（youkiti）による最終レビューで承認する（2026-08-21 決定）。承認記録は issue #54。第三者監修が未実施であることは納品時の開示事項として `RELEASE.md` に記載する

## 未決定事項（実装前にユーザーに確認する）

1. **修了証（目録）の発行単位** — 全6章の合格で1枚出すか、章ごとに出すか。修了証を輸入すること自体は上の「決定済み」に移した（2026-08-22）。issue #73 の実装前に確認する

かつてここに挙げていた「修了証を出すか」（→ issue #73）「SaTScan の実演ハンズオン」「監修体制」（→ issue #54）は 2026-08-21〜22 にすべて決着し、上の「決定済み」節へ移した。

## 執筆上の注意

- 読者は疫学の素養がある前提。割合・標準化・交絡の基礎説明は省いてよいが、**空間統計に固有の概念**（空間自己相関、空間重み行列、MAUP、空間的アウトライヤー）は丁寧に扱う
- 公開ページに載せる数値（Moran's I の値、prevalence ratio、論文の書誌情報など）は**原著で確認する**。memo.md 由来の数値をそのまま載せない。`verify-slide-citations` スキルが引用検証に使える
- クイズを書いたら `python scripts/quiz_lint.py` を通す。**閾値を緩めて通すのではなく、設問と選択肢の方を直す**。日本語の四択では L3（選択肢の最長/最短比 1.5 以内）と L2（正答肢長/平均 0.8〜1.3）が特に効く
