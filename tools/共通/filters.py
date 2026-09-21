"""絞り込みの条件。CLI のフラグ名 = 画面の URL パラメータ名 = ここの項目名。

「中山の芝1600m・良馬場の1番人気」のように、事実表（``facts``）の行を絞る。
範囲は ``1600``（その値だけ）・``1400-1800``（両端を含む）・``1400-``（以上）・``-1800``（以下）で書く。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
from typing import Any

from . import codes

#: 範囲の区切り。
_RANGE_SEPARATOR = "-"
#: 日付の桁数（``YYYYMMDD``）。
_DATE_DIGITS = 8


@dataclass(frozen=True)
class Range:
    """数の範囲。片側だけ（``1400-`` / ``-1800``）も書ける。両端を含む。"""

    low: float | None
    high: float | None

    @classmethod
    def parse(cls, text: str) -> "Range":
        """``1600`` / ``1400-1800`` / ``1400-`` / ``-1800`` を範囲にする。"""
        value = str(text).strip()
        if not value:
            raise ValueError("範囲が空です")
        low_text, separator, high_text = value.partition(_RANGE_SEPARATOR)
        try:
            low = float(low_text) if low_text else None
            high = (float(high_text) if high_text else None) if separator else low
        except ValueError:
            raise ValueError(f"範囲は 1600 か 1400-1800 のように書いてください: {text}") from None
        if low is None and high is None:
            raise ValueError(f"範囲の両端が空です: {text}")
        if low is not None and high is not None and low > high:
            raise ValueError(f"範囲の下限が上限より大きいです: {text}")
        return cls(low, high)

    def sql(self, column: str) -> tuple[str, list[float]]:
        """列に対する条件と引数。"""
        if self.low is not None and self.high is not None:
            return f"{column} BETWEEN ? AND ?", [self.low, self.high]
        if self.low is not None:
            return f"{column} >= ?", [self.low]
        return f"{column} <= ?", [self.high]  # type: ignore[list-item]

    def text(self) -> str:
        """書いたときの形に戻す。"""
        if self.low is not None and self.high is not None:
            return _number(self.low) if self.low == self.high else f"{_number(self.low)}-{_number(self.high)}"
        if self.low is not None:
            return f"{_number(self.low)}-"
        return f"-{_number(self.high)}"  # type: ignore[arg-type]

    def contains(self, value: float | None) -> bool:
        """値が範囲に入るか。None は入らない。"""
        if value is None:
            return False
        return (self.low is None or value >= self.low) and (self.high is None or value <= self.high)


def _number(value: float) -> str:
    """整数なら小数点なしで書く。"""
    return str(int(value)) if value.is_integer() else str(value)


def parse_date(text: str) -> str:
    """``2024-01-01`` か ``20240101`` を ``YYYY-MM-DD`` にする。"""
    value = str(text).strip()
    if len(value) == _DATE_DIGITS and value.isdigit():
        value = f"{value[:4]}-{value[4:6]}-{value[6:]}"
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(f"日付は 2024-01-01 か 20240101 の形で書いてください: {text}") from None


@dataclass(frozen=True)
class FilterField:
    """絞り込みの項目1つ。CLI のフラグと画面のフォームをここから作る。"""

    name: str
    label: str
    kind: str  # text / range / select / date
    help: str
    example: str
    choices: tuple[str, ...] = ()


#: 絞り込みの項目の目録。順番は CLI のヘルプと画面のフォームの並び。
FILTER_FIELDS: tuple[FilterField, ...] = (
    FilterField("venue", "競馬場", "select", "競馬場の名前かコード", "東京", tuple(codes.VENUE_NAMES.values())),
    FilterField("surface", "芝ダ", "select", "芝 / ダート / 障害", "芝", tuple(codes.SURFACE_ORDER)),
    FilterField("course", "コース", "select", "コースの名前（芝・右外 など）かトラックコード", "芝・左",
                tuple(dict.fromkeys(codes.TRACK_NAMES.values()))),
    FilterField("distance", "距離", "range", "距離（m）", "1600"),
    FilterField("condition", "馬場状態", "select", "良 / 稍重 / 重 / 不良", "良", tuple(codes.TRACK_CONDITION.values())),
    FilterField("class", "クラス", "select", "クラス名", "3勝クラス", tuple(codes.CLASS_ORDER)),
    FilterField("pop", "人気", "range", "単勝人気（確定）", "1-3"),
    FilterField("odds", "単勝オッズ", "range", "単勝オッズ（確定、倍）", "1.5-2.9"),
    FilterField("frame", "枠番", "range", "枠番", "1-2"),
    FilterField("finish", "着順", "range", "確定着順（着順の付かない競走中止・失格は含まない）", "1-3"),
    FilterField("sex", "性別", "select", "牡 / 牝 / セン", "牝", tuple(codes.SEX_NAMES.values())),
    FilterField("age", "馬齢", "range", "馬齢", "3"),
    FilterField("field", "出走頭数", "range", "出走頭数", "16-18"),
    FilterField("jockey", "騎手", "text", "騎手名（略称、部分一致）", "ルメール"),
    FilterField("trainer", "調教師", "text", "調教師名（略称、部分一致）", "友道"),
    FilterField("from", "開始日", "date", "この日を含む（YYYY-MM-DD）", "2024-01-01"),
    FilterField("to", "終了日", "date", "この日を含む（YYYY-MM-DD）", "2024-12-31"),
    FilterField("month", "月", "range", "開催月（1〜12）", "6-8"),
)
FIELD_BY_NAME: dict[str, FilterField] = {f.name: f for f in FILTER_FIELDS}

#: URL パラメータ・フラグ名と、``Filters`` の属性名の対応（Python の予約語を避けた分）。
_ATTRIBUTE_OF: dict[str, str] = {"class": "class_name", "from": "date_from", "to": "date_to"}
_NAME_OF: dict[str, str] = {attribute: name for name, attribute in _ATTRIBUTE_OF.items()}


def attribute_name(name: str) -> str:
    """項目名から ``Filters`` の属性名へ。"""
    return _ATTRIBUTE_OF.get(name, name)


def field_name(attribute: str) -> str:
    """``Filters`` の属性名から項目名へ。"""
    return _NAME_OF.get(attribute, attribute)


@dataclass(frozen=True)
class Filters:
    """絞り込みの条件。すべて省略でき、省略した条件は効かない。値は正規化済み（競馬場はコード、範囲は Range）。"""

    venue: str | None = None               # 競馬場コード
    surface: str | None = None             # 芝 / ダート / 障害
    course: tuple[str, ...] | None = None  # トラックコードの組
    distance: Range | None = None
    condition: str | None = None           # 馬場状態コード 1〜4
    class_name: str | None = None
    pop: Range | None = None
    odds: Range | None = None
    frame: Range | None = None
    finish: Range | None = None
    sex: str | None = None
    age: Range | None = None
    field: Range | None = None
    jockey: str | None = None
    trainer: str | None = None
    date_from: str | None = None           # YYYY-MM-DD
    date_to: str | None = None
    month: Range | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "Filters":
        """文字列の辞書（CLI の引数・URL のパラメータ）から作る。空文字と None は無視する。"""
        given: dict[str, Any] = {}
        for raw_name, raw in values.items():
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                continue
            attribute = attribute_name(raw_name)
            if attribute not in cls.__dataclass_fields__:
                continue
            given[attribute] = _normalize(field_name(attribute), str(raw))
        return cls(**given)

    def where(self, alias: str = "") -> tuple[str, list[Any]]:
        """WHERE 句の条件（AND でつないだもの）と引数。条件が無ければ ``TRUE``。"""
        prefix = f"{alias}." if alias else ""
        clauses: list[str] = []
        params: list[Any] = []

        def add(clause: str, *values: Any) -> None:
            clauses.append(clause)
            params.extend(values)

        def add_range(column: str, value: Range | None) -> None:
            if value is not None:
                clause, args = value.sql(prefix + column)
                add(clause, *args)

        if self.venue:
            add(f"{prefix}venue_code = ?", self.venue)
        if self.surface:
            add(f"{prefix}surface = ?", self.surface)
        if self.course:
            add(f"{prefix}track_code IN ({', '.join('?' * len(self.course))})", *self.course)
        add_range("distance_m", self.distance)
        if self.condition:
            add(f"{prefix}condition_code = ?", self.condition)
        if self.class_name:
            add(f"{prefix}class_name = ?", self.class_name)
        add_range("popularity", self.pop)
        add_range("win_odds", self.odds)
        add_range("frame_no", self.frame)
        add_range("finish", self.finish)
        if self.sex:
            add(f"{prefix}sex = ?", self.sex)
        add_range("age", self.age)
        add_range("field_size", self.field)
        if self.jockey:
            add(f"contains({prefix}jockey, ?)", self.jockey)
        if self.trainer:
            add(f"contains({prefix}trainer, ?)", self.trainer)
        if self.date_from:
            add(f"{prefix}race_date >= ?", self.date_from)
        if self.date_to:
            add(f"{prefix}race_date <= ?", self.date_to)
        add_range("month", self.month)
        return " AND ".join(clauses) or "TRUE", params

    def is_empty(self) -> bool:
        """条件が1つも無いか。"""
        return all(getattr(self, f.name) is None for f in fields(self))

    def items(self) -> list[tuple[str, str]]:
        """（項目名, 書いたときの形の値）の並び。省略した項目は入れない。"""
        out: list[tuple[str, str]] = []
        for f in fields(self):
            value = getattr(self, f.name)
            if value is not None:
                out.append((field_name(f.name), _display(field_name(f.name), value)))
        return out

    def describe(self) -> str:
        """人が読む形。例: ``東京 芝・左 1600m 良 1番人気 2024-01-01〜``。条件が無ければ「全レース」。"""
        parts = [_describe_one(name, value, self) for name, value in self.items()]
        return " ".join(parts) or "全レース"

    def cli_args(self) -> str:
        """同じ条件を CLI に渡すときのフラグ。例: ``--venue 05 --pop 1``。"""
        return " ".join(f"--{name} {_quote(value)}" for name, value in self.items())


def _normalize(name: str, raw: str) -> Any:
    """項目ごとの値の正規化。知らない値は ``ValueError``（日本語の説明付き）。"""
    kind = FIELD_BY_NAME[name].kind
    if name == "venue":
        return codes.venue_code(raw)
    if name == "surface":
        return codes.surface_name(raw)
    if name == "course":
        return codes.track_codes(raw)
    if name == "condition":
        return codes.condition_code(raw)
    if name == "sex":
        return codes.sex_name(raw)
    if kind == "range":
        return Range.parse(raw)
    if kind == "date":
        return parse_date(raw)
    return raw.strip()


def _display(name: str, value: Any) -> str:
    """正規化した値を、書いたときの形に戻す。"""
    if isinstance(value, Range):
        return value.text()
    if name == "course":
        return codes.TRACK_NAMES[value[0]] if len(value) == 1 else ",".join(value)
    if name == "condition":
        return codes.TRACK_CONDITION[value]
    return str(value)


#: 読みやすい書き方の型。値の前後に付ける文字。
_DESCRIBE_FORMAT: dict[str, str] = {
    "distance": "{}m", "pop": "{}番人気", "odds": "{}倍", "frame": "{}枠", "finish": "{}着", "age": "{}歳",
    "field": "{}頭", "from": "{}〜", "to": "〜{}", "month": "{}月",
}


def _describe_one(name: str, value: str, filters: Filters) -> str:
    """1項目の読みやすい書き方。"""
    if name == "venue":
        return codes.venue_name(filters.venue)
    return _DESCRIBE_FORMAT.get(name, "{}").format(value)


def _quote(value: str) -> str:
    """空白を含む値は引用符で包む。"""
    return f'"{value}"' if " " in value else value
