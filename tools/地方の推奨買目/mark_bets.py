"""1レースの地方の印の買い目の見せ方（見出しの1行と買い方ごとの行。出せないときは理由）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkBets:
    """``heading`` は ``MarkReturn.heading()``（買うか見送りか・合計・当たったときに戻る額）か、出せないときの「なし（理由）」。
    ``lines`` は買い方ごとの行（``RaceDescriber.mark_returns`` の書き方。先頭の「- 」は付けない）。"""

    heading: str = ""
    lines: tuple[str, ...] = ()

    @classmethod
    def none(cls, reason: str) -> MarkBets:
        return cls(f"なし（{reason}）")

    @property
    def empty(self) -> bool:
        """見せるものが何も無い（前日の時点など）。"""
        return not self.heading
