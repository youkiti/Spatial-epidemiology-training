#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quiz_lint.py — クイズJSON(docs/assets/data/quiz-*.json)の testwiseness cue 検査ツール。

正本は documents/作問ガイドライン.md の「§3 機械チェックの閾値」であり、
本スクリプトはその実装。閾値を変更する場合は、ガイドライン文書と本スクリプトの両方を
同時に改訂すること。

使い方:
    python scripts/quiz_lint.py                               # docs/assets/data/quiz-*.json 全件
    python scripts/quiz_lint.py docs/assets/data/quiz-ch1.json  # 指定ファイルのみ(複数可)

終了コード: 違反なし=0、違反あり=1、対象ファイルなし=0
標準ライブラリのみを使用(pip依存なし)。Python 3.9+。
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

# Windows のコンソールでも日本語出力が文字化けしないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# --- 断定語・婉曲表現の語彙リスト(ガイドライン §3-W と一字一句整合) -----------

JA_ABSOLUTE_WORDS = [
    "必ず", "一切", "すべて", "全て", "絶対", "常に", "決して", "完全に", "例外なく", "のみ",
]
JA_HEDGE_WORDS = [
    "ことがある", "場合がある", "可能性", "かもしれない", "おそれ", "傾向",
]

# 英語は単語境界・大文字小文字無視の正規表現(語尾の揺れは ? で許容)
EN_ABSOLUTE_PATTERNS = [
    r"always", r"never", r"only", r"all", r"every", r"none",
    r"completely", r"entirely", r"guaranteed?",
]
EN_HEDGE_PATTERNS = [
    r"may", r"might", r"can", r"could", r"sometimes", r"often",
    r"possible", r"possibly", r"tends?", r"likely",
]

EN_ABSOLUTE_RE = re.compile(
    r"\b(?:" + "|".join(EN_ABSOLUTE_PATTERNS) + r")\b", re.IGNORECASE
)
EN_HEDGE_RE = re.compile(
    r"\b(?:" + "|".join(EN_HEDGE_PATTERNS) + r")\b", re.IGNORECASE
)


def is_english(path: Path) -> bool:
    """ファイル名が .en.json で終われば英語版と判定する。"""
    return path.name.endswith(".en.json")


def count_ja_terms(text: str, terms: list[str]) -> int:
    """単純部分文字列マッチで延べ出現回数を数える(日本語)。"""
    return sum(text.count(term) for term in terms)


def count_en_terms(text: str, pattern: re.Pattern) -> int:
    """正規表現で延べ出現回数を数える(英語)。"""
    return len(pattern.findall(text))


# --- スキーマ検査 ---------------------------------------------------------


def check_schema(data: Any) -> list[str]:
    """トップレベル・各問題の必須フィールドを検査する。違反があれば即座にリストを返す。"""
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["[スキーマ] JSONのトップレベルがオブジェクトではありません"]

    if not isinstance(data.get("title"), str):
        errors.append("[スキーマ] title が文字列ではありません、または存在しません")
    if not isinstance(data.get("passRatio"), (int, float)) or isinstance(data.get("passRatio"), bool):
        errors.append("[スキーマ] passRatio が数値ではありません、または存在しません")
    questions = data.get("questions")
    if not isinstance(questions, list):
        errors.append("[スキーマ] questions がリストではありません、または存在しません")
        return errors

    for i, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            errors.append(f"[スキーマ] 問{i}: 問題がオブジェクトではありません")
            continue
        if not isinstance(q.get("q"), str):
            errors.append(f"[スキーマ] 問{i}: q が文字列ではありません、または存在しません")
        choices = q.get("choices")
        if not isinstance(choices, list) or len(choices) != 4 or not all(isinstance(c, str) for c in choices):
            errors.append(f"[スキーマ] 問{i}: choices が要素4の文字列リストではありません")
        answer = q.get("answer")
        if not isinstance(answer, int) or isinstance(answer, bool) or not (0 <= answer <= 3):
            errors.append(f"[スキーマ] 問{i}: answer が0〜3の整数ではありません")
        if not isinstance(q.get("explanation"), str):
            errors.append(f"[スキーマ] 問{i}: explanation が文字列ではありません、または存在しません")

    return errors


