"""組の表の列の並び。"""

from __future__ import annotations

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import horse_columns

from ..feature import CATALOGS
from .column_names import BASELINE, COMBO, HIT, ODDS, PAYOUT, RACE_DATE, RACE_ID, TICKET_TYPE


def built_columns(ticket_type: TicketType) -> list[str]:
    """材料づくり（``ComboTableBuilder``）が出す列。ID（レースID・券種・組番・馬番）・オッズ・出発点・材料。"""
    return [RACE_ID, TICKET_TYPE, COMBO, *horse_columns(ticket_type.spec.horse_count), ODDS, BASELINE, *CATALOGS[ticket_type].names]


def id_columns(ticket_type: TicketType) -> list[str]:
    """保存する組の表の ID 列（レースID・開催日・券種・組番・馬番）。"""
    return [RACE_ID, RACE_DATE, TICKET_TYPE, COMBO, *horse_columns(ticket_type.spec.horse_count)]


def stored_columns(ticket_type: TicketType) -> list[str]:
    """保存する組の表の列。ID・評価用（オッズ・払戻）・目的変数・出発点・材料。"""
    return [*id_columns(ticket_type), ODDS, PAYOUT, HIT, BASELINE, *CATALOGS[ticket_type].names]
