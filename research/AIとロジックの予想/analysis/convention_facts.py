"""研究「AIとロジックの予想」: 騎手の暗黙の了解（力関係で決まる隊列）が、過去のレースの数字に出ているかを数える。

    uv run python research/AIとロジックの予想/analysis/convention_facts.py

数えるもの（2016年からの芝・ダート。騎手の格と乗り方は前の年の成績から作るので、2015年から読む）:
- 逃げの候補（推定脚質が逃げ）が2頭以上いるレースで、実際に最初のコーナーを先頭で回った割合（人気・騎手の格・減量・枠ごと）。
- 逃げた馬の成績と、レースの前3ハロンの速さ（逃げた騎手の格ごと）。
- 最初のコーナーと4コーナーの順位の近さ（隊列が決まると動かないか）と、後ろから位置を上げた割合（騎手の格ごと）。
騎手の格は「前の年の勝ち数の順位」。レースの前に分かる。元DB は読むだけ。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "tools"))

#: 数え始める年（騎手の格と乗り方は、この前の年から作る）。
FIRST_YEAR = 2016
#: 騎手の格の区切り（前の年の勝ち数の順位）と名前。
CLASS_EDGES: tuple[float, ...] = (0, 10, 30, 60, 9999)
CLASS_NAMES: tuple[str, ...] = ("上位10", "11-30", "31-60", "61-")
#: 順位の無い騎手（前の年に勝っていない・乗っていない）の順位。
NO_RANK = 999.0
#: 「位置を上げた」と見る、最初のコーナーから4コーナーまでに上げた順位の、頭数に対する割合。
MOVE_SHARE = 0.25
#: 乗り方の割合を出すのに要る、前の年の騎乗数。
MIN_RIDES = 50
_COLUMNS = ("race_id", "race_date", "venue", "surface", "distance_m", "field_size", "horse_id", "horse_no", "jockey_code", "apprentice",
            "popularity", "win_odds", "finish", "style", "style_before", "lead_candidates", "first_corner_rank", "corner4", "first3f")


def read(first_year: int = FIRST_YEAR - 1) -> pd.DataFrame:
    """事実表の、出走した馬の 1行 = 1頭（芝・ダート）。"""
    from 共通 import db, facts

    with db.open_db() as con:
        table = facts.ensure_facts(con)
        runs = con.execute(f"""
            SELECT {", ".join(_COLUMNS)} FROM {table}
            WHERE race_date >= '{first_year}-01-01' AND ran AND surface IN ('芝', 'ダート')
        """).df()
    numbers = ["popularity", "win_odds", "finish", "first_corner_rank", "corner4", "field_size", "horse_no"]
    return runs.assign(race_id=runs["race_id"].astype(str), horse_id=runs["horse_id"].astype(str),
                       year=pd.to_datetime(runs["race_date"]).dt.year, **{name: runs[name].astype(float) for name in numbers})


def with_jockey_rank(runs: pd.DataFrame) -> pd.DataFrame:
    """騎手の格（前の年の勝ち数の順位 ``jockey_rank`` と区切り ``jockey_class``）を足す。前の年に勝ちが無ければ ``NO_RANK``。"""
    wins = runs[runs["finish"] == 1].groupby(["year", "jockey_code"]).size().rename("wins").reset_index()
    wins["jockey_rank"] = wins.groupby("year")["wins"].rank(ascending=False, method="min")
    wins["year"] += 1
    out = runs.merge(wins[["year", "jockey_code", "jockey_rank"]], on=["year", "jockey_code"], how="left")
    out["jockey_rank"] = out["jockey_rank"].fillna(NO_RANK)
    out["jockey_class"] = pd.cut(out["jockey_rank"], list(CLASS_EDGES), labels=list(CLASS_NAMES)).astype(str)
    return out


def moved_up(runs: pd.DataFrame) -> pd.Series:
    """最初のコーナーから4コーナーまでに、頭数の ``MOVE_SHARE`` 以上の順位を上げたか。"""
    return (runs["first_corner_rank"] - runs["corner4"]) / runs["field_size"] >= MOVE_SHARE


def jockey_habits(runs: pd.DataFrame) -> pd.DataFrame:
    """騎手の前の年の乗り方（1行 = 年 × 騎手。``year`` は使う年）。

    ``move_rate`` は、最初のコーナーを後ろ半分で回った騎乗のうち位置を上げた割合。``front_rate`` は逃げ・先行だった割合。
    前の年の騎乗が ``MIN_RIDES`` 未満なら欠損値。
    """
    seen = runs[runs["first_corner_rank"].notna()]
    seen = seen.assign(front=seen["style"].isin(["逃げ", "先行"]), moved=moved_up(seen))
    habits = seen.groupby(["year", "jockey_code"]).agg(rides=("front", "size"), front_rate=("front", "mean")).reset_index()
    rear = seen[seen["first_corner_rank"] / seen["field_size"] > 0.5]
    habits = habits.merge(rear.groupby(["year", "jockey_code"])["moved"].mean().rename("move_rate").reset_index(), how="left")
    habits.loc[habits["rides"] < MIN_RIDES, ["front_rate", "move_rate"]] = np.nan
    return habits.assign(year=habits["year"] + 1)[["year", "jockey_code", "front_rate", "move_rate"]]


def lead_shares(candidates: pd.DataFrame, by: pd.Series) -> pd.DataFrame:
    """逃げの候補を ``by`` で分けた、実際に逃げた割合と頭数。"""
    led = candidates["first_corner_rank"] == 1
    return led.groupby(by, observed=True).agg(["mean", "size"]).set_axis(["逃げた割合", "頭数"], axis=1)


def main() -> None:
    runs = with_jockey_rank(read())
    runs = runs[(runs["year"] >= FIRST_YEAR) & runs["first_corner_rank"].notna()]
    several = runs[(runs["style_before"] == "逃げ") & (runs["lead_candidates"] >= 2)]
    pd.set_option("display.width", 200)
    print("== 逃げの候補が2頭以上のレースで、実際に逃げた割合")
    for title, by in (("人気", pd.cut(several["popularity"], [0, 1, 3, 6, 9, 99])), ("騎手の格", several["jockey_class"]),
                      ("減量", several["apprentice"]), ("枠", pd.cut(several["horse_no"] / several["field_size"], [0, 0.34, 0.67, 1.01], labels=["内", "中", "外"]))):
        print(f"-- {title}"); print(lead_shares(several, by).round(3))
    two = several[several["lead_candidates"] == 2]
    print("-- 候補がちょうど2頭: 人気が上の方（1）と下の方（2）"); print(lead_shares(two, two.groupby("race_id")["popularity"].rank(method="first")).round(3))
    leaders = runs[runs["first_corner_rank"] == 1]
    leaders = leaders.assign(win=leaders["finish"] == 1, top3=leaders["finish"] <= 3, back=np.where(leaders["finish"] == 1, leaders["win_odds"], 0.0),
                             slower=leaders["first3f"] - leaders.groupby(["venue", "surface", "distance_m"])["first3f"].transform("mean"))
    print("== 逃げた馬の成績と、前3ハロン（コースの平均との差の秒。＋が遅い）: 騎手の格ごと")
    print(leaders.groupby("jockey_class").agg(頭数=("win", "size"), 勝率=("win", "mean"), 三着以内率=("top3", "mean"), 単勝の回収率=("back", "mean"), 前3ハロンの差=("slower", "mean")).round(3))
    lined = runs[runs["corner4"].notna() & (runs["field_size"] >= 8)]
    print(f"== 最初のコーナーと4コーナーの順位の相関 {lined['first_corner_rank'].corr(lined['corner4']):.3f}・位置を上げた割合 {moved_up(lined).mean():.1%}")
    rear = lined[lined["first_corner_rank"] / lined["field_size"] > 0.5]
    print("-- 後ろ半分から位置を上げた割合: 騎手の格ごと"); print(moved_up(rear).groupby(rear["jockey_class"]).mean().round(3))


if __name__ == "__main__":
    main()
