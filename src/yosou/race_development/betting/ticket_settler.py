"""買い目を払戻と照らし合わせて精算する。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import void_column

from .column_names import COMBO, HIT, PAYOUT, RACE_ID, STAKE, STAKE_YEN, TICKET_TYPE, YEN

_VOID = "void"


class TicketSettler:
    """買い目の表を、払戻の明細と照らし合わせて、``payout``（戻る円）と ``hit``（当たったか）を付ける（設計書 06 の図5）。

    - 払戻の表に、同じレース・同じ券種・同じ組番の行があれば、その払戻金（100円あたり）× 賭け金 ÷ 100。
      複勝・ワイドの複数行や同着の行は、組番ごとに別の行なので、合った行の払戻金になる。
    - 払戻の表に無ければ 0円。
    - **その券種が不成立・特払のレースは、その券種を買わない（見送り。表から落とす）。** 研究「馬券の買い方の検証」と同じ扱い。
    - 払戻のデータが無いレース（払戻の明細にもフラグにも無い。払戻の確定前）も、精算できないので落とす。
    取消・除外の馬を含む買い目は、買い目を作る段で作らない（ここでは見ない）。
    """

    def settle(self, tickets: pd.DataFrame, payouts: Mapping[TicketType, pd.DataFrame], flags: pd.DataFrame) -> pd.DataFrame:
        """``tickets`` は買い目の表（列 ``race_id``・``ticket_type``（``TicketType.key``）・``combo``・``stake``・``rule``。ほかの列はそのまま残す）。
        ``payouts`` は券種 → ``PayoutRepository.read`` の表（列 ``race_id``・``combo``・``yen``）、
        ``flags`` は ``PayoutFlagRepository.read`` の表（列 ``race_id`` と券種ごとの ``<key>_void``）。

        戻り値は、見送った行を落とし、列 ``payout``（円。int）・``hit``（bool）を足した表。行の並びは ``tickets`` の順。
        """
        yen = self._yen(payouts)
        known = set(flags[RACE_ID].astype(str)) | set(yen[RACE_ID])
        kept = tickets[tickets[RACE_ID].astype(str).isin(known)]
        kept = kept.merge(self._voids(flags), on=[RACE_ID, TICKET_TYPE], how="left")
        kept = kept[~kept[_VOID].eq(True)].drop(columns=_VOID)
        settled = kept.merge(yen, on=[RACE_ID, TICKET_TYPE, COMBO], how="left")
        settled[PAYOUT] = (settled[YEN].fillna(0) * settled[STAKE] // STAKE_YEN).astype("int64")
        settled[HIT] = settled[PAYOUT] > 0
        return settled.drop(columns=YEN).reset_index(drop=True)

    def _yen(self, payouts: Mapping[TicketType, pd.DataFrame]) -> pd.DataFrame:
        """券種ごとの払戻の明細を1つの表（列 ``race_id``・``ticket_type``・``combo``・``yen``）にする。同じ組番の行は足す。"""
        frames = [table[[RACE_ID, COMBO, YEN]].assign(**{TICKET_TYPE: ticket_type.key}) for ticket_type, table in payouts.items()]
        empty = pd.DataFrame({RACE_ID: pd.Series(dtype=str), COMBO: pd.Series(dtype=str), YEN: pd.Series(dtype="int64"),
                              TICKET_TYPE: pd.Series(dtype=str)})
        long = pd.concat([empty, *frames], ignore_index=True)
        long[RACE_ID] = long[RACE_ID].astype(str)
        return long.groupby([RACE_ID, TICKET_TYPE, COMBO], as_index=False)[YEN].sum()

    def _voids(self, flags: pd.DataFrame) -> pd.DataFrame:
        """フラグの表を、1行 = 1レース × 1券種 の「成立しなかったか」の表（列 ``race_id``・``ticket_type``・``void``）にする。"""
        frames = [
            pd.DataFrame({RACE_ID: flags[RACE_ID].astype(str), TICKET_TYPE: ticket_type.key, _VOID: flags[void_column(ticket_type)].astype(bool)})
            for ticket_type in TicketType if void_column(ticket_type) in flags.columns
        ]
        empty = pd.DataFrame({RACE_ID: pd.Series(dtype=str), TICKET_TYPE: pd.Series(dtype=str), _VOID: pd.Series(dtype=bool)})
        return pd.concat([empty, *frames], ignore_index=True)
