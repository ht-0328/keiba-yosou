"""研究「AIとロジックの予想」: AI（全頭の予想）が材料にしていない、レースの前に分かることを1レースごとに作る。

    uv run python research/AIとロジックの予想/analysis/logic_features.py --start 2022-09-03 --end 2026-09-23

- その日の馬場の偏り（``bias_z``）: 同じ日・同じ競馬場・同じ芝ダの、2つ前のレースまで（通知の時点で通過順が届いているレース）の3着以内の馬の
  4コーナーの位置（前 0・中 1・後ろ 2。頭数の3分の1ずつ）の平均を、その競馬場 × 芝ダの前の年までの平均と比べた z（道具「発走前の通知」の
  ``TrackTendency`` と同じ考え方）。マイナスが前寄り。数えたレースが無ければ欠損値。``bias_races`` は数えたレースの数。
- 馬ごとの推定脚質（``style_before``。今回より前の直近3走の脚質の中央）と、レースの逃げ・先行の馬の数（``front_runners``）。
出るもの（Git 対象外）: ``reports/AIとロジックの予想/logic_horses_<start>_<end>.pkl``（1行 = 1頭）。
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "tools"))

from 共通 import db, facts  # noqa: E402

OUT = _ROOT / "reports" / "AIとロジックの予想"
#: 通過順が届いていると見なす、今のレースとの番号の差（通知は発走10分前で、直前のレースの通過順はまだのことが多い）。
LAG = 2
_FRONT_STYLES = ("逃げ", "先行")


def read(start: str, end: str) -> pd.DataFrame:
    with db.open_db() as con:
        table = facts.ensure_facts(con)
        return con.execute(f"""
            SELECT race_id, race_date, venue_code, surface, race_no, horse_id, horse_no, finish, corner4, field_size, style_before
            FROM {table}
            WHERE race_date >= '{int(start[:4]) - 3}-01-01' AND race_date < '{end}' AND surface IN ('芝', 'ダート')
        """).df()


def positions(runs: pd.DataFrame) -> pd.Series:
    """4コーナーの位置の点数（前 0・中 1・後ろ 2）。"""
    corner = pd.to_numeric(runs["corner4"], errors="coerce").astype(float)
    share = ((corner - 1) / pd.to_numeric(runs["field_size"], errors="coerce").astype(float).clip(lower=1)).to_numpy()
    return pd.Series(np.select([share < 1 / 3, share < 2 / 3], [0, 1], 2), index=runs.index).where(corner.notna())


def day_bias(runs: pd.DataFrame, start: str) -> pd.DataFrame:
    """レースごとの bias_z・bias_races（1行 = 1レース。``start`` 以降のレースだけ）。"""
    top3 = runs[runs["finish"].between(1, 3)].assign(score=lambda frame: positions(frame)).dropna(subset=["score"])
    top3 = top3.assign(year=top3["race_date"].astype(str).str[:4].astype(int))
    usual = {}
    for (venue, surface), group in top3.groupby(["venue_code", "surface"]):
        for year in sorted(group["year"].unique()):
            past = group[(group["year"] < year) & (group["year"] >= year - 3)]["score"]
            if len(past) > 50:
                usual[(venue, surface, year)] = (past.mean(), past.std(ddof=0))
    races = runs.drop_duplicates("race_id")[["race_id", "race_date", "venue_code", "surface", "race_no"]]
    races = races[races["race_date"].astype(str) >= start].assign(race_no=lambda frame: frame["race_no"].astype(int))
    scores = top3.assign(race_no=top3["race_no"].astype(int)).groupby(["race_date", "venue_code", "surface", "race_no"])["score"].agg(["sum", "count"])
    rows = []
    for (day, venue, surface), group in races.groupby(["race_date", "venue_code", "surface"]):
        done = scores.loc[(day, venue, surface)] if (day, venue, surface) in scores.index.droplevel(3) else None
        key = (venue, surface, int(str(day)[:4]))
        for race in group.itertuples():
            before = done[done.index <= race.race_no - LAG] if done is not None else None
            if before is None or before.empty or key not in usual or usual[key][1] <= 0:
                rows.append((race.race_id, np.nan, 0 if before is None else len(before)))
                continue
            mean, spread = usual[key]
            count = before["count"].sum()
            rows.append((race.race_id, (before["sum"].sum() / count - mean) / (spread / math.sqrt(count)), len(before)))
    return pd.DataFrame(rows, columns=["race_id", "bias_z", "bias_races"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()
    runs = read(args.start, args.end)
    bias = day_bias(runs, args.start)
    horses = runs[runs["race_date"].astype(str) >= args.start][["race_id", "horse_id", "horse_no", "style_before"]]
    front = horses.assign(front=horses["style_before"].isin(_FRONT_STYLES)).groupby("race_id")["front"].sum().rename("front_runners")
    out = horses.merge(bias, on="race_id", how="left").merge(front.reset_index(), on="race_id", how="left")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"logic_horses_{args.start}_{args.end}.pkl"
    out.to_pickle(path)
    print(f"{out['race_id'].nunique():,} レース・{len(out):,} 頭 → {path}")


if __name__ == "__main__":
    main()
