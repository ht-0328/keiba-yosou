"""組の期待値の高い順に N 点を買う形を、全部の組の表から数える（印の形で届かなかったときの次の候補）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import HorseRatio
from yosou.shared.combo_value.horse_ratio import TOP3_RATIO, WIN_RATIO

from 今週の予想.forecast_columns import MARKET_TOP3, MARKET_WIN, PROBABILITY, WIN_PROBABILITY

from .shape_counter import MEAN_VALUE, POINTS, RETURN, SHAPE
from .ticket_shape import EXACTA, QUINELLA, TRIFECTA, TRIO, WIDE

#: 券種 → （研究「複勝以外の回収率100超」の組の表のファイル名の頭, 券種）。
_FILES = {QUINELLA: ("quinella", TicketType.QUINELLA), WIDE: ("wide", TicketType.WIDE), EXACTA: ("exacta", TicketType.EXACTA),
          TRIO: ("trio", TicketType.TRIO), TRIFECTA: ("trifecta", TicketType.TRIFECTA)}


@dataclass(frozen=True)
class ValueRankShape:
    """組の期待値の高い順に買う形1つ。

    オッズが ``cap`` 以下で、モデルが見た組の確率（市場が見た組の確率 × 各馬の比）が ``floor`` 以上の組を、組の期待値の高い順に ``points`` 点まで並べ、
    期待値が ``line`` 未満の組を外す（外しても1点は買う。全部の重賞を買うため。研究「重賞の買い方」4回目と同じ形）。
    """

    ticket: str
    points: int
    cap: float | None = None
    floor: float = 0.0
    line: float | None = None

    @property
    def name(self) -> str:
        parts = [f"組の期待値の上位 {self.points}点"]
        if self.cap is not None:
            parts.append(f"{self.cap:g}倍まで")
        if self.floor:
            parts.append(f"組の確率 {self.floor:.1%} 以上")
        if self.line is not None:
            parts.append(f"期待値 {self.line:g} 以上（1点は買う）")
        return "・".join(parts)


def value_rank_shapes() -> tuple[ValueRankShape, ...]:
    """候補（4回目の候補に、馬連・ワイド・3連複を足したもの）。"""
    caps = {QUINELLA: (None, 30.0, 100.0), WIDE: (None, 20.0, 50.0), EXACTA: (None, 50.0, 100.0, 300.0),
            TRIO: (None, 100.0, 300.0, 1000.0), TRIFECTA: (None, 300.0, 1000.0, 3000.0)}
    floors = {QUINELLA: (0.0, 0.01, 0.03), WIDE: (0.0, 0.03, 0.1), EXACTA: (0.0, 0.01, 0.03),
              TRIO: (0.0, 0.005, 0.01), TRIFECTA: (0.0, 0.002, 0.005)}
    return tuple(ValueRankShape(ticket, points, cap, floor, line)
                 for ticket in _FILES
                 for points, cap, floor, line in product((1, 2, 3, 5, 10, 20), caps[ticket], floors[ticket], (None, 1.0, 1.2)))


class ValueRankCounter:
    """全部の組の表（``combos/<券種>_<年>.parquet``）の重賞の組に、この予想の比を掛けて組の期待値を出し、形ごと・重賞ごとに数える。

    組の期待値 = 市場が見た組の確率（``q``）× 各位置の馬の比 × オッズ（設計書「買うレースと買い目を決める」07 の 2 の式。``q`` はオッズの逆数をレースで合計 1 にしたもの）。
    トリガミ（どれが当たっても投資より戻りが少ない組）は外す。結果の形は ``ShapeCounter.count`` と同じ（``shape`` は ``offset`` からの番号）。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def count(self, marked: pd.DataFrame, shapes: Sequence[ValueRankShape], years: Sequence[int], offset: int) -> pd.DataFrame:
        ratios = self._ratios(marked)
        dates = marked.drop_duplicates("race_id").set_index("race_id")["race_date"]
        parts = []
        for ticket in dict.fromkeys(shape.ticket for shape in shapes):
            combos = self._combos(ticket, years, set(dates.index.astype("int64")), ratios)
            for index, shape in enumerate(shapes):
                if shape.ticket == ticket:
                    parts.append(self._one(combos, shape, offset + index))
        table = pd.concat(parts, ignore_index=True)
        table["race_id"] = table["race_id"].astype(str)
        table["race_date"] = table["race_id"].map(dates)
        return table

    def _ratios(self, marked: pd.DataFrame) -> pd.DataFrame:
        ratio = HorseRatio().of(marked[PROBABILITY], marked[MARKET_TOP3], marked[WIN_PROBABILITY], marked[MARKET_WIN])
        return pd.DataFrame({"rid": marked["race_id"].astype("int64").to_numpy(), "horse": marked["horse_no"].astype(int).to_numpy(),
                             WIN_RATIO: ratio[WIN_RATIO].to_numpy(), TOP3_RATIO: ratio[TOP3_RATIO].to_numpy()})

    def _combos(self, ticket: str, years: Sequence[int], race_ids: set[int], ratios: pd.DataFrame) -> pd.DataFrame:
        stem, ticket_type = _FILES[ticket]
        count = ticket_type.spec.horse_count
        columns = ["rid", *(f"h{at}" for at in range(1, count + 1)), "odds", "q", "payout"]
        frames = [pq.read_table(self._folder / f"{stem}_{year}.parquet", columns=columns, filters=[("rid", "in", list(race_ids))]).to_pandas()
                  for year in years if (self._folder / f"{stem}_{year}.parquet").exists()]
        combos = pd.concat(frames, ignore_index=True)
        product_ = np.ones(len(combos))
        for at in range(1, count + 1):
            column = WIN_RATIO if (ticket_type.spec.is_ordered and at == 1) else TOP3_RATIO
            keyed = combos[["rid", f"h{at}"]].rename(columns={f"h{at}": "horse"}).astype({"horse": int})
            product_ *= keyed.merge(ratios[["rid", "horse", column]], on=["rid", "horse"], how="left")[column].to_numpy()
        probability = combos["q"].to_numpy() * product_
        return pd.DataFrame({"race_id": combos["rid"].to_numpy(), "odds": combos["odds"].to_numpy(), "payout": combos["payout"].to_numpy(),
                             "probability": probability, "value": probability * combos["odds"].to_numpy()}).dropna(subset=["value"])

    def _one(self, combos: pd.DataFrame, shape: ValueRankShape, index: int) -> pd.DataFrame:
        kept = combos[(combos["odds"] > 0) & (combos["probability"] >= shape.floor)]
        if shape.cap is not None:
            kept = kept[kept["odds"] <= shape.cap]
        kept = kept.sort_values(["race_id", "value"], ascending=[True, False])
        kept = kept[kept.groupby("race_id").cumcount() < shape.points]
        if shape.line is not None:
            first = kept.groupby("race_id").cumcount() == 0
            kept = kept[first | (kept["value"] >= shape.line)]
        kept = self._without_torigami(kept)
        grouped = kept.groupby("race_id")
        return pd.DataFrame({"race_id": grouped.size().index, SHAPE: index, POINTS: grouped.size().to_numpy(),
                             RETURN: grouped["payout"].sum().to_numpy(), MEAN_VALUE: grouped["value"].mean().to_numpy()})

    def _without_torigami(self, kept: pd.DataFrame) -> pd.DataFrame:
        """レースごとに、いちばん安い組のオッズが点数以下なら外す、を繰り返したのと同じ組を残す。

        オッズの安い順に i 番目（0 から）の組まで外したとき、残りは n − i 点。オッズは安い順に増え、n − i は減るので、
        「オッズ > n − i」が成り立つ組から先を全部残せばよい。
        """
        ordered = kept.sort_values(["race_id", "odds"])
        rank = ordered.groupby("race_id").cumcount()
        size = ordered.groupby("race_id")["odds"].transform("size")
        return ordered[ordered["odds"].to_numpy() > (size - rank).to_numpy()]
