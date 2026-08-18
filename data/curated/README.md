# data/curated/

`scripts/link_facilities.py`(施設名寄せ、issue #9)が機械的には解決できない
名簿の行について、**人が判断して対応づけた表**を置く。`data/processed/` の
自動生成物とは異なり、このディレクトリの内容は人手の判断そのものが正本になる。

## `facility_crosswalk.csv`

列: `pref_name, facility_name, basis, iryoken2_code, resolved_facility_name, note`

名簿の施設名が参照点テーブル(`data/interim/facility_reference.csv`)に
機械的には当たらない行(大学名だけの記載・施設名の改称・診療を行わない
勤務先など)について、`(pref_name, facility_name)` ごとに人が対応づけた表。

### `resolved_facility_name` が正本

`resolved_facility_name`(参照点テーブル上の正式名称)が埋まっている行は、
そちらを正本として `link_facilities.py` が県内の参照点テーブルから
`iryoken2_code` を導出する。`iryoken2_code` 列も埋まっていれば、導出値と
一致するかを検査し、食い違えばエラーで落とす(手打ちのコードは目視監査
だけでは「施設名は合っているのにコードが隣の医療圏を指している」ような
転記ミスに気づけないため、名前とコードを二重化して機械にも突き合わせさせる
設計にしている)。

`resolved_facility_name` が空の行(参照点テーブルに存在しない施設について、
医療圏だけを人手で決めたい場合の逃げ道)だけ、`iryoken2_code` の手入力を
正本として扱う。

### `basis` の意味

| 値 | 意味 |
|---|---|
| `university_hospital` | 名簿が大学名だけを記載している行を、その大学の医学部附属病院に対応づけた |
| `research_institute` | 研究機関を、実際に診療を行う附属施設に対応づけた |
| `renamed` | 施設の改称・表記差(名簿の表記と参照点テーブルの表記が異なる) |
| `excluded_non_care` | 診療を行わない勤務先(製薬企業・銀行・官庁・医学部を持たない大学など)。分子(専門医数)に入れない |
| `unassignable` | 名簿に施設の記載が無い、または勤務先が国外。座標を持たせようがない |

`excluded_non_care` / `unassignable` の行は `iryoken2_code` を必ず空にする
(埋まっていたら書き間違いの疑いが強いため、`link_facilities.py` がエラーで
落とす)。

### これは推論であり、観測ではない

「長崎大学」という名簿の記載が長崎大学病院を指すという対応づけは、名簿
そのものからは直接読めない。**1行ずつ根拠を残し**、`data/processed/facility_geo_audit.csv`
の `assignment_basis` 列にもこの `basis` をそのまま出しているのは、
自動突合(`assignment_basis=automatic`)と人手の推論を後から区別できるように
するため。

### 編集するとき

`facility_crosswalk.csv` を編集したら、必ず次の順で通すこと:

```bash
python scripts/link_facilities.py
python scripts/verify_facility_linkage.py
```

`verify_facility_linkage.py` の条件8が、この表の全行が監査表に意図どおり
反映されているか(`basis` と `assignment_basis` が一致し、
`excluded_non_care`/`unassignable` の行が `matched` になっていないか)を
検査する。
