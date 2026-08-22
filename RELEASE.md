# RELEASE.md — 空間疫学入門 リリース手順書

このリポジトリでリリース（タグ付き配布物）を作るときの手順書。上から順に実行すれば納品物（タグ・配布アーカイブ・チェックサム・GitHub Release）ができる。

**対象読者はリリース作業者。** 日常の PR 作成・レビューには不要。CI の7ゲートについては `CLAUDE.md`「コマンド」節が正本で、本書はそれをリリース手順の中に位置づけたものにすぎない。

## 0. 前提

- Python・R・Git・GitHub CLI（`gh`）がローカルにインストールされていること
- `gh auth status` でこのリポジトリに push 権限のあるアカウントにログイン済みであること
- リポジトリ本体（隔離ワークツリーではなく）で作業すること。リリース対象は `main` ブランチの特定コミットに固定するため、作業ツリーが枝分かれしたままではいけない

## 1. CI の必須ゲート7つをローカルで再現する

PR の必須ゲートは7つ（`.github/workflows/ci.yml` が正本、順序もこのとおり）。リリース前にもう一度ローカルで通す。

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 pip install -r requirements.txt

python -m compileall -q scripts
python scripts/quiz_lint.py
python scripts/verify_facility_linkage.py
python scripts/verify_simulation.py --sweep
python scripts/check_handson_fresh.py
mkdocs build --strict
python scripts/check_links.py
```

**依存関係の注意**: `check_links.py` は `site/` を検査するため、必ず `mkdocs build --strict` の**後**に実行すること。単独では動かない。

Windows でこれらを回すときの罠は「4. 環境上の罠」を参照。すべて `exit code 0` で通ること、`mkdocs build --strict` の出力に本物の `WARNING` が無いこと（見た目上の警告と紛らわしい既知の出力については後述）を確認する。

## 2. CI では検出できない検査（本書の本体）

CI の7ゲートは「標準ライブラリだけで動く」方針のため R を含まず、ブラウザも動かさない。**リリース前にはここでしか検出できない回帰がある。** 順に実行する。

### 2.1 R ハンズオンの全件レンダリング

CI に R を入れない方針の代償として、「全件レンダリングが通らない」という回帰（監査 F-01 / issue #44 で実際に踏んだ型 — `MASS::select` によるマスクが原因だった）は CI では検出できない。リリース前に必ずローカルで全件レンダリングを回す。

```bash
Rscript scripts/render_handson.R > release-render.log 2>&1
```

**成否を終了コードで判定しないこと。** `ragg` / `systemfonts` を読み込んだ R プロセスはプロセス終了時にクラッシュする既知の問題があり（`mat2listw()` / `poly2nb()` と同種）、R の出力自体は正常に完了していても終了コードが 0 以外（Git Bash 経由で 127 等）になることがある。**判定は `release-render.log` の末尾に `RENDER_HANDSON_OK` が出ているかどうかで行う。**

```bash
# Git Bash
tail -n 5 release-render.log
grep -q RENDER_HANDSON_OK release-render.log && echo "RENDER OK" || echo "RENDER NOT OK"
```

```powershell
# PowerShell
Get-Content release-render.log -Tail 5
Select-String -Path release-render.log -Pattern 'RENDER_HANDSON_OK' -Quiet
```

`RENDER_HANDSON_OK` が確認できたら、鮮度チェックと差分確認に進む。

```bash
python scripts/check_handson_fresh.py
git status --short
git diff -- analysis/render_manifest.json
```

- **`analysis/render_manifest.json` の `generated_at` フィールド1行だけの差分なら正常。** 図と md は同一環境ならバイト決定的に生成されるため、`generated_at`（タイムスタンプ）以外は変わらない。この場合は作業ツリーを元に戻す（`git checkout -- analysis/render_manifest.json` など、リリース対象のコミットを汚さないため）。
- **`docs/handson/` の md・図・配布用 `.Rmd` コピー、あるいは `render_manifest.json` の `sha256` フィールドに差分が出た場合は異常のシグナル。** コミット済みの生成物と実際のレンダリング結果がズレているということなので、原因（Rmd の変更漏れ、環境差異など）を調査してから先に進む。差分を握り潰してリリースを進めない。

### 2.2 `pip-audit`

`requirements.txt` と `requirements-data.txt` の両方に対して実行する。

```bash
pip install pip-audit
pip-audit -r requirements.txt
pip-audit -r requirements-data.txt
```

**合格条件は「ゼロ件」ではなく「受容済みの例外を除いてゼロ件」。** 受容している例外は次の1つだけ:

- パッケージ `cryptography`（`requirements-data.txt` が固定する版 `46.0.3`）、**Windows ARM64 限定**（環境マーカー `platform_system == "Windows" and platform_machine == "ARM64"`）。advisory は `PYSEC-2026-35` / `PYSEC-2026-36` / `PYSEC-2026-2141` / `PYSEC-2026-3552` / `PYSEC-2026-3553` / `PYSEC-2026-3554` / `GHSA-537c-gmf6-5ccf` の**ユニーク7件**。`pip-audit` の出力は `PYSEC-2026-35` と `PYSEC-2026-36` がそれぞれ2行ずつ重複して出るため見かけ9行になるが、advisory ID としては7種類なので数えて混乱しないこと。

**これ以外の脆弱性が1件でも出たら失敗として扱う。** ここで受容の範囲を広げない — 新しいパッケージや別バージョンの脆弱性が出た場合は、そのままリリースするか修正してからにするかを都度判断する。

実行環境によって結果が変わることに注意する:

- **Windows ARM64** で `pip-audit -r requirements-data.txt` を実行すると、上記の環境マーカーが真になり、`cryptography` の既知脆弱性7件が報告される。**これは想定どおりの結果であり、失敗ではない。**
- **Linux や x86_64 Windows** ではこの環境マーカーが偽になるため `cryptography` は監査対象にすら入らず、`requirements-data.txt` も0件になる。CI の `weekly-deps.yml` の `pip-audit` ジョブは `ubuntu-latest` で走るため、通常はこちら（0件）を見ることになる。

受容の理由の要約: `cryptography` は 46.0.4 以降 win_arm64 wheel を配布しなくなったため 46.0.3 に据え置いている。このパイプラインで `cryptography` が使われるのは pdfminer.six が暗号化PDFをローカルで復号する経路のみで、名簿PDFは暗号化されておらず、`requests` の TLS 通信にも使われない。**受容の正本は `requirements-data.txt` の該当コメント（28〜47行目）。** これとは別に、requests / pdfminer.six 経由で見つかっていた既知脆弱性3件は issue #45 → PR #60 で版を上げて**修正済み**（受容ではない）。上記の `cryptography` 7件だけが「修正」ではなく「Windows ARM64 限定で受容」という決定であることを混同しないこと。

### 2.3 ブラウザ E2E（Playwright、ローカル）

CI はブラウザを動かさないため、UI の実際の振る舞いはローカルの手動 E2E でしか確認できない。issue #53 に列挙された次の項目を確認する。

**配信方法の注意（最初に必ず読む）**:

- クイズは `fetch` を使うため **`file://` の直開きでは動かない**。`mkdocs serve` などで HTTP 配信してから検証する。
- `overrides/404.html` のリンクは**ルート相対**（`/Spatial-epidemiology-training/...`）で書かれている。404 ページのリンクを検証するときは、`mkdocs serve` の既定の `/`（ルート）配下ではなく、**本番と同じベースパス（`/Spatial-epidemiology-training/`）配下で配信する**必要がある。`mkdocs serve` はこのベースパスを再現できないため使えない。**先に `mkdocs build --strict` で `site/` を作ってから**、次の最小サーバーで配信する。

