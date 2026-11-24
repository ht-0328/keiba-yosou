"""成績を数える買い目の表（1行 = 1点）の列の名前と、数え方の定数（定数だけ）。"""

from __future__ import annotations

#: 買い目の表の列（予想のパッケージの年ごとの予測 ``PredictionStore`` の列と同じ名前）。``payout`` は 100円あたりの払戻（外れは 0）、
#: ``hit`` は当たったら 1。
RACE_ID, RACE_DATE, TICKET_TYPE, COMBO = "race_id", "race_date", "ticket_type", "combo"
ODDS, PAYOUT, HIT, PROBABILITY = "odds", "payout", "hit", "probability"
PICK_COLUMNS: tuple[str, ...] = (RACE_ID, RACE_DATE, TICKET_TYPE, COMBO, ODDS, PAYOUT, HIT, PROBABILITY)
#: 全部の券種を合わせた行の名前。
TOTAL = "合計"
#: 探す期間の最後の年（この年までの成績を見て買い方を決めた。次の年からが確かめる期間）。
SEARCH_LAST_YEAR = 2022
#: 線の感度の表で動かす、期待値の線と、1レース・1券種の上限の点数（None は上限なし）。
SENSITIVITY_VALUE_LINES: tuple[float, ...] = (1.00, 1.05, 1.10, 1.20)
SENSITIVITY_MAX_POINTS: tuple[int | None, ...] = (None, 3, 5, 10)
