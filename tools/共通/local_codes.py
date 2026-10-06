"""地方競馬DATA のコード値と、地方の事実表の決めごと（予想の設計書「地方競馬の近走と適性から3着以内を予想」09 の A・06 の図2）。

一次資料は nvdata-store の ``docs/reference/codes.md``（地方特有のコード値）と、実データで確かめた競走条件名称の書き方。
地方のレースは競走条件コードがすべて ``000`` なので、クラスは競走条件名称の文字列（例 ``３歳上Ｃ３　二``・``Ｂ１－２``・``ＯＰ``）と
グレードコードから読む。
"""

from __future__ import annotations

import re

from . import codes
from .facts import FactsSource

#: 地方の競馬場コードの範囲（門別 30 〜 中京（地方）61）。ばんえい帯広（83）は入らない。
LOCAL_VENUE_RANGE: tuple[str, str] = ("30", "61")
BANEI_VENUE_CODE = "83"
#: 地方の競馬場コード → 名前（ばんえいを除く）。
LOCAL_VENUE_NAMES: dict[str, str] = {
    code: name for code, name in codes.LOCAL_VENUE_NAMES.items() if code != BANEI_VENUE_CODE
}
#: 今も開催のある地方 14場（出走別着度数地方の競馬場別の欄も、この 14場で作る）。
ACTIVE_LOCAL_VENUE_CODES: tuple[str, ...] = ("30", "35", "36", "42", "43", "44", "45", "46", "47", "48", "50", "51", "54", "55")
#: 芝のコースがある地方の競馬場（盛岡だけ）。
TURF_LOCAL_VENUE_CODES: tuple[str, ...] = ("35",)

#: 地方のクラス名 → 並び順（下から上へ。設計書 09 の A の表）。番号の無い格（Ｃ・Ｂ・Ａ）は、その格の真ん中に置く。
LOCAL_CLASS_ORDER: dict[str, int] = {
    "新馬": 0, "未勝利": 1, "年齢の条件戦": 2,
    "C4": 3, "C3": 4, "C2": 5, "C": 5, "C1": 6,
    "B4": 7, "B3": 8, "B2": 9, "B": 9, "B1": 10,
    "A4": 11, "A3": 12, "A2": 13, "A": 13, "A1": 14,
    "オープン": 15, "準重賞": 16, "重賞": 17, "Jpn3": 18, "Jpn2": 19, "Jpn1": 20,
}
#: グレードコード → クラス名（地方。nvdata-store の codes.md の 2003）。A〜C はダートグレード競走、D・P〜S は重賞、T は準重賞。
LOCAL_GRADE_CLASSES: dict[str, str] = {
    "A": "Jpn1", "B": "Jpn2", "C": "Jpn3", "D": "重賞", "P": "重賞", "Q": "重賞", "R": "重賞", "S": "重賞", "T": "準重賞",
}

#: 全角の英字と数字 → 半角。英字は A〜Z の全部を直す（ＪＲＡ認定 の Ａ を格と取り違えないため）。
_FULLWIDTH = "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９"
_HALFWIDTH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_FULLWIDTH_SPACE = "　"
#: 競走条件名称から読む言葉。格は、前に英字の無い A・B・C と、そのすぐあとの数字1桁。
_MAIDEN_PATTERN = r"新馬|初出走|未出走"
_UNWON_PATTERN = r"未勝利|認未勝"
_OPEN_PATTERN = r"(?:^|[^A-Z])OP"
_LETTER_PATTERN = r"(?:^|[^A-Z])([ABC])"
_DIGIT_PATTERN = r"(?:^|[^A-Z])[ABC] ?([1-9])"
_AGED_PATTERN = r"[0-9]歳"
#: 格の番号は 1〜3 をそのまま、4 以上はまとめて 4 にする。
_LOWEST_RANK = "4"


def normalized_name_sql(name_expr: str) -> str:
    """競走条件名称の式を、全角の英数字を半角に・全角の空白を半角にそろえた式にする。"""
    return f"translate(replace({name_expr}, '{_FULLWIDTH_SPACE}', ' '), '{_FULLWIDTH}', '{_HALFWIDTH}')"