```python
# serve_basepath.py — site/ を本番と同じベースパス配下で配信する(404ページも本番相当)
import functools
import http.server
import pathlib
import sys

PREFIX = "/Spatial-epidemiology-training"
DIRECTORY = "site"


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith(PREFIX):
            path = path[len(PREFIX):] or "/"
        return super().translate_path(path)

    def send_error(self, code, message=None, explain=None):
        # 存在しないURLで SimpleHTTPRequestHandler 標準の素っ気ない404本文ではなく、
        # site/404.html(overrides/404.html 由来)をステータス404のまま返す。
        # これをやらないと「404ページに遷移してそこからルート相対リンクをたどる」という
        # 本番の流れを検証できない。
        if code == 404:
            try:
                body = (pathlib.Path(DIRECTORY) / "404.html").read_bytes()
            except OSError:
                return super().send_error(code, message, explain)
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = functools.partial(Handler, directory=DIRECTORY)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving {DIRECTORY}/ at http://127.0.0.1:{port}{PREFIX}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
```

```bash
mkdocs build --strict
python serve_basepath.py 8765
# ブラウザ／Playwright から http://127.0.0.1:8765/Spatial-epidemiology-training/ を開く
```

`translate_path()` で先頭の `PREFIX` を剥がしてから `SimpleHTTPRequestHandler` の標準解決に渡し、`send_error()` で404のときだけ `site/404.html` の中身をステータス404のまま返す。**このスクリプトを Git Bash から実行するときの罠は「4. 環境上の罠」を参照**（`PREFIX` のような先頭が `/` の文字列を Git Bash 経由でコマンド引数として渡すと壊れる。このスクリプトは `PREFIX` をファイル内に直書きしているため影響を受けないが、同種の作業で `curl` 等に `/Spatial-epidemiology-training/...` を引数として渡すときは注意する）。

