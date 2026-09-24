"""勝負するレースを選ぶための、レース単位の表を作る。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..combined.horse_columns import FORM_PROBABILITY
from ..marks.mark import MARK, Mark
from ..marks.mark_material import DANGER
from .candidate_columns import COVER, RACE, TICKET, VALUE
from .race_columns import CONFIDENCE, GRADED, HONMEI_DANGER, HONMEI_TOP3

#: ◎の自信を出す券種（◎の単勝と複勝）。
_CONFIDENCE_TICKETS = (TicketType.WIN.label, TicketType.PLACE.label)


class RaceTableBuilder:
    """印の付いた1頭ごとの表と、買い目の候補から、1行 = 1レースの表（開催日・重賞か・◎の自信・◎の危うさ）を作る。

    ``graded`` は重賞のレースID（研究「馬券の買い方の検証」の ``RaceFactRepository`` のグレードコード A〜D）。
    ◎の買い目が1つも無いレース（オッズが無いなど）の自信は欠損値で、上位 N レースには入らない。
    """

    def build(self, horses: pd.DataFrame, candidates: pd.DataFrame, graded: Collection[str]) -> pd.DataFrame:
        honmei = horses[horses[MARK] == Mark.HONMEI.value].drop_duplicates(RACE_ID)
        races = pd.DataFrame({
            RACE: honmei[RACE_ID].astype(str).to_numpy(), RACE_DATE: honmei[RACE_DATE].to_numpy(),
            HONMEI_TOP3: honmei[FORM_PROBABILITY].to_numpy(), HONMEI_DANGER: honmei[DANGER].to_numpy(),
        })
        own = candidates[candidates[TICKET].isin(_CONFIDENCE_TICKETS) & ~candidates[COVER]]
        confidence = own.groupby(RACE)[VALUE].max().rename(CONFIDENCE)
        races = races.merge(confidence, left_on=RACE, right_index=True, how="left")
        return races.assign(**{GRADED: races[RACE].isin(set(graded))})
