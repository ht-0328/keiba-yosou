"""JV-Data のコード値と、人が読む名前。

一次資料は JRA-VAN Data Lab. SDK 同梱の JV-Data 仕様書のコード表
（写しが ``../jvdata-store/docs/reference/codes.md`` にある）。ここに無いコードは記憶で足さず、仕様書を引いて足す。
"""

from __future__ import annotations

from typing import Any

#: コード表 2001.競馬場コード（中央だけ）。
VENUE_NAMES: dict[str, str] = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉",
}

#: コード表 2009.トラックコード。競馬場と組み合わせて「コース」になる。
TRACK_NAMES: dict[str, str] = {
    "10": "芝・直線", "11": "芝・左", "12": "芝・左外", "13": "芝・左内→外", "14": "芝・左外→内",
    "15": "芝・左内2周", "16": "芝・左外2周", "17": "芝・右", "18": "芝・右外",
    "19": "芝・右内→外", "20": "芝・右外→内", "21": "芝・右内2周", "22": "芝・右外2周",
    "23": "ダート・左", "24": "ダート・右", "25": "ダート・左内", "26": "ダート・右外",
    "27": "サンド・左", "28": "サンド・右", "29": "ダート・直線",
    "51": "障害・芝襷", "52": "障害・芝→ダート", "53": "障害・芝左", "54": "障害・芝",
    "55": "障害・芝外", "56": "障害・芝外→内", "57": "障害・芝内→外",
    "58": "障害・芝内2周", "59": "障害・芝外2周",
}

#: トラックコードの範囲と芝ダの対応。10〜22 が芝、23〜29 がダート（サンド含む）、51〜59 が障害。
_SURFACE_RANGES: tuple[tuple[str, str, str], ...] = (
    ("10", "22", "芝"), ("23", "29", "ダート"), ("51", "59", "障害"),
)
#: 芝ダの並び順。
SURFACE_ORDER: dict[str, int] = {"芝": 0, "ダート": 1, "障害": 2}
#: ページのファイル名に使う芝ダの英字（``reports/stats`` と同じ規則）。
SURFACE_SLUG: dict[str, str] = {"芝": "turf", "ダート": "dirt", "障害": "jump"}

#: コード表 2010.馬場状態コード。
TRACK_CONDITION: dict[str, str] = {"1": "良", "2": "稍重", "3": "重", "4": "不良"}
#: コード表 2011.天候コード。
WEATHER_NAMES: dict[str, str] = {"1": "晴", "2": "曇", "3": "雨", "4": "小雨", "5": "雪", "6": "小雪"}
#: コード表 2202.性別コード。
SEX_NAMES: dict[str, str] = {"1": "牡", "2": "牝", "3": "セン"}
#: コード表 2301.東西所属コード（名称2）。0 は未設定。
AFFILIATION_NAMES: dict[str, str] = {"1": "美浦", "2": "栗東", "3": "招待", "4": "招待"}
#: コード表 2008.重量種別コード。0 は未設定。
WEIGHT_TYPE_NAMES: dict[str, str] = {"1": "ハンデ", "2": "別定", "3": "馬齢", "4": "定量"}
#: 「今回レース脚質判定」の値。レースが終わってから決まる。
STYLE_NAMES: dict[str, str] = {"1": "逃げ", "2": "先行", "3": "差し", "4": "追込"}
#: コード表 2101.異常区分コード。0 は正常。
ABNORMAL_NAMES: dict[str, str] = {
    "0": "", "1": "出走取消", "2": "発走除外", "3": "競走除外", "4": "競走中止",
    "5": "失格", "6": "落馬再騎乗", "7": "降着",
}
#: データ区分（レース・馬毎レース情報）の意味。7 が月曜の確定成績。
STAGE_NAMES: dict[str, str] = {
    "1": "出走馬名表", "2": "出馬表", "3": "速報成績（3着まで）", "4": "速報成績（5着まで）",
    "5": "速報成績（全馬）", "6": "速報成績（全馬・通過順あり）", "7": "成績（確定）", "9": "レース中止",
    "0": "削除", "A": "地方", "B": "海外",
}
#: 競走条件コード（最若年条件）からクラス名へ。
CONDITION_NAMES: dict[str, str] = {
    "005": "1勝クラス", "010": "2勝クラス", "016": "3勝クラス",
    "701": "新馬", "702": "未出走", "703": "未勝利", "999": "オープン",
}
#: コード表 2003.グレードコード。
GRADE_NAMES: dict[str, str] = {
    "A": "G1", "B": "G2", "C": "G3", "D": "重賞", "E": "特別",
    "F": "J・G1", "G": "J・G2", "H": "J・G3", "L": "L",
}
#: クラス名の並び順（下から上へ）。目録に無いクラスは最後。
CLASS_ORDER: dict[str, int] = {
    "新馬": 0, "未出走": 1, "未勝利": 2, "1勝クラス": 3, "2勝クラス": 4, "3勝クラス": 5,
    "オープン": 6, "L": 7, "G3": 8, "G2": 9, "G1": 10, "J・G3": 11, "J・G2": 12, "J・G1": 13,
    "重賞": 14,
}
#: 条件コードにもグレードにも無いときのクラス名。
UNKNOWN_CLASS = "条件不明"