確認項目:

1. **各ページのナビゲーション応答が HTTP 200 であることを確認する。** ベースパスの配信設定を間違えると、**全ページが 404 本文を返しているのに DOM の検査（画像・SVG・コントラストなど）はどれも「異常なし」を返して素通りし、E2E が緑に見える**（沈黙は成功ではない）。上記サーバーが正しく機能しているかを、E2E の本検査に入る前に必ず単独で確認すること（例: 主要ページ数本に対して `page.goto()` 後の `response.status` を見る、または `curl -o /dev/null -w '%{http_code}\n'` で疎通確認する）。
2. **クイズ**: 解答 → 採点 → 未回答警告 → 合格保存（`localStorage`）→ 進捗表示、の一連の流れ。**自己チェック**（`data-quiz-gate` 無し）と**章末クイズ**（`data-quiz-gate` 有り）の両方で確認する。
3. **リンク色コントラスト**: ライト/ダーク両スキームで、全ページのリンク色コントラストの最小値を測る。
   - `query_selector_all` 等で**ページ内の全リンクを走査**する（先頭1リンクだけの確認では足りない）。
   - クイズの採点結果ボックス内のリンク（`.spepi-quiz-incorrect-list a` など）は独自の色経路を持つため、**解答して採点まで進めないと DOM に現れない**。
   - ホバー色は Material が約0.25秒かけて遷移するため、`hover()` 直後に読むと遷移途中の値を掴む。**400ms 待ってから読む。**
4. **レスポンシブ**: ビューポート幅 320px / 768px / 1440px で、本文の横スクロールが発生しないこと・表示崩れが無いことを確認する。
5. **404 ページ**: 存在しない URL（例: `http://127.0.0.1:8765/Spatial-epidemiology-training/no-such-page/`）を直接踏んで、ステータス404で `overrides/404.html` 由来のページが表示されることを確認したうえで、そのページ内のリンクをクリックして正しく遷移することを確認する（上記サーバーの `send_error()` 対応により、この一連の流れを本番と同じ形で再現できる）。

Playwright はこのリポジトリの `requirements.txt` / `requirements-data.txt` には含めていない（サイト運用やデータ整備に必須の依存ではなく、リリース前手動 QA 専用のツールのため）。作業者のローカルに一時的に `pip install playwright && playwright install chromium`（または同等の Node 版）を用意して使う。

### 2.4 週次ワークフローを手動実行して緑を確認する

`external-links.yml`（外部リンク生存確認）と `weekly-deps.yml`（依存の脆弱性・クリーンインストール試験）は PR の必須ゲートではなく週次実行のため、リリース前に明示的に手動起動して結果を見る。

