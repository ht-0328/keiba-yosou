"""券種ごとの形の候補（設計書「重賞に特化して3着以内と1着を予想」16 の 6.3）。"""

from __future__ import annotations

from itertools import product

from .ticket_shape import BRACKET, EXACTA, PLACE, QUINELLA, TRIFECTA, TRIO, WIDE, WIN, TicketShape


def _grid(ticket: str, forms: list[tuple[str, str]], caps, lines, floors=(None,)) -> list[TicketShape]:
    return [TicketShape(ticket, form, partners, cap, floor, line)
            for (form, partners), cap, floor, line in product(forms, caps, floors, lines)]


def _place() -> list[TicketShape]:
    return [TicketShape(PLACE, form, line=line, star=star)
            for form, star, line in product(("◎", "◎・○", "◎・○・▲"), (False, True), (None, 1.0, 1.1))]


_TRIO_POOLS = ("印", "印と上位の無印3頭", "無印に流す")

#: 形の候補。単勝は ◎ の1点だけ（利用者の決定）。
SHAPES: tuple[TicketShape, ...] = (
    TicketShape(WIN, "◎"),
    *_place(),
    *_grid(BRACKET, [("◎の枠−相手の枠", partners) for partners in ("○▲", "○▲△", "○▲△☆")], (None, 50.0, 300.0), (None,)),
    *_grid(QUINELLA, [("◎−相手", partners) for partners in ("○▲", "○▲☆", "○▲△☆", "印")] + [("◎○▲の3頭の組", "")],
           (None, 30.0, 100.0), (None, 1.0)),
    *_grid(WIDE, [("◎−相手", partners) for partners in ("○▲", "☆注", "印")] + [("◎○−相手", partners) for partners in ("○▲", "☆注", "印")],
           (None,), (None, 1.0), floors=(None, 2.0, 4.0)),
    *_grid(EXACTA, [(form, partners) for form in ("◎→相手", "相手→◎", "◎と相手の両方向") for partners in ("○▲☆", "○▲△", "印")],
           (None, 30.0, 100.0), (None, 1.0)),
    *_grid(TRIO, [(form, partners) for form in ("◎軸−相手−相手", "◎○の2頭軸−相手") for partners in _TRIO_POOLS]
           + [("◎○▲△の4頭の組", ""), ("◎軸−印−無印に流す", "")], (None, 300.0, 1000.0), (None, 1.0, 1.2)),
    *_grid(TRIFECTA, [(form, partners) for form in ("◎→相手→相手", "相手→◎→相手", "相手→相手→◎") for partners in _TRIO_POOLS]
           + [("○▲→消以外→◎", ""), ("◎→○▲→無印に流す", "")], (None, 1000.0, 3000.0), (None, 1.0, 1.2)),
)

#: 今の印の買い目（設計書「買うレースと買い目を決める」08 の 2 の形）。選ばれなくても比べる行として出す。
#: 3連複・3連単の相手（○▲☆ と ○▲△☆ の2段）は上の候補に無い形なので、相手の範囲を「○▲△☆」の形で近づけて数える。
CURRENT_RULE_SHAPES: tuple[TicketShape, ...] = (
    TicketShape(WIDE, "◎−相手", "☆注"),
    TicketShape(QUINELLA, "◎−相手", "○▲☆"),
    TicketShape(EXACTA, "◎→相手", "○▲☆"),
)
