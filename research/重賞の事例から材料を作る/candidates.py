"""新しい材料の候補（10個）を、重賞（2015〜2026年）の出走ごとに作る（段2）。

    uv run python research/重賞の事例から材料を作る/candidates.py    # reports/重賞の事例から材料を作る/候補.parquet に書く

どれも、そのレースより前に分かることだけから作る。騎手・調教師・父の成績は、その年より前の年だけで数える。
「人気から見た」成績は、2011〜2014年の人気ごとの3着以内率を物差しにした超過（実際の3着以内の数 − 物差しの数）÷ 出走数。
DB は開かない（facts.parquet を読む）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

_OUT = Path(__file__).resolve().parents[2] / "reports" / "重賞の事例から材料を作る"
_EAST = "('札幌', '函館', '福島', '新潟', '東京', '中山')"

#: 候補の列の名前（作る順）。
CANDIDATES: tuple[str, ...] = (
    "父の今日の馬場状態での3着以内率", "父の今日の馬場状態での出走数",
    "遠征",
    "騎手の重賞での超過3着以内率", "騎手の重賞の騎乗数",
    "調教師の重賞での超過3着以内率", "調教師の重賞の出走数",
    "調教師の休み明けでの超過3着以内率",
    "前走の相手のその後の勝ち上がりの割合", "前走の相手のその後のOP以上での3着以内の数",
    "重賞で上がり最速の回数",
    "今回の距離の前後100mでの最高着順", "今回の距離の前後100mでの出走数",
    "前走が重い馬場で負けて今回は良",
    "前走が牝馬限定で今回は混合",
)


def main() -> None:
    con = duckdb.connect()
    facts = (_OUT / "facts.parquet").as_posix()
    frame = con.execute(_sql(facts)).df()
    out = _OUT / "候補.parquet"
    frame.to_parquet(out)
    print(out, len(frame))
    print(frame[list(CANDIDATES)].describe().T.to_string())


def _sql(facts: str) -> str:
    return f"""
    WITH f AS (
        SELECT *, CASE WHEN finish <= 3 THEN 1.0 ELSE 0.0 END AS top3, CASE WHEN condition_order >= 3 THEN '重い' ELSE '軽い' END AS going
        FROM read_parquet('{facts}') WHERE surface <> '障害'
    ),
    yardstick AS (  -- 2011〜2014年の、人気ごとの3着以内率
        SELECT least(popularity, 16) AS pop, avg(top3) AS rate FROM f WHERE ran AND year <= 2014 GROUP BY 1
    ),
    r AS (SELECT f.*, y.rate AS expected FROM f LEFT JOIN yardstick y ON y.pop = least(f.popularity, 16) WHERE ran),
    h AS (
        SELECT r.*,
               lag(race_id) OVER w AS prev_race_id, lag(race_date) OVER w AS prev_date,
               lag(condition_order) OVER w AS prev_cond, lag(mixed_sex) OVER w AS prev_mixed
        FROM r WINDOW w AS (PARTITION BY horse_id ORDER BY race_date, race_id)
    ),
    g AS (SELECT * FROM h WHERE grade_code IN ('A', 'B', 'C') AND year >= 2015),
    sire_year AS (SELECT sire, surface, going, year, count(*) AS n, sum(top3) AS t FROM r GROUP BY ALL),
    jockey_year AS (SELECT jockey_code, year, count(*) AS n, sum(top3 - expected) AS x FROM r WHERE grade_code IN ('A', 'B', 'C') GROUP BY ALL),
    trainer_year AS (SELECT trainer_code, year, count(*) AS n, sum(top3 - expected) AS x FROM r WHERE grade_code IN ('A', 'B', 'C') GROUP BY ALL),
    rest_year AS (SELECT trainer_code, year, count(*) AS n, sum(top3 - expected) AS x FROM r WHERE interval_days >= 70 GROUP BY ALL),
    sire_c AS (
        SELECT g.race_id, g.horse_id, sum(s.t) / nullif(sum(s.n), 0) AS rate, coalesce(sum(s.n), 0) AS n
        FROM g LEFT JOIN sire_year s ON s.sire = g.sire AND s.surface = g.surface AND s.going = g.going AND s.year < g.year
        GROUP BY g.race_id, g.horse_id
    ),
    jockey_c AS (
        SELECT g.race_id, g.horse_id, sum(j.x) / nullif(sum(j.n), 0) AS x, coalesce(sum(j.n), 0) AS n
        FROM g LEFT JOIN jockey_year j ON j.jockey_code = g.jockey_code AND j.year < g.year GROUP BY g.race_id, g.horse_id
    ),
    trainer_c AS (
        SELECT g.race_id, g.horse_id, sum(t.x) / nullif(sum(t.n), 0) AS x, coalesce(sum(t.n), 0) AS n
        FROM g LEFT JOIN trainer_year t ON t.trainer_code = g.trainer_code AND t.year < g.year GROUP BY g.race_id, g.horse_id
    ),
    rest_c AS (
        SELECT g.race_id, g.horse_id, sum(t.x) / nullif(sum(t.n), 0) AS x
        FROM g LEFT JOIN rest_year t ON t.trainer_code = g.trainer_code AND t.year < g.year GROUP BY g.race_id, g.horse_id
    ),
    opponents AS (  -- 前走の相手の、前走のあと今回より前の出走
        SELECT g.race_id, g.horse_id, o.horse_id AS opp,
               max(CASE WHEN later.finish = 1 THEN 1.0 ELSE 0.0 END) AS won_later,
               sum(CASE WHEN later.class_order <= 3 AND later.finish <= 3 THEN 1 ELSE 0 END) AS open_top3
        FROM g JOIN r o ON o.race_id = g.prev_race_id AND o.horse_id <> g.horse_id
        JOIN r later ON later.horse_id = o.horse_id AND later.race_date > g.prev_date AND later.race_date < g.race_date
        GROUP BY g.race_id, g.horse_id, o.horse_id
    ),
    opp_c AS (SELECT race_id, horse_id, avg(won_later) AS won_share, sum(open_top3) AS open_top3 FROM opponents GROUP BY ALL),
    career AS (
        SELECT g.race_id, g.horse_id,
               count(*) FILTER (WHERE p.grade_code IN ('A', 'B', 'C') AND p.last3f_rank = 1) AS fastest,
               min(p.finish) FILTER (WHERE p.surface = g.surface AND abs(p.distance_m - g.distance_m) <= 100) AS best_near,
               count(*) FILTER (WHERE p.surface = g.surface AND abs(p.distance_m - g.distance_m) <= 100) AS runs_near
        FROM g JOIN r p ON p.horse_id = g.horse_id AND p.race_date < g.race_date
        GROUP BY g.race_id, g.horse_id
    )
    SELECT g.race_id, g.horse_id, g.year,
           s.rate AS "父の今日の馬場状態での3着以内率", CAST(s.n AS DOUBLE) AS "父の今日の馬場状態での出走数",
           CASE WHEN g.affiliation = '美浦' AND g.venue NOT IN {_EAST} THEN 1.0
                WHEN g.affiliation = '栗東' AND g.venue IN {_EAST} THEN 1.0 ELSE 0.0 END AS "遠征",
           j.x AS "騎手の重賞での超過3着以内率", CAST(j.n AS DOUBLE) AS "騎手の重賞の騎乗数",
           t.x AS "調教師の重賞での超過3着以内率", CAST(t.n AS DOUBLE) AS "調教師の重賞の出走数",
           CASE WHEN g.interval_days >= 70 THEN rc.x END AS "調教師の休み明けでの超過3着以内率",
           o.won_share AS "前走の相手のその後の勝ち上がりの割合", CAST(coalesce(o.open_top3, 0) AS DOUBLE) AS "前走の相手のその後のOP以上での3着以内の数",
           CAST(coalesce(c.fastest, 0) AS DOUBLE) AS "重賞で上がり最速の回数",
           CAST(c.best_near AS DOUBLE) AS "今回の距離の前後100mでの最高着順", CAST(coalesce(c.runs_near, 0) AS DOUBLE) AS "今回の距離の前後100mでの出走数",
           CASE WHEN g.prev_cond >= 3 AND g.prev_finish >= 4 AND g.condition_order = 1 THEN 1.0 ELSE 0.0 END AS "前走が重い馬場で負けて今回は良",
           CASE WHEN g.prev_mixed = FALSE AND g.mixed_sex THEN 1.0 ELSE 0.0 END AS "前走が牝馬限定で今回は混合"
    FROM g
    LEFT JOIN sire_c s USING (race_id, horse_id) LEFT JOIN jockey_c j USING (race_id, horse_id)
    LEFT JOIN trainer_c t USING (race_id, horse_id) LEFT JOIN rest_c rc USING (race_id, horse_id)
    LEFT JOIN opp_c o USING (race_id, horse_id) LEFT JOIN career c USING (race_id, horse_id)
    """


if __name__ == "__main__":
    sys.exit(main())
