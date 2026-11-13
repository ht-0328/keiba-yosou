"""その日の WIN5 の対象レースと発走時刻を、元DB から読む。"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from 共通 import card, db

from yosou.form_aptitude_win5_tickets.repository import Win5DayRepository

from 発走前の通知.win5_slot import Win5Slot

#: レース一覧の列の位置。
_RID = card.CARD_LIST_HEADERS.index("rid")
_POST = card.CARD_LIST_HEADERS.index("発走")


class Win5Schedule:
    """対象レースは予想のパッケージの ``Win5DayRepository``（元DB の ``wf``。当日の分は速報の WIN5（0B51）で入る）、発走時刻は道具「今週の出馬表」の
    レース一覧から読む。DB は読むたびに開いてすぐ閉じる（取り込みの邪魔をしない）。発走時刻の変更を拾えるように、呼ぶ側は待つ間にも読み直す。"""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path

    def read(self, day: str) -> Win5Slot | None:
        """その日の WIN5。無い日・中止・対象レースがそろっていない・発走時刻が1つも分からない日は None。"""
        with db.open_db(self._db_path) as con:
            try:
                win5 = Win5DayRepository(con).read(date.fromisoformat(day))
            except LookupError:
                return None
            listed = card.list_cards(con, date_from=day, date_to=day, limit=card.MAX_LIST_LIMIT)
        posts = {str(row[_RID]): row[_POST] for row in listed.rows if row[_POST]}
        times = tuple(datetime.fromisoformat(f"{day}T{posts[rid]}:00") if rid in posts else None for rid in win5.race_ids)
        if all(post is None for post in times):
            return None
        return Win5Slot(day, win5.race_ids, times)
