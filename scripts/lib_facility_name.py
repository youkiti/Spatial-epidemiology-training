#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 出典: https://github.com/youkiti/visualize-regional-medical-care-for-2040
#       tools/build_facility_geo_linkage.py の normalize_facility_name() ほかを逐語移植。
#       同一著者のリポジトリ。移植日 2026-08-18。
#       ⚠ 法人格語除去のガード（除去結果が種別語だけになる場合は除去しない）は
#         誤結合の根本原因への対処であり、簡略化してはいけない。
"""施設名の正規化（issue #9「専門医名簿の施設名に座標を与える」の第1チャンクで使う
共有モジュール）。

`normalize_facility_name()` は決定的（乱数を使わない）に施設名を正規化し、
NFKC正規化 → 小文字化 → 空白除去 → 記号除去 → 法人格語の除去、の順で処理する。
法人格語除去には「除去結果が施設種別語だけになる場合は除去しない」というガードが
付いており、これは実データで見つかった誤結合の根本原因への対処なので簡略化しては
いけない（詳細は `normalize_facility_name()` のdocstring参照）。

このチャンクでは正規化した名前を出力するだけで、名寄せ（突合）そのものは次の
チャンクで行う。
"""

import re
import unicodedata

# 法人格語(brief記載の語をそのまま定数化)。除去は長い語から先に行う
# (`_LEGAL_ENTITY_TERMS_BY_LENGTH_DESC`)ことで、「医療法人社団」を先に除去
# せずに「医療法人」だけを除去してしまい「社団」が残る、という部分除去を防ぐ。
#
# 「社会医療法人社団」「社会医療法人財団」「特定医療法人社団」は、実データに
# 実在することを確認して追加した複合語(「社会医療法人」+「医療法人社団」/
# 「医療法人財団」のように2つの短い語が重なり合う位置に出現するため、複合語を
# 明示的に登録しないと重なりのどちらを先に除去するかで結果が変わってしまう。
# 例: 「社会医療法人財団董仙会」は「社会医療法人」(6文字)と「医療法人財団」
# (6文字)が「医療法人」の4文字を共有して重なっており、複合語を登録しない
# 状態では除去順序によって「財団董仙会」または「社会董仙会」という不完全な
# 結果になっていた(実測で発見した不具合。順序は`set`のハッシュ順に依存して
# 実行のたびに変わるため、非決定的な不具合でもあった)。「特定医療法人財団」は
# 実データには見当たらないが、同型の法人格として将来に備えて登録しておく。
LEGAL_ENTITY_TERMS = (
    "社会医療法人社団",
    "社会医療法人財団",
    "特定医療法人社団",
    "特定医療法人財団",
    "医療法人社団",
    "医療法人財団",
    "医療法人",
    "社会医療法人",
    "特定医療法人",
    "独立行政法人",
    "国立研究開発法人",
    "地方独立行政法人",
    "国立大学法人",
    "公立大学法人",
    "学校法人",
    "公益社団法人",
    "一般社団法人",
    "公益財団法人",
    "一般財団法人",
    "社会福祉法人",
    "恩賜財団",
    "厚生農業協同組合連合会",
    "農業協同組合連合会",
    "厚生連",
    "国民健康保険団体連合会",
    "共済組合連合会",
)
# 第2キー(文字列そのもの)まで指定するのは、`set(...)`の反復順が
# PYTHONHASHSEEDに依存し実行のたびに変わるため。同じ長さの語が複数ある本リスト
# では、長さだけをキーにすると同じ長さの語同士の順序が実行ごとに変わってしまい
# (実測で見つけた非決定性の不具合)、除去対象が重なり合う語同士(上記コメント
# 参照)で結果が変わりうる。文字列そのものを第2キーに加えることで常に同じ順序
# になる。
_LEGAL_ENTITY_TERMS_BY_LENGTH_DESC = tuple(
    sorted(set(LEGAL_ENTITY_TERMS), key=lambda term: (-len(term), term))
)

_WHITESPACE_RE = re.compile(r"[\s　]+")
# 中黒・括弧類・句読点・ハイフン類等の記号(NFKC後の全角/半角どちらの形も
# 拾えるよう両方含めておく)。長音記号「ー」もここで除去されるため、下記
# `FACILITY_TYPE_WORDS`の語をそのまま(除去前の表記で)`in`/`replace`に使うと
# 「センター」→「センタ」のように正規化済みテキストと噛み合わなくなる
# (実測で見つけた不具合)。そのため`_FACILITY_TYPE_WORDS_BY_LENGTH_DESC`は
# 各語をこの正規表現で正規化してから使う。
_SYMBOL_RE = re.compile(
    "[" + re.escape("・･｡｢｣「」『』【】()（）[]｛｝{}<>〈〉《》〔〕、。，．,.!！?？:：;；~～-ー－―_/／\\｜|") + "]+"
)

