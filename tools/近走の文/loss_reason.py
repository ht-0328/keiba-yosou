"""負けた走の敗因の候補。"""

from __future__ import annotations

from collections.abc import Sequence

from .past_run import PastRun
from .record_contrast import RecordContrast

#: 休み明けとみなす前走からの日数（全頭評価と同じ中9週以上）。
REST_DAYS = 63
#: 馬体重の増減がこれ以上なら書く（kg）。
WEIGHT_SWING = 10
#: 重い馬場。
HEAVY_GOINGS: tuple[str, ...] = ("重", "不良")


class LossReason:
    """4着以下の走について、敗因の候補を事実から定型で出す。材料が無ければ空（推測は書かない）。

    候補は、回顧の不利（出遅れ・展開が向かなかった・バイアスと逆）、初めての条件（初出走・重い馬場・芝ダ・距離）、
    前走からの変化（距離の延長・短縮、上のクラス）、その走までの成績の対比（重い馬場・芝ダ・距離・クラスで、ほかの条件より
    3着以内率がはっきり低いとき。``RecordContrast``）、休み明け、馬体重の大きな増減。
    対比はその走までの走で数える（後の走は使わない。時系列で読んだときに、そのときの材料だけで書いてある形にする）。
    """

    def __init__(self) -> None:
        self._contrast = RecordContrast()

    def of(self, run: PastRun, history: Sequence[PastRun]) -> list[str]:
        """``history`` はその馬の過去走（``run`` を含む。古い順）。"""
        if not run.lost:
            return []
        reasons: list[str] = []
        if run.handicaps:
            reasons.append("不利: " + "・".join(run.handicaps))
        earlier = [other for other in history if (other.race_date, other.race_id) < (run.race_date, run.race_id)]
        if not earlier:
            return reasons + ["初出走"]
        previous = earlier[-1]
        reasons += self._going(run, earlier)
        reasons += self._surface(run, earlier)
        reasons += self._distance(run, earlier, previous)
        reasons += self._class(run, earlier, previous)
        reasons += self._condition(run)
        return reasons

    def _going(self, run: PastRun, earlier: Sequence[PastRun]) -> list[str]:
        if run.condition not in HEAVY_GOINGS:
            return []
        heavy = [other for other in earlier if other.condition in HEAVY_GOINGS]
        if not heavy:
            return ["初めての重・不良の馬場"]
        firm = [other for other in earlier if other.condition and other.condition not in HEAVY_GOINGS]
        found = self._contrast.of([*heavy, run], firm)
        return [f"重い馬場（重・不良では {found[0].text}、良・稍重では {found[1].text}）"] if found else []

    def _surface(self, run: PastRun, earlier: Sequence[PastRun]) -> list[str]:
        if not run.surface:
            return []
        same = [other for other in earlier if other.surface == run.surface]
        if not same:
            return [f"初めての{run.surface}"]
        different = [other for other in earlier if other.surface and other.surface != run.surface]
        found = self._contrast.of([*same, run], different)
        return [f"{run.surface}（{run.surface}では {found[0].text}、ほかの芝ダでは {found[1].text}）"] if found else []

    def _distance(self, run: PastRun, earlier: Sequence[PastRun], previous: PastRun) -> list[str]:
        change = ""
        if previous.distance_m and previous.distance_m != run.distance_m:
            change = "延長" if run.distance_m > previous.distance_m else "短縮"
        same = [other for other in earlier if other.distance_m == run.distance_m]
        if not same:
            return [f"初めての {run.distance_m}m" + (f"（前走 {previous.distance_m}m から{change}）" if change else "")]
        reasons = [f"前走から距離{change}（{previous.distance_m}m → {run.distance_m}m）"] if change else []
        different = [other for other in earlier if other.distance_m != run.distance_m]
        found = self._contrast.of([*same, run], different)
        if found:
            reasons.append(f"距離（{run.distance_m}m では {found[0].text}、ほかの距離では {found[1].text}）")
        return reasons

    def _class(self, run: PastRun, earlier: Sequence[PastRun], previous: PastRun) -> list[str]:
        if run.class_order is None:
            return []
        reasons = []
        if previous.class_order is not None and run.class_order > previous.class_order:
            reasons.append(f"前走より上のクラス（{previous.class_name} → {run.class_name}）")
        same = [other for other in earlier if other.class_order == run.class_order]
        lower = [other for other in earlier if other.class_order is not None and other.class_order < run.class_order]
        found = self._contrast.of([*same, run], lower)
        if found:
            reasons.append(f"{run.class_name}（{run.class_name}では {found[0].text}、下のクラスでは {found[1].text}）")
        return reasons

    def _condition(self, run: PastRun) -> list[str]:
        reasons = []
        if run.interval_days is not None and run.interval_days >= REST_DAYS:
            reasons.append(f"休み明け（前走から {run.interval_days}日）")
        if run.weight_change is not None and abs(run.weight_change) >= WEIGHT_SWING:
            reasons.append(f"馬体重 {run.weight_change:+d}kg")
        return reasons
