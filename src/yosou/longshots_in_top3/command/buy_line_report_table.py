"""保存した「買い」の線で買ったときの成績を、検証・テストの期間ごとに表にする。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.shared.command.cell_format import rounded
from yosou.shared.dataset import RACE_DATE
from yosou.shared.dataset.column_names import PLACE_PAYOUT, POPULARITY
from yosou.shared.feature import PredictionTiming
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE
from yosou.shared.workflow.calibration_check import PART, PART_TEST, PART_VALID, SEGMENT, TIMING

from ..buy_line import DayBootstrapInterval

#: 区分を合わせた行の、区分の列の値。
WHOLE = "全体"
#: 途中の列の名前（その行の馬の区分の線）。
_LINE = "線"
#: 「穴馬を選べているか」を見る人気の線（10番人気以下）。
_LONGSHOT_POPULARITY = 10
#: 複勝の払戻は 100円あたりの円。
_STAKE = 100.0


class BuyLineReportTable:
    """確率のずれの確かめ（``CalibrationCheck``）の材料の表と、保存した「買い」の線から、線以上の穴馬の複勝を全部 100円ずつ
    買ったときの成績を、時点 × 区分（と区分を合わせた全体）× 期間ごとに表にする（設計書 16 の 3）。

    列は、線・点数・予想の的中率・実際の的中率・回収率・開催日を単位にしたブートストラップの 90% の幅・10番人気以下の割合。
    線は検証期間だけで決めたものなので、テスト期間の行が「確かめる期間」の結果になる。
    ``lines`` は時点 → 区分 → 線（``BuyLineRepository.load()`` の形）。線の無い区分は買わない（点数 0）。
    ``zones`` は区分の名前の並び（表の並べ順。例: 中穴・大穴）。
    """

    def __init__(self, frame: pd.DataFrame, lines: dict[PredictionTiming, dict[str, float]], zones: Sequence[str]) -> None:
        self._frame = frame
        self._lines = {(timing.label, zone): value for timing, by_zone in lines.items() for zone, value in by_zone.items()}
        self._interval = DayBootstrapInterval()
        timings = [timing.label for timing in PredictionTiming]
        self._rank = {
            TIMING: {label: position for position, label in enumerate(timings)},
            PART: {PART_VALID: 0, PART_TEST: 1},
            SEGMENT: {label: position for position, label in enumerate([*zones, WHOLE])},
        }

    def table(self) -> Table:
        valued = self._frame[self._frame[PLACE_VALUE].notna()]
        valued = valued.assign(**{_LINE: [self._lines.get(key, np.nan) for key in zip(valued[TIMING], valued[SEGMENT])]})
        by_zone = [self._row(timing, zone, part, group)
                   for (timing, zone, part), group in valued.groupby([TIMING, SEGMENT, PART], sort=False)]
        whole = [self._row(timing, WHOLE, part, group)
                 for (timing, part), group in valued.groupby([TIMING, PART], sort=False)]
        return Table(
            [TIMING, PART, SEGMENT, "線", "点数", "予想の的中率", "実際の的中率", "回収率", "90%の下限", "90%の上限",
             "10番人気以下の割合"],
            sorted(by_zone + whole, key=self._order), title="「買い」の線で買ったときの成績",
            note="線以上の穴馬の複勝を全部 100円ずつ買ったときの成績。線は学習のときに検証期間だけで決めたもので、"
                 "テスト期間が確かめる期間。90% の幅は開催日を単位にしたブートストラップ。回収率が 100% を超え、"
                 "下限も 100% 以上なら、偶然の幅を考えても 100% を超えている。確定オッズで見積もるので、実際に買う時点より楽観側。",
        )

    def _row(self, timing: str, zone: str, part: str, group: pd.DataFrame) -> list[object]:
        bought = group[group[PLACE_VALUE] >= group[_LINE].fillna(np.inf)]
        paid = pd.to_numeric(bought[PLACE_PAYOUT], errors="coerce").fillna(0.0)
        points = len(bought)
        low, high = self._interval.of(bought[RACE_DATE], paid) if points else (np.nan, np.nan)
        longshots = pd.to_numeric(bought[POPULARITY], errors="coerce") >= _LONGSHOT_POPULARITY
        return [
            timing, part, zone, self._line_text(zone, group), points,
            rounded(bought[PLACE_PROBABILITY].mean()) if points else None,
            rounded((paid > 0).mean()) if points else None,
            rounded(paid.sum() / (_STAKE * points)) if points else None,
            rounded(low), rounded(high), rounded(longshots.mean()) if points else None,
        ]

    def _line_text(self, zone: str, group: pd.DataFrame) -> object:
        """線の欄。区分の行はその線（無ければ「なし」）、全体の行は「区分ごと」。"""
        if zone == WHOLE:
            return "区分ごと"
        line = group[_LINE].iloc[0]
        return "なし" if pd.isna(line) else line

    def _order(self, row: list[object]) -> tuple[int, int, int]:
        """時点 → 期間（検証・テスト）→ 区分（全体は最後）の順に並べる。行の先頭3つが 時点・期間・区分。"""
        return self._rank[TIMING][row[0]], self._rank[PART][row[1]], self._rank[SEGMENT][row[2]]
