"""期待値の線を、選ぶ期間の結果だけで決め、確かめる期間の結果で使うかどうかを決める。"""

from __future__ import annotations

from line_decision import LineDecision

#: 試す線。今の線 1.2 から上げていく。
CANDIDATE_LINES: tuple[float, ...] = (1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0, 2.5, 3.0)
#: 線を選ぶときに要る、選ぶ期間の最少の点数（少なすぎる線は、たまたまの大当たりで下限が上がりうる）。
MIN_BETS = 100
#: 複勝の回収率の下限（開催日単位のブートストラップの 90% の幅の下側）が、これ以上なら届いたとする。
LOWER_BOUND_FLOOR = 1.0


class LineSelection:
    """選ぶ期間で「点数が足り、複勝の回収率の下限が 100% に届く」いちばん低い線を選び、確かめる期間でも届くかを見る。

    確かめる期間の結果は、線を選ぶのには使わない（選ぶ期間と確かめる期間を分ける）。
    どちらかで届かなければ、線は None（「買い」を出さず「参考」にする）。
    """

    def decide(self, choose: dict[float, dict], confirm: dict[float, dict]) -> LineDecision:
        """``choose``・``confirm`` は、線ごとの買った結果（``evaluation.bet_result`` の辞書）。"""
        passing = [line for line in sorted(choose) if self.reaches(choose[line])]
        if not passing:
            return LineDecision(None, "選ぶ期間で、複勝の回収率の下限が 100% に届く線が無い")
        line = passing[0]
        if not self.reaches(confirm[line]):
            return LineDecision(None, f"選ぶ期間で選んだ線 {line:g} が、確かめる期間では下限 100% に届かない")
        return LineDecision(line, f"選ぶ期間で下限 100% に届いたいちばん低い線 {line:g} が、確かめる期間でも届いた")

    @staticmethod
    def reaches(result: dict) -> bool:
        lower = result.get("複勝回収率の下限")
        return result.get("点数", 0) >= MIN_BETS and lower is not None and lower >= LOWER_BOUND_FLOOR
