"""その日の馬場の傾向（同じ日・同じ競馬場・同じ芝ダの、先に終わったレース）と馬の脚質・枠を合わせて、重賞での予想とのずれを数える。

    uv run python research/重賞の事例から材料を作る/day_bias.py    # reports/重賞の事例から材料を作る/その日の馬場.md に書く

- 前残りの度合い: 先のレースの3着以内の馬の、4コーナーの位置（頭数で割った 0〜1。小さいほど前）の平均
- 内の度合い: 先のレースの3着以内の馬のうち、馬番が頭数の半分以下（内）の割合
- 馬の脚質: 直近3走の4コーナーの位置（頭数で割った値）の平均。前（0.33 以下）・中・後ろ（0.6 以上）
先のレースが3つ以上ある重賞だけを数える。DB は開かない。
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import _OUT, _predictions  # noqa: E402

_MIN_EARLIER = 3


def main() -> None:
    rows = _rows()
    lines = ["# その日の馬場の傾向と脚質・枠（重賞・2015〜2022年）", "",
             f"先に終わった同じ競馬場・芝ダのレースが {_MIN_EARLIER} つ以上ある重賞の行 {len(rows):,}。"
             "ずれ = 実際の3着以内率 ÷ 予想の確率の平均。", ""]
    lines += _table(rows, "前残りの度合い × 馬の脚質", ["前残り", "脚質"])
    lines += _table(rows, "内の度合い × 馬の枠", ["内有利", "枠"])
    out = _OUT / "その日の馬場.md"
    out.write_bytes("\n".join(lines).encode("utf-8"))
    print("\n".join(lines))


def _rows() -> pd.DataFrame:
    con = duckdb.connect()
    con.register("pred", _predictions())
    facts = (_OUT / "facts.parquet").as_posix()
    frame = con.execute(f"""
    WITH f AS (SELECT *, corner4 / field_size AS pos4, CASE WHEN horse_no <= field_size / 2.0 THEN 1.0 ELSE 0.0 END AS inner_half
               FROM read_parquet('{facts}') WHERE ran),
    h AS (SELECT f.*, avg(pos4) OVER (PARTITION BY horse_id ORDER BY race_date, race_id ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS style_pos
          FROM f),
    g AS (SELECT h.*, p.p FROM h JOIN pred p USING (race_id, horse_id)
          WHERE grade_code IN ('A', 'B', 'C') AND surface <> '障害' AND year BETWEEN 2015 AND 2022),
    day AS (
        SELECT r.race_id, count(DISTINCT e.race_id) AS earlier, avg(e.pos4) AS front_bias, avg(e.inner_half) AS inner_bias
        FROM (SELECT DISTINCT race_id, race_date, venue, surface, race_no FROM g) r
        JOIN f e ON e.race_date = r.race_date AND e.venue = r.venue AND e.surface = r.surface AND e.race_no < r.race_no AND e.finish <= 3
        GROUP BY r.race_id
    )
    SELECT g.race_id, g.horse_id, g.finish, g.place_payout, g.p, g.style_pos, g.inner_half, d.earlier, d.front_bias, d.inner_bias
    FROM g JOIN day d USING (race_id) WHERE d.earlier >= {_MIN_EARLIER}
    """).df().astype({"finish": float, "place_payout": float, "p": float, "style_pos": float, "front_bias": float, "inner_bias": float})
    front = frame["front_bias"]
    return frame.assign(
        前残り=pd.cut(front, [-1, front.quantile(0.25), front.quantile(0.75), 2], labels=["前が残る日", "ふつう", "差しが届く日"]).astype(str),
        脚質=np.select([frame["style_pos"].le(0.33), frame["style_pos"].ge(0.6)], ["前", "後ろ"], "中"),
        内有利=pd.cut(frame["inner_bias"], [-1, frame["inner_bias"].quantile(0.25), frame["inner_bias"].quantile(0.75), 2],
                    labels=["外が来る日", "ふつう", "内が来る日"]).astype(str),
        枠=np.where(frame["inner_half"].eq(1.0), "内", "外"),
        top3=frame["finish"].le(3).astype(float),
        place=np.where(frame["finish"].le(3), frame["place_payout"], 0.0),
    )


def _table(rows: pd.DataFrame, title: str, keys: list[str]) -> list[str]:
    lines = [f"## {title}", "", "| " + " | ".join(keys) + " | 頭数 | 3着以内率 | 予想の確率 | ずれ | 複勝の回収率 |",
             "|" + "---|" * (len(keys) + 5)]
    for key, group in rows.groupby(keys):
        actual, predicted = group["top3"].mean(), group["p"].mean()
        lines.append("| " + " | ".join(key) + f" | {len(group):,} | {actual:.3f} | {predicted:.3f} | {actual / predicted:.2f} | {group['place'].mean():.0f}% |")
    return lines + [""]


if __name__ == "__main__":
    sys.exit(main())
