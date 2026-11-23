"""研究「AIとロジックの予想」: 騎手の暗黙の了解から作った材料と、買う線を外したときの印の買い目の結果を、期間ごとのレースの表に足す。

    uv run python research/AIとロジックの予想/analysis/convention_materials.py

``race_materials.py`` の ``materials.pkl``（5つの期間の、1行 = 1レースの表）に次を足す。どれもレースの前に分かる（人気は確定のもの）。
- レースの材料: 逃げの候補（推定脚質が逃げ）のうち一番人気のある馬の人気 ``best_lead_pop``、逃げの候補の頭数 ``lead_count``、
  減量の騎手の逃げの候補の頭数 ``lead_apprentices``、逃げ・先行で3番人気以内の馬の頭数 ``front_popular``。
- ◎ の騎手の材料: 騎手の格 ``top_jockey_class``、後ろから位置を上げる割合 ``top_move_rate``（``convention_facts.py``）。
- 買う線を外した結果: 印の買い目を本番と同じ配り方で買ったときの見込みの回収率 ``f_expected``・投資 ``f_stake``・払戻 ``f_back``
  （AI が買わないレースも数えるため）。
出るもの（Git 対象外）: ``reports/AIとロジックの予想/convention.pkl``（期間の名前 → 表）。
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import convention_facts  # noqa: E402
import race_materials  # noqa: E402
import race_outcomes as outcomes  # noqa: E402

PATH = outcomes.OUT / "convention.pkl"
_FRONT_STYLES = ("逃げ", "先行")
#: 「人気のある前の馬」と見る人気。
POPULAR = 3


def race_features(runs: pd.DataFrame) -> pd.DataFrame:
    """レースごとの材料（索引は race_id）。逃げの候補のいないレースは ``best_lead_pop`` が欠損値、頭数は 0。"""
    leads = runs[runs["style_before"] == "逃げ"]
    by_race = leads.groupby("race_id")
    out = pd.DataFrame({"best_lead_pop": by_race["popularity"].min(), "lead_count": by_race.size(),
                        "lead_apprentices": (leads["apprentice"] == "減量あり").groupby(leads["race_id"]).sum()})
    front = runs["style_before"].isin(_FRONT_STYLES) & (runs["popularity"] <= POPULAR)
    out = out.join(front.groupby(runs["race_id"]).sum().rename("front_popular"), how="outer")
    counts = ["lead_count", "lead_apprentices", "front_popular"]
    return out.assign(**{name: out[name].fillna(0).astype(int) for name in counts})


def top_features(runs: pd.DataFrame, habits: pd.DataFrame) -> pd.DataFrame:
    """馬ごとの騎手の材料（索引は race_id・horse_id）。"""
    table = runs.merge(habits, on=["year", "jockey_code"], how="left").set_index(["race_id", "horse_id"])
    return table[["jockey_class", "move_rate", "front_rate"]].rename(columns={"jockey_class": "top_jockey_class", "move_rate": "top_move_rate",
                                                                            "front_rate": "top_front_rate"})


def forced(pool: pd.DataFrame) -> pd.DataFrame:
    """買う線を外して、全レースの印の買い目を本番と同じ配り方で買った結果（索引は race_id）。"""
    rows = []
    for race_id, race in pool.groupby("race_id", sort=False):
        add_back = race["p"].iloc[0] >= outcomes.REVERSE_LINE
        tickets = race[(race["kind"] == "表") | ((race["kind"] == outcomes.compare.EXACTA_BACK) & add_back)].to_dict("records")
        chosen, _ = outcomes.EqualPayoutStakes().allocate(tickets)
        if not chosen:
            continue
        yen = outcomes.mark_return._amounts(chosen)
        rows.append((str(race_id), sum(share * ticket["value"] for ticket, share in chosen if ticket["value"] == ticket["value"]),
                     sum(yen), sum(amount * ticket["pay"] / 100 for amount, (ticket, _) in zip(yen, chosen, strict=True))))
    return pd.DataFrame(rows, columns=["race_id", "f_expected", "f_stake", "f_back"]).set_index("race_id")


def attach(table: pd.DataFrame, races: pd.DataFrame, horses: pd.DataFrame, settled: pd.DataFrame) -> pd.DataFrame:
    """1つの期間の表（索引は race_id）に、レースの材料・◎ の騎手の材料・買う線を外した結果を足す。"""
    keys = pd.MultiIndex.from_arrays([table.index, table["top_horse_id"].astype(str)])
    return table.join(races).join(horses.reindex(keys).set_axis(table.index)).join(settled)


def main() -> None:
    import logic_eval  # noqa: F401  （periods.pkl を読むのに要る）

    runs = convention_facts.with_jockey_rank(convention_facts.read())
    races, horses = race_features(runs), top_features(runs, convention_facts.jockey_habits(runs))
    periods = pickle.load(open(outcomes.OUT / "periods.pkl", "rb"))
    _, start, end = race_materials.EXTRA
    settled = pd.concat([forced(period.pool) for period in periods] + [forced(outcomes.pool(start, start, end))])
    settled = settled[~settled.index.duplicated()]
    out = {name: attach(table, races, horses, settled) for name, table in pd.read_pickle(race_materials.PATH).items()}
    pd.to_pickle(out, PATH)
    print("・".join(f"{name} {len(table):,} レース" for name, table in out.items()), "→", PATH)


if __name__ == "__main__":
    main()
