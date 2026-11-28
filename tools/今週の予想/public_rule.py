"""的中実績の公開ルール（2段）: 全レースで直した ◎ の単勝を買い、直した ◎ の期待値が線以上のレースは勝負として馬単も買う。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from 今週の予想.bet_shapes import BetShapes
from 今週の予想.forecast_columns import HORSE_NO, MARK, PUBLIC_RULE

#: 見出しのことば。
LABEL_ALL = "公開ルール（全レース）"
LABEL_SHOBU = "公開ルール（勝負）"
#: 1点の金額（円）。
STAKE_YEN = 100
#: 券種の名前（払戻を引くときの名前）。
WIN, EXACTA = "単勝", "馬単"
#: 判定する時点（予想の JSON の timing）。
_RACE_DAY = "当日"
_TOP_MARK = "◎"


@dataclass(frozen=True)
class PublicRule:
    """1レースの公開ルールの判定（研究「的中実績の公開ルール」の 02）。予想の JSON の ``public_rule``（``PublicRulePicker.judge``）を読む。

    - 全レース: 当日の予想の全レースで、直した ◎（1着の確率を直した上での、単勝 30倍以下の期待値1位）の単勝を ``STAKE_YEN`` 円。
    - 勝負: 直した ◎ の期待値が線（1.25）以上のレースは、単勝に加えて、馬単 ◎→相手（直した1着の確率の上位3頭）を各 ``STAKE_YEN`` 円。
    1レースの文・発走前の通知（``RaceMessage``）・その日の結果（``RaceResult``）が同じ判定を使う。

    例: 直した ◎ が 5番・期待値 1.31・相手 3・8・11 なら、全レースは「単勝 5 100円」、勝負は
    「単勝 5 100円 ／ 馬単 1着流し 5 → 3・8・11 各 100円（4点 400円）」。
    """

    top: int | None
    partners: tuple[int, ...]
    value: float | None
    line: float | None
    shobu: bool
    marked_top: int | None
    reason: str

    @classmethod
    def of(cls, forecast: dict[str, Any]) -> PublicRule:
        marked_top = next((int(horse[HORSE_NO]) for horse in forecast.get("horses") or []
                           if horse.get(MARK) == _TOP_MARK and horse.get(HORSE_NO) is not None), None)
        if forecast.get("timing") != _RACE_DAY:
            return cls(None, (), None, None, False, marked_top, "当日の予想で判定する")
        judged = forecast.get(PUBLIC_RULE)
        if not judged:
            return cls(None, (), None, None, False, marked_top, "この予想には入っていない（前の版の予想）")
        if not judged.get("ready"):
            return cls(None, (), None, judged.get("line"), False, marked_top, str(judged.get("reason") or "判定できない"))
        return cls(int(judged["top"]), tuple(int(number) for number in judged.get("partners") or ()), float(judged["value"]),
                   float(judged["line"]), bool(judged["shobu"]), marked_top, "")

    @property
    def buys(self) -> bool:
        """全レースの段で買うか。"""
        return self.top is not None

    def lines(self) -> list[str]:
        """通知・1レースの文の行（全レースの段と勝負の段の2行）。"""
        return [self.all_line(), self.shobu_line()]

    def all_line(self) -> str:
        if self.top is None:
            return f"{LABEL_ALL}: なし（{self.reason}）"
        return f"{LABEL_ALL}: {WIN} {self.top} {STAKE_YEN:,}円{self._top_note()}"

    def shobu_line(self) -> str:
        if self.top is None:
            return f"{LABEL_SHOBU}: なし（{self.reason}）"
        if not self.shobu:
            return f"{LABEL_SHOBU}: なし（直した ◎ の期待値 {self.value:.2f}。{self.line:.2f} 以上で勝負）"
        exacta = BetShapes().text([f"{self.top}→{partner}" for partner in self.partners])
        points = 1 + len(self.partners)
        return (f"{LABEL_SHOBU}: {WIN} {self.top} {STAKE_YEN:,}円 ／ {EXACTA} {exacta} 各 {STAKE_YEN:,}円"
                f"（{points}点 {points * STAKE_YEN:,}円。直した ◎ の期待値 {self.value:.2f}）")

    def stakes_all(self) -> list[tuple[str, str, int]]:
        """全レースの段の精算に使う、（券種の名前, 組番, 金額）の並び。買わなければ空。"""
        return [] if self.top is None else [(WIN, f"{self.top:02d}", STAKE_YEN)]

    def stakes_shobu(self) -> list[tuple[str, str, int]]:
        """勝負の段の精算に使う並び（単勝と馬単）。勝負でなければ空。"""
        if self.top is None or not self.shobu:
            return []
        return [(WIN, f"{self.top:02d}", STAKE_YEN), *((EXACTA, f"{self.top:02d}{partner:02d}", STAKE_YEN) for partner in self.partners)]

    def _top_note(self) -> str:
        """直した ◎ が印の ◎ と違う馬なら、その旨。"""
        if self.marked_top is None or self.marked_top == self.top:
            return ""
        return f"（印の ◎ {self.marked_top} とは別の馬）"
