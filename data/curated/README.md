# data/curated/

`scripts/link_facilities.py`(施設名寄せ、issue #9)が機械的には解決できない
名簿の行について、**人が判断して対応づけた表**を置く。`data/processed/` の
自動生成物とは異なり、このディレクトリの内容は人手の判断そのものが正本になる。

## `facility_crosswalk.csv`

列: `pref_name, facility_name, basis, care_setting, iryoken2_code, resolved_facility_name, note`

名簿の施設名が参照点テーブル(`data/interim/facility_reference.csv`)に
機械的には当たらない行(大学名だけの記載・施設名の改称・診療を行わない
勤務先など)について、`(pref_name, facility_name)` ごとに人が対応づけた表。

### `care_setting`(診療の場かどうか)

**issue #9改訂で新設した列。値は `care`(診療の場)/ `non_care`(診療を行わない
勤務先)/ 空(`basis=unassignable` の行のみ)。**

もともとこの表は、診療を行わない勤務先(製薬企業・銀行・官庁・医学部を
持たない大学など)を `basis=excluded_non_care` として**分子から除外**する
設計だった。しかしユーザー(著者)から「国立健康危機管理研究機構
国立感染症研究所は診療機関ではない」という指摘を受け、除外ではなく
**フラグとして持たせ、`care`(診療の場のみ)と `all`(勤務地ベース)の
2通りの分布を出す**設計に変更した。除外してしまうと「専門医ではあるが
診療はしていない」という情報自体が失われる上、症例定義を変えると地図が
変わるという空間疫学の題材として好適だったため。これに伴い
`basis=excluded_non_care` は `basis=non_care_workplace` に改名し(「除外」
ではなく「フラグ」であることを名前にも反映)、これまで所在を与えず除外
していた行にも、可能な範囲で所在の参照点を新たに与えた
(`data/processed/README.md` の実測値を参照)。

`care_setting=non_care` の行(`basis=non_care_workplace` /
`research_institute` の一部)でも、`resolved_facility_name` /
`iryoken2_code` を持ってよい(所在さえ分かれば `all` 系列の地図には載る)。
`basis=unassignable` の行だけは座標を持たせようがないため
`care_setting` を空にする。

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
| `university_hospital` | 名簿が大学名だけを記載している行を、その大学の医学部附属病院に対応づけた(`care_setting=care`) |
| `research_institute` | 研究機関を所在の参照点に対応づけた。実際に診療を行う附属病院なら `care_setting=care`、研究所自体や職員診療所のように診療の場でなければ `care_setting=non_care`(例: 国立感染症研究所→職員診療所) |
| `renamed` | 施設の改称・表記差(名簿の表記と参照点テーブルの表記が異なる)。`care_setting` は施設の実態に応じて `care`/`non_care` |
| `non_care_workplace` | 診療を行わない勤務先(製薬企業・銀行・官庁・医学部を持たない大学など、`care_setting=non_care`)。所在の参照点が分かれば `resolved_facility_name`/`iryoken2_code` を持ち `all` 系列の地図に載る。所在が分からなければ `match_status=unassignable`(`reason_code=no_location_for_non_care`)になる |
| `unassignable` | 名簿に施設の記載が無い、または勤務先が国外。座標を持たせようがない(`care_setting` も空) |

`basis=unassignable` の行は `iryoken2_code` を必ず空にする(埋まっていたら
書き間違いの疑いが強いため、`link_facilities.py` がエラーで落とす)。
`non_care_workplace`/`university_hospital`/`research_institute`/`renamed`
は、`resolved_facility_name` と `iryoken2_code` の少なくとも一方が必要
(両方空だと `link_facilities.py` がエラーで落とす。ただし
`non_care_workplace` だけは所在の参照点が実在しない場合があるため、この
制約の対象外 = 両方空を許容する)。

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
反映されているか(`basis` と `assignment_basis` が一致し、`care_setting` も
一致し、`unassignable` の行が `matched` になっていないか)を検査する。
