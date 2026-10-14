"""登録日相当（材料の締めの日）の決め方。"""

from __future__ import annotations

from datetime import date, timedelta

#: 1週間の日数。
_WEEK = 7


class RegistrationCutoff:
    """開催日から、材料の締めの日（登録日相当）を決める（設計書 06 の図3・11 の 6）。

    開催日より前の直近の月曜日。土曜なら 5日前、日曜なら 6日前、月曜（祝日の開催）なら 7日前。
    学習データの過去のレースにも、予測する登録馬の行にも、同じ決め方で付ける（特別登録の作成日ではなく開催日から決める）。
    SQL の式（``sql``。事実表・登録馬の行に列を足す）と Python の関数（``of``。テストと表示）の両方を持ち、同じ判断をする。
    """

    def of(self, race_day: date) -> date:
        """開催日より前の直近の月曜日。"""
        offset = race_day.isoweekday() - 1
        return race_day - timedelta(days=offset if offset else _WEEK)

    def sql(self, day_expr: str) -> str:
        """``day_expr``（開催日の列か式）から、登録日相当を返す SQL の式（日付型）。"""
        day = f"CAST({day_expr} AS DATE)"
        # isodow は BIGINT を返し、日付から引けるのは INTEGER なので直す
        return f"({day} - CAST(CASE WHEN isodow({day}) = 1 THEN {_WEEK} ELSE isodow({day}) - 1 END AS INTEGER))"
