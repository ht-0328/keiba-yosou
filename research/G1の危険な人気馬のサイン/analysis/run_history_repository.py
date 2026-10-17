"""元DB の事実表から、サインを数えるのに使う中央の全出走を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, stakes

#: 読む列（事実表の列名。stakes_no だけ重賞の対応表から）。
RUN_COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "horse_id", "venue_code", "track_code", "surface", "distance_m", "grade_code", "class_order",
    "field_size", "horse_no", "sex", "age", "popularity", "win_odds", "finish", "mixed_sex", "prev_distance_m",
    "prev_finish", "prev_popularity", "win_payout", "place_payout", "stakes_no",
)
#: 値の無いことがある数の列。
_NULLABLE_NUMBERS: tuple[str, ...] = ("finish", "popularity", "win_odds", "prev_distance_m", "prev_finish", "prev_popularity")


class RunHistoryRepository:
    """事実表（``共通.facts``）の出走した行に、重賞の特別競走番号を付けて読む。1行 = 1頭の出走。

    取消・除外（``ran`` が偽）は数えない。着順の付かない出走（競走中止など）は ``finish`` が NULL のまま残す。
    """

    def read(self, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        facts.ensure_facts(con)
        stakes_map = stakes.ensure_stakes_map(con)
        columns = ", ".join(f"f.{column}" for column in RUN_COLUMNS if column != "stakes_no")
        frame = con.execute(f"""
            SELECT {columns}, m.stakes_no
            FROM facts f LEFT JOIN {stakes_map} m ON m.race_id = f.race_id
            WHERE f.ran
        """).df()
        frame["race_date"] = pd.to_datetime(frame["race_date"])
        # 値の無いことがある整数の列は、比べた結果が欠けないように小数（無ければ NaN）にする
        return frame.astype({column: "float64" for column in _NULLABLE_NUMBERS})