```bash
gh workflow run external-links.yml --ref main
gh workflow run weekly-deps.yml --ref main

# 実行状況の確認(数分待ってから)
gh run list --workflow=external-links.yml --limit 5
gh run list --workflow=weekly-deps.yml --limit 5

# 個別の実行ログを見る場合
gh run view <run-id> --log
```

- `external-links.yml` が赤い場合、リンク切れの原因を確認する（一時的な不調か、恒久的なリンク切れか）。
- `weekly-deps.yml` は3ジョブに分かれている。`pip-audit` ジョブは既知脆弱性があれば赤くなる設計（2.2 節と同じ確認を CI 側でも行っている）。`install-test-windows-arm` には `continue-on-error: true` が付いているためこのジョブが赤でもワークフロー全体は失敗しないが、**現在は3ジョブとも緑が期待値**（2026-08-22 実測: `windows-11-arm` ランナーは実在し、`cryptography-46.0.3-cp311-abi3-win_arm64.whl` の取得を含めてクリーンインストールに成功、`pip-audit` も `requirements.txt` / `requirements-data.txt` の両方で "No known vulnerabilities found"）。**このジョブが赤ならそれは退行なので、`continue-on-error` で握り潰さず必ず中身を確認すること。**

## 3. タグ付与 → アーカイブ → チェックサム → GitHub Release

**このセクションのコマンドはリリース作業者が実行する。**

**この節の手順は「検査した SHA」「タグを打つ SHA」「`origin/main` の SHA」の3つを最後まで一致させることを軸に組んである。** リリース準備のための変更（`CITATION.cff` / `CHANGELOG.md` の更新）を先に `main` へ反映してから対象 SHA を固定し、その固定 SHA に対して1・2節の全検査を1回だけ正式に行う — その後は検査結果を汚す変更を何も加えずにタグを打つ。順序を逆にする（先に検査して後から準備コミットを載せる）と、検査した内容とタグが指すコミットがズレる。

### 3.1 前提条件の確認

- P1（最優先）に分類された issue がすべて閉じている、または残存リスクを文書（`documents/納品前監査レポート.md` 等）で受容していることを確認する。
- **既知の限界（開示事項）**: 第三者による独立監修は未実施（著者による最終レビューのみ。issue #54）。監修体制自体は決着済み（[要件定義書](documents/要件定義書.md) §9-5）だが、独立監修が行われていないという事実はリリースの開示事項として扱う。
- 1・2 節の検査一式（CI 7ゲート + R 全件レンダリング + `pip-audit` + E2E + 週次ワークフロー）が、この時点の作業ブランチで通ることを一通り確認しておく。**ただしこれは準備確認であり、正式な合格記録ではない。** 正式な検査は 3.5 で、実際にタグを打つ SHA に対して行う。

### 3.2 バージョン番号の方針

