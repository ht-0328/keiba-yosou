"""券種ごと・年ごとに、型の数え上げに使う標準の形の組の表を作る。"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboBlend, ComboBlendWeights
from yosou.shared.combo_value.combo_blend import VALUE as BLEND_VALUE

from .formation_mask import POSITIONS
from .grades_table import CELL
from .horse_slots import POSITION, THRESHOLD_COLUMNS, HorseSlots
from .ticket_picker import ODDS, VALUE

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from レースの種類ごとの買い方.analysis.combo_features import ComboFeatures  # noqa: E402

#: 扱う券種（表に出す順）。
BRACKET_LABEL = "枠連"
TICKET_LABELS: tuple[str, ...] = (TicketType.WIN.label, TicketType.PLACE.label, BRACKET_LABEL, TicketType.QUINELLA.label, TicketType.EXACTA.label,
                                  TicketType.WIDE.label, TicketType.TRIO.label, TicketType.TRIFECTA.label)
#: 組の表（``combos/<券種>_<年>.parquet``）のある券種。
COMBO_TICKETS: tuple[TicketType, ...] = (TicketType.QUINELLA, TicketType.EXACTA, TicketType.WIDE, TicketType.TRIO, TicketType.TRIFECTA)
#: 単勝・複勝の、印を付けた表の列（期待値・オッズ・払戻）。
_SINGLE_COLUMNS: dict[str, tuple[str, str, str]] = {
    TicketType.WIN.label: ("win_value", "win_odds", "win_payout"), TicketType.PLACE.label: ("place_value", "place_odds_low", "place_payout"),
}
#: 標準の列。
BASE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", CELL, VALUE, ODDS, "payout")


def horse_count(label: str) -> int:
    """券種の馬の数（枠連は 2）。"""
    if label in _SINGLE_COLUMNS:
        return 1
    if label == BRACKET_LABEL:
        return 2
    return next(ticket for ticket in COMBO_TICKETS if ticket.label == label).spec.horse_count


class CombosSource:
    """研究「複勝以外の回収率100超」の組の表（券種ごと・年ごとの全部の組）・印を付けた表（単勝・複勝）・研究「レースの種類ごとの買い方」の枠連の表から、
    券種ごと・年ごとに、型の数え上げに使う標準の形（``BASE_COLUMNS`` と ``pos1``〜・``h1``〜）の表を作る（docs/01 の 2）。

    - 組の券種（馬連・馬単・ワイド・3連複・3連単）: 4つのもとの対数（``ComboFeatures``）に本番の重み（``weights``。``combo_blend.json``）を掛けた
      組の確率 × 確定オッズを期待値にする（``ComboBlend``。今の重みで過去を数えた参考）。
    - 単勝・複勝: 印を付けた表の馬ごとの期待値（1着の確率 × 単勝オッズ、3着以内の確率 × 複勝の見込みの倍率）とオッズ・払戻。
    - 枠連: 枠連の表の期待値（枠連の重みで合わせた組の確率 × オッズ）。枠の位置は、枠の中の馬の位置の最小（``frames``: race_id・horse_no・frame）。
    ``slots`` は ``HorseSlots.build``、``grades`` は ``GradesTable.build`` の表。セルの無いレース（◎ が無い）と、種類の分からないレースは落ちる。
    確率の線で相手を決める型のために、レースごとの線以上の馬の数（``HorseSlots.partner_counts``。列 ``n50``・``n25``）も付ける。
    """

    def __init__(self, combos_folder: Path, marked: pd.DataFrame, kinds: pd.DataFrame, weights: Mapping[TicketType, ComboBlendWeights],
                 slots: pd.DataFrame, grades: pd.DataFrame, bracket: pd.DataFrame | None = None, frames: pd.DataFrame | None = None) -> None:
        self._features = ComboFeatures(Path(combos_folder))
        self._marked = marked
        self._kinds = kinds
        self._weights = dict(weights)
        self._slots = slots.assign(race_id=lambda frame: frame["race_id"].astype(str), horse_no=lambda frame: frame["horse_no"].astype(int))
        self._grades = grades[["race_id", "race_date", CELL]].assign(race_id=lambda frame: frame["race_id"].astype(str))
        self._grades = self._grades.merge(HorseSlots().partner_counts(marked), on="race_id", how="left")
        for column in THRESHOLD_COLUMNS.values():
            self._grades[column] = self._grades[column].fillna(0).astype(int)
        self._bracket = bracket
        self._frame_slots = self._frame_positions(frames) if frames is not None else None

    def load(self, label: str, year: int) -> pd.DataFrame:
        if label in _SINGLE_COLUMNS:
            return self._single(label, year)
        if label == BRACKET_LABEL:
            return self._bracket_combos(year)
        return self._combos(next(ticket for ticket in COMBO_TICKETS if ticket.label == label), year)

    def _single(self, label: str, year: int) -> pd.DataFrame:
        value, odds, payout = _SINGLE_COLUMNS[label]
        rows = self._marked[pd.to_datetime(self._marked["race_date"]).dt.year == year]
        table = pd.DataFrame({"race_id": rows["race_id"].astype(str).to_numpy(), "h1": rows["horse_no"].astype(int).to_numpy(),
                              VALUE: rows[value].astype(float).to_numpy(), ODDS: rows[odds].astype(float).to_numpy(),
                              "payout": rows[payout].astype(float).to_numpy()})
        return self._finish(self._with_positions(table, 1), 1)

    def _combos(self, ticket_type: TicketType, year: int) -> pd.DataFrame:
        features = self._features.of(ticket_type, year, self._kinds)
        blended = ComboBlend().of(ticket_type, features, self._weights[ticket_type])
        count = ticket_type.spec.horse_count
        table = blended[["race_id", *(f"h{at}" for at in range(1, count + 1)), "odds", "payout", BLEND_VALUE]].rename(columns={BLEND_VALUE: VALUE})
        return self._finish(self._with_positions(table, count), count)

    def _bracket_combos(self, year: int) -> pd.DataFrame:
        if self._bracket is None or self._frame_slots is None:
            raise LookupError("枠連の表か枠番の表がありません（materials.py frames）")
        rows = self._bracket[pd.to_datetime(self._bracket["race_date"]).dt.year == year]
        table = pd.DataFrame({"race_id": rows["race_id"].astype(str).to_numpy(), "h1": rows["h1"].astype(int).to_numpy(),
                              "h2": rows["h2"].astype(int).to_numpy(), VALUE: rows["value"].astype(float).to_numpy(),
                              ODDS: rows["odds"].astype(float).to_numpy(), "payout": rows["payout"].astype(float).to_numpy()})
        for at in (1, 2):
            keyed = self._frame_slots.rename(columns={"frame": f"h{at}", POSITION: POSITIONS[at - 1]})
            table = table.merge(keyed, on=["race_id", f"h{at}"], how="left")
        return self._finish(table, 2)

    def _with_positions(self, table: pd.DataFrame, count: int) -> pd.DataFrame:
        for at in range(1, count + 1):
            keyed = self._slots.rename(columns={"horse_no": f"h{at}", POSITION: POSITIONS[at - 1]})
            table = table.merge(keyed, on=["race_id", f"h{at}"], how="left")
        return table

    def _finish(self, table: pd.DataFrame, count: int) -> pd.DataFrame:
        merged = table.merge(self._grades, on="race_id", how="inner")
        columns = [*BASE_COLUMNS, *THRESHOLD_COLUMNS.values(), *POSITIONS[:count], *(f"h{at}" for at in range(1, count + 1))]
        return merged[columns].sort_values(["race_id", *(f"h{at}" for at in range(1, count + 1))], kind="stable").reset_index(drop=True)

    def _frame_positions(self, frames: pd.DataFrame) -> pd.DataFrame:
        """枠ごとの位置（枠の中の馬の位置の最小。消だけの枠は欠損値）。列 race_id・frame・pos。"""
        keyed = frames.assign(race_id=lambda frame: frame["race_id"].astype(str), horse_no=lambda frame: frame["horse_no"].astype(int),
                              frame=lambda frame: frame["frame"].astype(int))[["race_id", "horse_no", "frame"]]
        merged = keyed.merge(self._slots, on=["race_id", "horse_no"], how="left")
        return merged.groupby(["race_id", "frame"], as_index=False)[POSITION].min()
