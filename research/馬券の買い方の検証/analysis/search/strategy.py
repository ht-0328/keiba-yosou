"""戦略1つ。"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Strategy:
    """参加パターン・しきい値・買い方の組み合わせ1つ。

    - ``pattern_key``: 参加パターンの鍵（``01all`` など）。
    - ``wide_plan``・``narrow_plan``: 広め・少点数の買い方の名前（使わないパターンでは None）。
    - ``upset_share``: 荒れ度の線を「上位 x%」で表したもの。``upset_threshold``: それを探索期間で確率に直した値（確認期間でもこの値を使う）。
    - ``form_threshold``・``danger_threshold``: 本命の確率（以上）・危険確率（未満）の線。
    - ``top_k``: 週の上位 k。
    """

    pattern_key: str
    wide_plan: str | None
    narrow_plan: str | None
    upset_share: float | None
    upset_threshold: float | None
    form_threshold: float | None
    danger_threshold: float | None
    top_k: int | None

    @property
    def name(self) -> str:
        """人が読める短い名前（結果の表と JSON の鍵）。"""
        parts = [
            self.pattern_key,
            f"u{self.upset_share:.2f}" if self.upset_share is not None else None,
            f"f{self.form_threshold:.2f}" if self.form_threshold is not None else None,
            f"d{self.danger_threshold:.2f}" if self.danger_threshold is not None else None,
            f"k{self.top_k}" if self.top_k is not None else None,
            f"広め={self.wide_plan}" if self.wide_plan else None,
            f"少点数={self.narrow_plan}" if self.narrow_plan else None,
        ]
        return "|".join(part for part in parts if part is not None)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, saved: dict[str, object]) -> Strategy:
        return cls(**{key: saved[key] for key in cls.__dataclass_fields__})
