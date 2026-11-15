"""その日の先のレース（2つ前のレースまで）から分かることを、重賞での予想とのずれで数える（段1の確かめの続き）。

    uv run python research/重賞の事例から材料を作る/day_signals.py    # reports/重賞の事例から材料を作る/その日の材料.md に書く

- 騎手のその日の調子: 同じ日（どの競馬場でも）の先のレースで、その騎手が3着以内に来た割合
- その日の時計の速さ × 持ち時計: 同じ競馬場・芝ダの先のレースの勝ち時計が、同じコース・距離の前の年までの勝ち時計の中央値より速いか × 馬の持ち時計の順位
- 父のその日の成績: 同じ日・同じ競馬場・芝ダの先のレースで、同じ父の産駒が3着以内に来た割合
DB は開かない。
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import _OUT, _predictions  # noqa: E402
from day_bias import _table  # noqa: E402

_GAP = 2


def main() -> None:
    rows = _rows()
    lines = ["# その日の先のレースから分かること（重賞・2015〜2022年）", "",
             "ずれ = 実際の3着以内率 ÷ 予想の確率の平均。先のレースは2つ前のレースまで。", ""]
    lines += _table(rows, "騎手のその日の調子", ["騎手の調子"])
    lines += _table(rows, "その日の時計の速さ × 持ち時計", ["時計", "持ち時計"])
    lines += _table(rows, "父のその日の成績", ["父の調子"])
    out = _OUT / "その日の材料.md"
    out.write_bytes("\n".join(lines).encode("utf-8"))
    print("\n".join(lines))


def _rows() -> pd.DataFrame:
    con = duckdb.connect()
    con.register("pred", _predictions())
    facts = (_OUT / "facts.parquet").as_posix()
    frame = con.execute(f"""
    WITH f AS (SELECT * FROM read_parquet('{facts}') WHERE ran),
    g AS (SELECT f.*, p.p FROM f JOIN pred p USING (race_id, horse_id)
          WHERE grade_code IN ('A', 'B', 'C') AND surface <> '障害' AND year BETWEEN 2015 AND 2022),
    jockey AS (
        SELECT g.race_id, g.horse_id, count(e.race_id) AS j_rides, avg(CASE WHEN e.finish <= 3 THEN 1.0 ELSE 0.0 END) AS j_top3
        FROM g JOIN f e ON e.race_date = g.race_date AND e.jockey_code = g.jockey_code
                       AND e.race_no <= g.race_no - {_GAP}
        GROUP BY g.race_id, g.horse_id
    ),
    standard AS (
        SELECT venue, surface, distance_m, year, median(finish_time) AS std_time
        FROM f WHERE finish = 1 GROUP BY venue, surface, distance_m, year
    ),
    day_speed AS (
        SELECT r.race_id, avg(e.finish_time - (SELECT median(s.std_time) FROM standard s
                                                WHERE s.venue = e.venue AND s.surface = e.surface AND s.distance_m = e.distance_m
                                                  AND s.year < e.year)) AS speed
        FROM (SELECT DISTINCT race_id, race_date, venue, surface, race_no FROM g) r
        JOIN f e ON e.race_date = r.race_date AND e.venue = r.venue AND e.surface = r.surface AND e.race_no <= r.race_no - {_GAP} AND e.finish = 1
        GROUP BY r.race_id
    ),
    sire AS (
        SELECT g.race_id, g.horse_id, count(e.race_id) AS s_runs, avg(CASE WHEN e.finish <= 3 THEN 1.0 ELSE 0.0 END) AS s_top3
        FROM g JOIN f e ON e.race_date = g.race_date AND e.venue = g.venue AND e.surface = g.surface AND e.sire = g.sire
                       AND e.race_no <= g.race_no - {_GAP}
        GROUP BY g.race_id, g.horse_id
    )
    SELECT g.race_id, g.horse_id, g.finish, g.place_payout, g.p, g.best_time_unit_rank, g.field_size,
           j.j_rides, j.j_top3, d.speed, s.s_runs, s.s_top3
    FROM g LEFT JOIN jockey j USING (race_id, horse_id) LEFT JOIN day_speed d USING (race_id) LEFT JOIN sire s USING (race_id, horse_id)
    """).df()
    frame = frame.astype({c: float for c in ["finish", "place_payout", "p", "best_time_unit_rank", "field_size", "j_rides", "j_top3",
                                                "speed", "s_runs", "s_top3"]})
    return frame.assign(
        騎手の調子=np.select([frame["j_rides"].fillna(0).lt(3), frame["j_top3"].ge(0.5), frame["j_top3"].le(0.1)],
                          ["先の騎乗3回未満", "半分以上3着以内", "1割以下"], "ふつう"),
        時計=np.select([frame["speed"].isna(), frame["speed"].le(-0.5), frame["speed"].ge(0.5)], ["先のレースなし", "速い日", "遅い日"], "ふつう"),
        持ち時計=np.select([frame["best_time_unit_rank"].le(3), frame["best_time_unit_rank"].isna()], ["上位3頭", "なし"], "4位以下"),
        父の調子=np.select([frame["s_runs"].fillna(0).lt(2), frame["s_top3"].ge(0.5), frame["s_top3"].le(0.1)],
                         ["先の出走2回未満", "半分以上3着以内", "1割以下"], "ふつう"),
        top3=frame["finish"].le(3).astype(float),
        place=np.where(frame["finish"].le(3), frame["place_payout"], 0.0),
    )


if __name__ == "__main__":
    sys.exit(main())