def local_class_name_sql(name_expr: str, grade_expr: str) -> str:
    """競走条件名称とグレードコードの式から、地方のクラス名を返す CASE 式（設計書 06 の図2）。

    グレードコード → 新馬 → 未勝利 → ＯＰ → 格（Ａ・Ｂ・Ｃ と番号）→ 年齢の条件戦 → 条件不明 の順に見る。
    """
    name = normalized_name_sql(name_expr)
    by_grade = "".join(f" WHEN {grade_expr} = '{code}' THEN '{class_name}'" for code, class_name in LOCAL_GRADE_CLASSES.items())
    letter = f"regexp_extract({name}, '{_LETTER_PATTERN}', 1)"
    digit = f"regexp_extract({name}, '{_DIGIT_PATTERN}', 1)"
    rank = f"CASE WHEN {digit} IN ('1', '2', '3') THEN {digit} WHEN {digit} <> '' THEN '{_LOWEST_RANK}' ELSE '' END"
    return (
        f"CASE{by_grade}"
        f" WHEN regexp_matches({name}, '{_MAIDEN_PATTERN}') THEN '新馬'"
        f" WHEN regexp_matches({name}, '{_UNWON_PATTERN}') THEN '未勝利'"
        f" WHEN regexp_matches({name}, '{_OPEN_PATTERN}') THEN 'オープン'"
        f" WHEN regexp_matches({name}, '{_LETTER_PATTERN}') THEN {letter} || {rank}"
        f" WHEN regexp_matches({name}, '{_AGED_PATTERN}') THEN '年齢の条件戦'"
        f" ELSE '{codes.UNKNOWN_CLASS}' END"
    )


def local_class_name(name: str, grade: str) -> str:
    """``local_class_name_sql`` と同じ決まりの Python 版（テストと合成DB が使う）。"""
    normalized = name.replace(_FULLWIDTH_SPACE, " ").translate(str.maketrans(_FULLWIDTH, _HALFWIDTH))
    if grade.strip() in LOCAL_GRADE_CLASSES:
        return LOCAL_GRADE_CLASSES[grade.strip()]
    if re.search(_MAIDEN_PATTERN, normalized):
        return "新馬"
    if re.search(_UNWON_PATTERN, normalized):
        return "未勝利"
    if re.search(_OPEN_PATTERN, normalized):
        return "オープン"
    letter = re.search(_LETTER_PATTERN, normalized)
    if letter:
        digit = re.search(_DIGIT_PATTERN, normalized)
        rank = "" if digit is None else (digit.group(1) if digit.group(1) in ("1", "2", "3") else _LOWEST_RANK)
        return letter.group(1) + rank
    if re.search(_AGED_PATTERN, normalized):
        return "年齢の条件戦"
    return codes.UNKNOWN_CLASS


def _local_class_name_sql(condition_expr: str, grade_expr: str, name_expr: str) -> str:
    """``FactsSource.class_name_sql`` の形（競走条件コードの式は使わない）。"""
    return local_class_name_sql(name_expr, grade_expr)


#: 地方の元データ（nvdata-store の DuckDB）。
LOCAL_FACTS_SOURCE = FactsSource(
    name="地方", venue_range=LOCAL_VENUE_RANGE, venue_names=LOCAL_VENUE_NAMES, pedigree_table="nu__3代血統情報",
    class_name_sql=_local_class_name_sql, class_order=LOCAL_CLASS_ORDER, marker_table="nu",
)


def local_venue_code(text: str) -> str:
    """地方の競馬場の名前かコードをコードにする。知らなければ ``ValueError``。"""
    value = text.strip()
    if value in LOCAL_VENUE_NAMES:
        return value
    by_name = {name: code for code, name in LOCAL_VENUE_NAMES.items()}
    if value in by_name:
        return by_name[value]
    raise ValueError(f"知らない地方の競馬場です: {text}（{', '.join(LOCAL_VENUE_NAMES[c] for c in ACTIVE_LOCAL_VENUE_CODES)} など）")