# 施設種別語(病院・診療所の種別、および診療科名)。法人格語を
# 除去した結果がこれらの語だけ(=種別語を取り除くと何も残らない)になる名称は、
# 医療機関名としての識別力を失っており(例: 「厚生連クリニック」から「厚生連」
# を除去すると「クリニック」になり、これは全国のクリニック共通の一般名詞に
# すぎない)、接尾一致ティアで無関係の別施設と誤結合しうる
# (`normalize_facility_name`のガード・`_find_suffix_relation_candidates`の
# ガード、いずれも参照)。網羅的なリストではない(診療科名は多数存在する)ため
# あくまで防御的なガード用。
FACILITY_TYPE_WORDS = (
    "病院", "医院", "診療所", "クリニック", "医療センター", "センター",
    "歯科医院", "歯科診療所", "歯科クリニック", "歯科", "薬局",
    "内科", "外科", "眼科", "耳鼻科", "耳鼻咽喉科", "皮膚科", "皮膚泌尿器科",
    "産婦人科", "産科", "婦人科", "小児科", "精神科", "神経科", "神経内科",
    "心療内科", "整形外科", "形成外科", "美容外科", "脳神経外科",
    "呼吸器科", "呼吸器内科", "循環器科", "循環器内科", "消化器科", "消化器内科",
    "泌尿器科", "放射線科", "麻酔科", "リハビリテーション科", "リハビリ科",
    "アレルギー科", "腫瘍内科", "乳腺外科", "肛門科", "胃腸科",
)


def _normalize_type_word(word: str) -> str:
    """`FACILITY_TYPE_WORDS`の1語を、`normalize_facility_name()`が実際の
    テキストへ適用するのと同じNFKC正規化・小文字化・記号除去を適用してから
    返す(「センター」の長音記号のように、記号除去で消える文字を語の定義に
    含んでいても、正規化済みテキストとの比較で正しく機能するようにするため)。
    """
    text = unicodedata.normalize("NFKC", word)
    text = text.lower()
    text = _SYMBOL_RE.sub("", text)
    return text


_FACILITY_TYPE_WORDS_BY_LENGTH_DESC = tuple(
    sorted({_normalize_type_word(w) for w in FACILITY_TYPE_WORDS}, key=lambda term: (-len(term), term))
)


def _residual_after_removing_type_words(text: str) -> str:
    """`text`から`FACILITY_TYPE_WORDS`の語(正規化済み)を(長い語から先に)
    全て取り除いた残余を返す。残余が空文字なら、`text`は施設種別語(と、
    既に除去済みの法人格語)だけで構成されていたことを意味する。
    """
    for word in _FACILITY_TYPE_WORDS_BY_LENGTH_DESC:
        if word in text:
            text = text.replace(word, "")
    return text


def normalize_facility_name(name: str) -> str:
    """医療機関名を突合用に正規化する(決定的。乱数は使わない)。

    NFKC正規化 → 小文字化 → 空白除去 → 記号除去 → 法人格語の除去、の順。
    法人格語は空白/記号を除去した**後**に除去する(語の途中に全角空白が
    挟まっている表記でも確実に除去できるようにするため)。

    ⚠ 法人格語除去のガード(レビューで発見された誤結合の根本原因への対処):
    法人格語を除去した結果が施設種別語(`FACILITY_TYPE_WORDS`)だけになる場合
    (=種別語を取り除くと残余が**空**になる場合)は、法人格語を除去せず、
    除去前の名称を採用する。例:
      - 「厚生連クリニック」→ 法人格語「厚生連」を除去すると「クリニック」に
        なり、これは種別語だけ(除去すると残余が空)なので、除去せず
        「厚生連クリニック」のまま返す(全国の「クリニック」と誤って接尾一致
        しないようにするため)。
      - 「医療法人社団森クリニック」→ 法人格語「医療法人社団」を除去すると
        「森クリニック」になり、これは種別語「クリニック」を取り除いても
        「森」が残る(空にならない)ので、そのまま「森クリニック」を返す
        (正しい正規化であり、巻き戻すとP04側の「森クリニック」と一致しなく
        なってしまう。残余の判定を「空かどうか」ではなく「◯文字未満」等に
        してはいけない理由はここにある)。
    """
    text = unicodedata.normalize("NFKC", name)
    text = text.lower()
    text = _WHITESPACE_RE.sub("", text)
    text = _SYMBOL_RE.sub("", text)
    before_legal_removal = text
    after_legal_removal = text
    for term in _LEGAL_ENTITY_TERMS_BY_LENGTH_DESC:
        if term in after_legal_removal:
            after_legal_removal = after_legal_removal.replace(term, "")
    if _residual_after_removing_type_words(after_legal_removal) == "":
        return before_legal_removal
    return after_legal_removal


def is_type_word_only(normalized_name: str) -> bool:
    """既に正規化済みの名称が、施設種別語だけ(=種別語を取り除くと残余が空)で
    構成されているかを判定する。接尾一致ティアの保険のガード
    (`_find_suffix_relation_candidates`)で使う。空文字列に対しても
    (取り除く対象が無い=残余は空文字列のままなので)`True`を返す。
    """
    return _residual_after_removing_type_words(normalized_name) == ""