def has_valid_question_shape(q: Any) -> bool:
    """後続の検査(L1/L2/W/P)を安全に行えるだけの最低限の形になっているか。"""
    if not isinstance(q, dict):
        return False
    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) != 4 or not all(isinstance(c, str) for c in choices):
        return False
    answer = q.get("answer")
    if not isinstance(answer, int) or isinstance(answer, bool) or not (0 <= answer <= 3):
        return False
    return True


# --- L1. 正答肢最長の割合(ファイル単位) ------------------------------------


def check_l1(questions: list[dict]) -> list[str]:
    n = len(questions)
    if n == 0:
        return []
    longest_count = 0
    detail_indices: list[int] = []
    for idx, q in enumerate(questions, start=1):
        choices = q["choices"]
        answer = q["answer"]
        lengths = [len(c) for c in choices]
        answer_len = lengths[answer]
        others = [l for i, l in enumerate(lengths) if i != answer]
        if others and answer_len > max(others):
            longest_count += 1
            detail_indices.append(idx)

    threshold = max(1, math.floor(0.4 * n))
    if longest_count > threshold:
        detail = "、".join(f"問{i}" for i in detail_indices)
        return [
            f"[L1] 正答肢が最長の問題が {longest_count}/{n} 問あり、閾値(max(1, floor(0.4×{n}))={threshold})を超えています(該当: {detail})"
        ]
    return []


# --- L2. 正答肢長の比(問題単位) --------------------------------------------


def check_l2(questions: list[dict]) -> list[str]:
    messages: list[str] = []
    for idx, q in enumerate(questions, start=1):
        choices = q["choices"]
        answer = q["answer"]
        lengths = [len(c) for c in choices]
        mean_len = sum(lengths) / len(lengths)
        if mean_len == 0:
            continue
        ratio = lengths[answer] / mean_len
        if ratio < 0.8 or ratio > 1.3:
            messages.append(f"問{idx}: 正答肢が長すぎる(正答/平均比 {ratio:.2f})" if ratio > 1.3 else f"問{idx}: 正答肢が短すぎる(正答/平均比 {ratio:.2f})")
    if messages:
        return [f"[L2] {m}" for m in messages]
    return []


# --- L3. 選択肢長の最長/最短比(問題単位) ------------------------------------


def check_l3(questions: list[dict]) -> list[str]:
    messages: list[str] = []
    for idx, q in enumerate(questions, start=1):
        lengths = [len(c) for c in q["choices"]]
        shortest = min(lengths)
        if shortest == 0:
            continue
        ratio = max(lengths) / shortest
        if ratio > 1.5:
            messages.append(
                f"[L3] 問{idx}: 選択肢の最長/最短比 {ratio:.2f} が1.5を超えています(最長{max(lengths)}文字/最短{shortest}文字)"
            )
    return messages


# --- W. 断定語・婉曲表現の偏り(ファイル単位) --------------------------------


def check_w(questions: list[dict], english: bool) -> list[str]:
    violations: list[str] = []

    absolute_correct = 0
    absolute_wrong = 0
    hedge_correct = 0
    hedge_wrong = 0
    absolute_wrong_locations: list[str] = []
    hedge_correct_locations: list[str] = []

    for idx, q in enumerate(questions, start=1):
        choices = q["choices"]
        answer = q["answer"]
        for ci, choice in enumerate(choices):
            if english:
                abs_count = count_en_terms(choice, EN_ABSOLUTE_RE)
                hedge_count = count_en_terms(choice, EN_HEDGE_RE)
            else:
                abs_count = count_ja_terms(choice, JA_ABSOLUTE_WORDS)
                hedge_count = count_ja_terms(choice, JA_HEDGE_WORDS)

            is_correct = ci == answer
            label = f"問{idx}-選択肢{ci + 1}"

            if abs_count > 0:
                if is_correct:
                    absolute_correct += abs_count
                else:
                    absolute_wrong += abs_count
                    absolute_wrong_locations.append(label)

            if hedge_count > 0:
                if is_correct:
                    hedge_correct += hedge_count
                    hedge_correct_locations.append(label)
                else:
                    hedge_wrong += hedge_count

    if absolute_wrong >= 3 and absolute_correct == 0:
        locs = "、".join(absolute_wrong_locations)
        violations.append(
            f"[W] 断定語が誤答肢に{absolute_wrong}回出現・正答肢には0回(偏り)。出現箇所: {locs}"
        )

    if hedge_correct >= 3 and hedge_wrong == 0:
        locs = "、".join(hedge_correct_locations)
        violations.append(
            f"[W] 婉曲表現が正答肢に{hedge_correct}回出現・誤答肢には0回(偏り)。出現箇所: {locs}"
        )

    return violations