#: 芝ダの書き方のゆれ。``ダ`` でも ``ダート`` でも受ける。
_SURFACE_ALIASES: dict[str, str] = {"芝": "芝", "ダ": "ダート", "ダート": "ダート", "障": "障害", "障害": "障害"}
#: 馬場状態の書き方のゆれ。コード（1〜4）でも受ける。
_CONDITION_ALIASES: dict[str, str] = {
    "良": "1", "稍": "2", "稍重": "2", "重": "3", "不": "4", "不良": "4",
    "1": "1", "2": "2", "3": "3", "4": "4",
}
#: 性別の書き方のゆれ。
_SEX_ALIASES: dict[str, str] = {"牡": "牡", "牝": "牝", "セン": "セン", "セ": "セン", "騙": "セン"}
_VENUE_CODES: dict[str, str] = {name: code for code, name in VENUE_NAMES.items()}


def surface_of(track_code: str | None) -> str | None:
    """トラックコードから芝・ダート・障害を返す。範囲外は None。"""
    if not track_code:
        return None
    for low, high, surface in _SURFACE_RANGES:
        if low <= track_code <= high:
            return surface
    return None


def venue_code(text: str) -> str:
    """競馬場の名前かコードをコードにする。知らなければ ``ValueError``。"""
    value = text.strip()
    if value in VENUE_NAMES:
        return value
    if value in _VENUE_CODES:
        return _VENUE_CODES[value]
    raise ValueError(f"知らない競馬場です: {text}（{', '.join(VENUE_NAMES.values())} か 01〜10）")


def venue_name(code: str | None) -> str:
    """競馬場コードを名前にする。知らないコードは「場XX」。"""
    return VENUE_NAMES.get(code or "", f"場{code}")


def track_codes(text: str) -> tuple[str, ...]:
    """コースの名前（芝・右外 など）かトラックコード（18 など）を、トラックコードの組にする。"""
    value = text.strip()
    if value in TRACK_NAMES:
        return (value,)
    codes = tuple(code for code, name in TRACK_NAMES.items() if name == value)
    if codes:
        return codes
    raise ValueError(f"知らないコースです: {text}（{', '.join(TRACK_NAMES.values())}）")


def surface_name(text: str) -> str:
    """芝ダの書き方のゆれ（ダ／ダート など）を正式な名前にそろえる。"""
    try:
        return _SURFACE_ALIASES[text.strip()]
    except KeyError:
        raise ValueError(f"知らない芝ダです: {text}（芝 / ダート / 障害）") from None


def condition_code(text: str) -> str:
    """馬場状態の名前かコードをコードにする。"""
    try:
        return _CONDITION_ALIASES[text.strip()]
    except KeyError:
        raise ValueError(f"知らない馬場状態です: {text}（良 / 稍重 / 重 / 不良）") from None


def sex_name(text: str) -> str:
    """性別の書き方のゆれをそろえる。"""
    try:
        return _SEX_ALIASES[text.strip()]
    except KeyError:
        raise ValueError(f"知らない性別です: {text}（牡 / 牝 / セン）") from None


def class_name(condition_code_value: str | None, grade_code: str | None) -> str:
    """条件コードとグレードコードからクラス名を作る。重賞・L は条件コードより優先する。"""
    grade = GRADE_NAMES.get((grade_code or "").strip())
    if grade and grade != "特別":
        return grade
    return CONDITION_NAMES.get((condition_code_value or "").strip(), UNKNOWN_CLASS)


def sql_literal(value: Any) -> str:
    """SQL のリテラルにする。文字列は引用し、数はそのまま置く。"""
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def sql_case(expr: str, mapping: dict[str, Any], default: Any) -> str:
    """辞書を ``CASE expr WHEN ... END`` の式にする。"""
    whens = "".join(f" WHEN {expr} = {sql_literal(key)} THEN {sql_literal(value)}" for key, value in mapping.items())
    return f"CASE{whens} ELSE {sql_literal(default)} END"


def class_name_sql(condition_expr: str, grade_expr: str) -> str:
    """条件コードとグレードコードの式から、クラス名を返す CASE 式（:func:`class_name` の SQL 版）。"""
    graded = {code: name for code, name in GRADE_NAMES.items() if name != "特別"}
    by_grade = "".join(f" WHEN {grade_expr} = '{code}' THEN '{name}'" for code, name in graded.items())
    by_condition = "".join(f" WHEN {condition_expr} = '{code}' THEN '{name}'" for code, name in CONDITION_NAMES.items())
    return f"CASE{by_grade}{by_condition} ELSE '{UNKNOWN_CLASS}' END"


def surface_sql(track_expr: str) -> str:
    """トラックコードの式から芝・ダート・障害を返す CASE 式。"""
    whens = "".join(f" WHEN {track_expr} BETWEEN '{low}' AND '{high}' THEN '{surface}'" for low, high, surface in _SURFACE_RANGES)
    return f"CASE{whens} ELSE '?' END"
