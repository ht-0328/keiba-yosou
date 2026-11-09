"""確かめる買い目の形の一覧と、合計の行の組み方。"""

from __future__ import annotations

from yosou.shared.betting import TicketType

from .formation import BOX, FORM, Formation
from .payout_floor import PayoutFloor
from .rank_span import RankSpan
from .row_spec import RowSpec


def _span(low: int, high: int | None = None) -> tuple[RankSpan, ...]:
    return (RankSpan(low, high),)


#: 集計金額（サイトの表に載っていた、券種ごとの的中の払戻の下限）。
WIN_FLOORS = (PayoutFloor(yen=500),)
EXACTA_FLOORS = (PayoutFloor(per_point=500), PayoutFloor(yen=5_000))
TRIFECTA_FLOORS = (PayoutFloor(yen=10_000), PayoutFloor(yen=50_000))
WIDE_FLOORS = (PayoutFloor(yen=2_000),)
QUINELLA_FLOORS = (PayoutFloor(per_point=500), PayoutFloor(yen=5_000))
TRIO_FLOORS = (PayoutFloor(yen=5_000), PayoutFloor(yen=10_000))
BOX_FLOORS = (PayoutFloor(yen=10_000),)
BOX_TRIFECTA_FLOORS = (PayoutFloor(yen=50_000),)
#: 上位5頭BOX の順位。
_TOP5 = _span(1, 5)


class FormationCatalog:
    """予想サイトの「指数の順位で組む買い目」の形（「指数 n位」をレースの中のモデルの順位と読む）と、合計の行の組み方。

    形は券種ごとに別々に数え、同じ券種の形を合わせた合計、上位5頭BOX の合計、全部の合計も出す。
    """

    FORMATIONS: tuple[Formation, ...] = (
        Formation("単勝 1位", TicketType.WIN, (_span(1, 1),), WIN_FLOORS),
        Formation("馬単 1位→2〜8位", TicketType.EXACTA, (_span(1, 1), _span(2, 8)), EXACTA_FLOORS),
        Formation("馬単 2位→1位・3位", TicketType.EXACTA, (_span(2, 2), (RankSpan(1, 1), RankSpan(3, 3))), EXACTA_FLOORS),
        Formation("3連単 1位→2〜8位→2〜8位の残り", TicketType.TRIFECTA, (_span(1, 1), _span(2, 8), _span(2, 8)), TRIFECTA_FLOORS),
        Formation("3連単 1位→2・3位→9位以下", TicketType.TRIFECTA, (_span(1, 1), _span(2, 3), _span(9)), TRIFECTA_FLOORS),
        Formation("3連単 1位→9位以下→2・3位", TicketType.TRIFECTA, (_span(1, 1), _span(9), _span(2, 3)), TRIFECTA_FLOORS),
        Formation("3連単 2位→1位→3〜8位", TicketType.TRIFECTA, (_span(2, 2), _span(1, 1), _span(3, 8)), TRIFECTA_FLOORS),
        Formation("3連単 2位→3位→1位・4〜8位", TicketType.TRIFECTA, (_span(2, 2), _span(3, 3), (RankSpan(1, 1), RankSpan(4, 8))), TRIFECTA_FLOORS),
        Formation("3連単 3位→1・2位→1・2位の残り・4〜8位", TicketType.TRIFECTA,
                  (_span(3, 3), _span(1, 2), (RankSpan(1, 2), RankSpan(4, 8))), TRIFECTA_FLOORS),
        Formation("3連単 4位→1位→2・3・5・6位", TicketType.TRIFECTA, (_span(4, 4), _span(1, 1), (RankSpan(2, 3), RankSpan(5, 6))), TRIFECTA_FLOORS),
        Formation("3連単 5位→1位→2〜4位・6位", TicketType.TRIFECTA, (_span(5, 5), _span(1, 1), (RankSpan(2, 4), RankSpan(6, 6))), TRIFECTA_FLOORS),
        Formation("ワイド 1位−2〜5位", TicketType.WIDE, (_span(1, 1), _span(2, 5)), WIDE_FLOORS),
        Formation("馬連 1位−2〜8位", TicketType.QUINELLA, (_span(1, 1), _span(2, 8)), QUINELLA_FLOORS),
        Formation("馬連 2位−3位", TicketType.QUINELLA, (_span(2, 2), _span(3, 3)), QUINELLA_FLOORS),
        Formation("3連複 1位−2〜4位−3〜8位の残り", TicketType.TRIO, (_span(1, 1), _span(2, 4), _span(3, 8)), TRIO_FLOORS),
        Formation("3連複 1位−2・3位−9位以下", TicketType.TRIO, (_span(1, 1), _span(2, 3), _span(9)), TRIO_FLOORS),
        Formation("3連複 1位−5〜7位−6〜8位の残り", TicketType.TRIO, (_span(1, 1), _span(5, 7), _span(6, 8)), TRIO_FLOORS),
        Formation("3連複 2位−3位−4〜8位", TicketType.TRIO, (_span(2, 2), _span(3, 3), _span(4, 8)), TRIO_FLOORS),
        Formation("上位5頭BOX 馬連", TicketType.QUINELLA, (_TOP5, _TOP5), BOX_FLOORS, group=BOX),
        Formation("上位5頭BOX 馬単", TicketType.EXACTA, (_TOP5, _TOP5), BOX_FLOORS, group=BOX),
        Formation("上位5頭BOX 3連複", TicketType.TRIO, (_TOP5, _TOP5, _TOP5), BOX_FLOORS, group=BOX),
        Formation("上位5頭BOX 3連単", TicketType.TRIFECTA, (_TOP5, _TOP5, _TOP5), BOX_TRIFECTA_FLOORS, group=BOX),
    )

    @classmethod
    def all(cls) -> tuple[Formation, ...]:
        return cls.FORMATIONS

    @classmethod
    def forms(cls) -> tuple[Formation, ...]:
        """サイトの個々の形（BOX を除く）。"""
        return tuple(formation for formation in cls.FORMATIONS if formation.group == FORM)

    @classmethod
    def boxes(cls) -> tuple[Formation, ...]:
        return tuple(formation for formation in cls.FORMATIONS if formation.group == BOX)

    @classmethod
    def tickets(cls) -> tuple[TicketType, ...]:
        """使う券種（出てくる順）。"""
        found: dict[TicketType, None] = {}
        for formation in cls.FORMATIONS:
            found.setdefault(formation.ticket, None)
        return tuple(found)

    @classmethod
    def by_label(cls) -> dict[str, Formation]:
        return {formation.label: formation for formation in cls.FORMATIONS}

    @classmethod
    def row_specs(cls) -> list[RowSpec]:
        """表の行（形ごと・券種ごとの合計・BOX の合計・全部の合計）の順。"""
        rows = [RowSpec(formation.label, formation.ticket.label, (formation.label,), formation.floors) for formation in cls.forms()]
        for ticket in cls.tickets():
            members = tuple(formation.label for formation in cls.forms() if formation.ticket is ticket)
            if len(members) > 1:
                rows.append(RowSpec(f"{ticket.label} の形の合計", ticket.label, members))
        rows += [RowSpec(formation.label, formation.ticket.label, (formation.label,), formation.floors) for formation in cls.boxes()]
        rows.append(RowSpec("上位5頭BOX の合計", "4券種", tuple(formation.label for formation in cls.boxes())))
        rows.append(RowSpec("全部の合計（BOX を除く）", "6券種", tuple(formation.label for formation in cls.forms())))
        rows.append(RowSpec("全部の合計（BOX を含む）", "6券種", tuple(formation.label for formation in cls.FORMATIONS)))
        return rows