# --- P. 正答位置の分散(ファイル単位) ---------------------------------------


def check_p(questions: list[dict]) -> list[str]:
    n = len(questions)
    if n == 0:
        return []
    counts = [0, 0, 0, 0]
    for q in questions:
        counts[q["answer"]] += 1

    most_common = max(counts)

    if n >= 8:
        missing = [i for i, c in enumerate(counts) if c == 0]
        threshold = math.ceil(0.4 * n)
        problems = []
        if missing:
            problems.append(f"未出現のインデックス: {missing}")
        if most_common > threshold:
            problems.append(f"最頻インデックスの出現数 {most_common} が閾値 ceil(0.4×{n})={threshold} を超過")
        if problems:
            return [f"[P] 正答位置の分散が不十分です(内訳 {counts})。" + " / ".join(problems)]
    else:
        threshold = math.ceil(0.6 * n)
        if most_common > threshold:
            return [
                f"[P] 正答位置の分散が不十分です(内訳 {counts})。最頻インデックスの出現数 {most_common} が閾値 ceil(0.6×{n})={threshold} を超過"
            ]
    return []


# --- ファイル単位の検査エントリポイント --------------------------------------


def lint_file(path: Path) -> list[str]:
    """指定ファイルを検査し、違反メッセージのリストを返す(違反なしなら空リスト)。"""
    path = Path(path)
    messages: list[str] = []

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"[スキーマ] ファイルを読み込めません: {e}"]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"[スキーマ] JSONとして解析できません: {e}"]

    schema_errors = check_schema(data)
    if schema_errors:
        # スキーマ違反がある場合、後続の検査は安全に行えないことがあるため
        # 形の壊れていない問題だけに絞って可能な範囲で追加検査する。
        messages.extend(schema_errors)

    questions_raw = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions_raw, list):
        return messages

    # 形が壊れている問題は L1/L2/W/P の対象から除外する(スキーマ検査で既に報告済み)。
    valid_questions = [q for q in questions_raw if has_valid_question_shape(q)]

    english = is_english(path)

    messages.extend(check_l1(valid_questions))
    messages.extend(check_l2(valid_questions))
    messages.extend(check_l3(valid_questions))
    messages.extend(check_w(valid_questions, english))
    messages.extend(check_p(valid_questions))

    return messages


# --- CLI -------------------------------------------------------------------


def default_targets() -> list[Path]:
    """引数なし実行時のデフォルト対象: docs/assets/data/quiz-*.json 全件。

    スクリプトの位置からの相対解決により、どのディレクトリから実行しても動く。
    """
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "docs" / "assets" / "data"
    return sorted(data_dir.glob("quiz-*.json"))


def main(argv: list[str]) -> int:
    if argv:
        targets = [Path(a) for a in argv]
    else:
        targets = default_targets()

    if not targets:
        print("対象ファイルが見つかりませんでした。")
        return 0

    any_violation = False
    for path in targets:
        violations = lint_file(path)
        if violations:
            any_violation = True
            print(f"■ {path}")
            for v in violations:
                print(f"  {v}")
            print()
        else:
            print(f"○ {path}: 違反なし")

    if any_violation:
        print("結果: 違反あり")
        return 1
    print("結果: 違反なし")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