[Semantic Versioning](https://semver.org/lang/ja/) に準拠した `vMAJOR.MINOR.PATCH` を使う。教材という性質上「API の破壊的変更」は厳密には無いが、目安は次のとおり:

- **MAJOR**: 教材の対象読者や章立ての大枠が変わるなど、既存の学習者への影響が大きい変更
- **MINOR**: 新しい章・ハンズオン・データセットの追加など、内容の追加
- **PATCH**: 誤字修正、リンク切れ修正、CI・依存関係の整備など、内容の追加を伴わない修正

**タグは現時点で1件も無い。初回リリースは `v0.1.0` とする**（`1.0.0` ではなく `0.1.0` から始めるのは、修了証（目録）の要否や SaTScan ハンズオンの追加可否など、教材の対象範囲に関わる事項が未決のまま残っている段階のため。[要件定義書](documents/要件定義書.md) §9 参照）。バージョン番号はこの後の準備コミット（3.3節）で必要になるため、ここで確定させておく。

### 3.3 リリース準備コミットを作り、`main` に反映する

`CITATION.cff` には現時点で `version` と `date-released` の2フィールドが**無い**（未リリースの段階で書くと、cffconvert や GitHub の "Cite this repository" がセンチネル値をそのまま引用文字列に出してしまうため、意図的に省略してある）。タグ付けの**前**に、次の変更を `main` へ反映する。

1. `CITATION.cff` に `version:` と `date-released:` の2行を**追加**する。例:

   ```yaml
   version: "0.1.0"
   date-released: "2026-XX-XX"
   ```

   `version` は先頭の `v` を付けない数字表記（CFF の慣例）。`date-released` は実際のリリース日（`YYYY-MM-DD`）。追加位置はファイル末尾の既存コメントの直後でよい。
2. `CHANGELOG.md` の `## [Unreleased]` 見出しを `## [0.1.0] - YYYY-MM-DD` に書き換え、新しい空の `## [Unreleased]` 見出しをその上に追加する（Keep a Changelog の運用）。
3. 作業ブランチを作って変更をコミットし（例: `git commit -m "chore: prepare v0.1.0 release"`）、**PR を作って `main` にマージする。** このリポジトリは `main` への直接 push ではなく PR 運用のため、ここも例外にしない。
4. マージ後、そのマージコミットに対して CI（7ゲート）が緑であることを `gh pr checks` 等で確認する。

### 3.4 リリース対象の SHA を固定する

```bash
git checkout main
git pull origin main
git rev-parse HEAD    # このコミットがリリース対象
```

**この SHA が 3.3 の準備コミット（`CITATION.cff` の `version`/`date-released` 追加、`CHANGELOG.md` の見出し書き換え）を含んでいることを確認する**（例: `git show --stat HEAD` や `git log -1` で直前のマージ内容を見る）。含まれていなければ `git pull` し忘れているか、PR がまだマージされていない。

### 3.5 固定した SHA で1・2節の全検査を実行する

3.4 で固定した SHA（作業ツリーの状態）に対して、1・2節の検査一式（CI 7ゲート + R 全件レンダリング + `pip-audit` + E2E + 週次ワークフロー）を通す。**これがこの節における唯一の「正式な」検査であり、これより後はタグを打つところまで作業ツリーに変更を加えない。**

### 3.6 注釈付きタグを打つ

タグを打つ直前に、次の3つの SHA が一致していることを確認する:

- 3.5 で検査した SHA（3.4 で `git rev-parse HEAD` で確認したもの）
- これから打つタグが指す SHA（現在の `HEAD`）
- `origin/main` の SHA（`git ls-remote origin main` で確認できる。ローカルの `main` と食い違っていたら、誰かが割り込みで `main` を更新した可能性があるため 3.4 からやり直す）

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

軽量タグ（`-a` 無し）ではなく**注釈付きタグ**を使う。誰がいつ何のメッセージでタグを打ったかが記録に残るため。

### 3.7 `git archive` で配布アーカイブを作る

```bash
# Git Bash / WSL — zip
git archive --format=zip \
  --prefix="Spatial-epidemiology-training-v0.1.0/" \
  -o "spatial-epidemiology-training-v0.1.0.zip" \
  v0.1.0

# Git Bash / WSL — tar.gz(Unix系での配布向け)
git archive --format=tar.gz \
  --prefix="Spatial-epidemiology-training-v0.1.0/" \
  -o "spatial-epidemiology-training-v0.1.0.tar.gz" \
  v0.1.0
```

`--prefix` を付けることで、展開したときにファイルがカレントディレクトリへ直接ばら撒かれず、`Spatial-epidemiology-training-v0.1.0/` という単一フォルダの下に収まる。

### 3.8 SHA-256 チェックサムを生成する

```bash
# Git Bash / WSL
sha256sum "spatial-epidemiology-training-v0.1.0.zip" > "spatial-epidemiology-training-v0.1.0.zip.sha256"
sha256sum "spatial-epidemiology-training-v0.1.0.tar.gz" > "spatial-epidemiology-training-v0.1.0.tar.gz.sha256"
cat "spatial-epidemiology-training-v0.1.0.zip.sha256"
```

```powershell
# PowerShell
Get-FileHash ".\spatial-epidemiology-training-v0.1.0.zip" -Algorithm SHA256 |
    Select-Object -ExpandProperty Hash |
    Out-File -Encoding ascii ".\spatial-epidemiology-training-v0.1.0.zip.sha256"

Get-FileHash ".\spatial-epidemiology-training-v0.1.0.tar.gz" -Algorithm SHA256 |
    Select-Object -ExpandProperty Hash |
    Out-File -Encoding ascii ".\spatial-epidemiology-training-v0.1.0.tar.gz.sha256"

Get-Content ".\spatial-epidemiology-training-v0.1.0.zip.sha256"
Get-Content ".\spatial-epidemiology-training-v0.1.0.tar.gz.sha256"
```

### 3.9 リリースノートを添えて GitHub Release を作る

`CHANGELOG.md` の該当バージョンの節（3.3 で書き換えた `## [0.1.0] - YYYY-MM-DD` 以下、次のバージョン見出しの手前まで）を、エディタで手元にコピーしてリリースノート用の一時ファイル（例: `release-notes-v0.1.0.md`）を作る。**自動抽出のワンライナーは使わない** — `sed` の範囲パターン（開始行〜次の `## [` 見出し）は、初回リリースのように対象バージョンの後にもうバージョン見出しが無い場合、終端が EOF まで伸びてしまい、そこにさらに末尾1行を削る処理を重ねると本文の最終行が欠ける。手でコピーする方が確実。

```bash
gh release create v0.1.0 \
  "spatial-epidemiology-training-v0.1.0.zip" \
  "spatial-epidemiology-training-v0.1.0.zip.sha256" \
  "spatial-epidemiology-training-v0.1.0.tar.gz" \
  "spatial-epidemiology-training-v0.1.0.tar.gz.sha256" \
  --title "v0.1.0" \
  --notes-file release-notes-v0.1.0.md
```

公開後、`gh release view v0.1.0 --web` で公開ページを開いて内容を目視確認する。

## 4. 環境上の罠

リリース作業でよく踏む、この環境（Windows ローカル）固有の罠。詳細は `CLAUDE.md`「コマンド」節・「環境」節が正本。

- **`pip install -r requirements.txt` は Windows ローカルで失敗しうる。** `requirements.txt` に日本語コメントがあるため、pip がロケール（cp932）でファイルを読もうとして `UnicodeDecodeError` になる。**`PYTHONUTF8=1` を付けると通る。** CI（ubuntu-latest）は UTF-8 ロケールなので起きない。**さらに pip が終了コード 0 を返すことがあり**、その場で気づかず、後になって `No module named mkdocs` で発覚することがある。`pip install` の直後に `python -c "import mkdocs"` などで実際に入ったか確認するのが安全。
- **`mkdocs build --strict` の出力に出る "Warning from the Material for MkDocs team"（MkDocs 2.0 の告知）はビルド警告ではない。** 警告ゼロの判定に数えない。同様に `git-revision-date-localized` プラグインが出す `has no git logs` も `--strict` を落とさない print 出力であり、ビルド警告ではない。
- **Windows では出力をパイプに繋ぐと `$?` が `tail` 側の終了コードになる。** 例えば `Rscript scripts/render_handson.R | tail -n 5` の直後に `echo $?` を見ても、それは `Rscript` ではなく `tail` の終了コードを見ている。**ログファイルにリダイレクトしてから、別コマンドで終了コード・内容を確認すること**（2.1 節のコマンド例はこの理由でリダイレクト形式にしている）。
- **Git Bash では、先頭が `/` の引数が Windows のパスへ勝手に変換される（MSYS のパス変換）。** 例えば `--prefix "/Spatial-epidemiology-training"` のような、先頭が `/` の文字列をコマンドやスクリプトの引数として渡すと、Git Bash が「Unix 風の絶対パス」とみなして `C:/Program Files/Git/Spatial-epidemiology-training` のような別物に化けて渡ってしまう。2.3 節の `serve_basepath.py` は `PREFIX` をスクリプト内に直書きしているためこの影響を受けないが、同種の値（ルート相対パスなど）を `curl` や他のコマンドラインツールの**引数として**渡すときは要注意。壊れたまま気づきにくく、**全ページが 404 になるのに原因が見えない**、という形で現れる。回避策は環境変数 `MSYS_NO_PATHCONV=1` を付けてそのコマンドを実行すること。
