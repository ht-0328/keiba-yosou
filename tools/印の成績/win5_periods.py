"""WIN5 の確かめの期間（探索期間・確認期間）。"""

from __future__ import annotations

#: 期間の名前。
EXPLORE = "探索（2019〜2024年）"
CONFIRM = "確認（2025年〜）"
#: 期間の始まり（開催日の ``YYYY-MM-DD``）。探索期間は確認期間の始まりの前日まで。
EXPLORE_START = "2019-01-01"
CONFIRM_START = "2025-01-01"


class Win5Periods:
    """開催日を、探索期間（2019〜2024年。買い方を選ぶ）か確認期間（2025年から。選んだ買い方を1回だけ確かめる）に分ける
    （設計書「近走と適性からWIN5の買い目を決める」16 の 1.）。2019年より前は確かめない（前日と当日の区切りごとの予測がそろわない）。"""

    def label_of(self, race_date: str) -> str | None:
        """開催日（``YYYY-MM-DD``）の期間の名前。2019年より前なら None。"""
        if race_date < EXPLORE_START:
            return None
        return EXPLORE if race_date < CONFIRM_START else CONFIRM
