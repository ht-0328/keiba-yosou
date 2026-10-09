"""重賞の出走の行を、分析に要る列だけ読み込む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys, stakes

#: 前走が平場（競走名なし）のときの、前走レース名の表示。
NO_PREV_NAME = "（平場・条件戦）"
#: 前走が DB に無い（中央の確定成績に前走が無い）ときの表示。地方・海外帰りを含む。
NO_PREV = "（前走なし・地方・海外）"


def load_runners(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """重賞（G1・G2・G3）の出走の行。1行 = 1頭の出走。

    事実表の列に、レースの同定（``stakes_no``・``stakes_name``・``grade``）と、
    前走のレース名・クラス（馬ごとの1つ前の中央の出走から引く）を足したもの。
    """
    facts.ensure_facts(con)
    stakes.ensure_stakes_map(con)
    return con.execute(f"""
    WITH runs AS (
        SELECT race_id, horse_id, race_date, race_name, class_name,
               lag(race_name) OVER (PARTITION BY horse_id ORDER BY race_date) AS prev_race_name,
               lag(class_name) OVER (PARTITION BY horse_id ORDER BY race_date) AS prev_class_name
        FROM {facts.FACTS_TABLE} WHERE ran
    )
    SELECT f.race_id, f.race_date, f.year, f.venue, f.course, f.distance_m, f.condition,
           f.grade_code, f.field_size, f.frame_no, f.horse_no, f.horse_name,
           f.sex, f.age, f.affiliation, f.popularity, f.win_odds, f.finish,
           f.style, f.style_before, f.interval_days, f.distance_change,
           f.same_race_places_before, f.win_payout, f.place_payout,
           m.stakes_no, m.stakes_name, m.grade,
           r.prev_race_name, r.prev_class_name
    FROM {facts.FACTS_TABLE} f
    JOIN {keys.q(stakes.STAKES_MAP_TABLE)} m USING (race_id)
    JOIN runs r ON r.race_id = f.race_id AND r.horse_id = f.horse_id
    WHERE f.ran
    ORDER BY f.race_date, f.race_id, f.horse_no
    """).df()


def latest_names(runners: pd.DataFrame) -> pd.DataFrame:
    """特別競走番号ごとの、いちばん新しい開催の情報（名前・グレード・場・コース・距離・開催数・期間）。"""
    rows = []
    for no, group in runners.groupby("stakes_no"):
        last = group.loc[group["race_date"].idxmax()]
        rows.append({
            "stakes_no": no, "stakes_name": last["stakes_name"], "grade": last["grade"],
            "venue": last["venue"], "course": last["course"], "distance_m": last["distance_m"],
            "editions": group["race_id"].nunique(),
            "first_year": int(group["year"].min()), "last_year": int(group["year"].max()),
        })
    order = {"A": 0, "B": 1, "C": 2}
    rows.sort(key=lambda r: (order.get(r["grade"], 9), r["stakes_no"]))
    return pd.DataFrame(rows)
