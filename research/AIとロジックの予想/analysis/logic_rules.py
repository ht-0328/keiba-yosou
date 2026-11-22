"""研究「AIとロジックの予想」: ロジックの決まり（AI の予想の印と買い目を見送るレース）と、期間ごとの成績。

    uv run python research/AIとロジックの予想/analysis/logic_rules.py

``periods.pkl``（3つの期間の買い目の候補と、1レースごとの材料・今の本番の買い目の結果）を読み、決まりごとに
買ったレースの数・回収率・的中率・1日の儲け（今の本番との差）を出す。
期間: 参考1（2022年9月〜2024年9月）・参考2（2024年9月〜2025年9月）は、オッズの動きで直す前の当日の予想なので向きを見る参考。
作る（2025年9月6日〜2026年3月7日）で決まりを選び、確かめる（2026年3月8日〜2026年9月22日）は一度だけ数える。
"""

from __future__ import annotations

import pickle
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import race_outcomes as outcomes  # noqa: E402

#: 確かめる期間の初日。
VERIFY_FROM = "2026-03-08"
_FRONT, _BACK = ("逃げ", "先行"), ("差し", "追込")
#: 展開のロジック: 逃げ・先行の馬が頭数のこの割合以下（ペースが遅くなりそう）。
SLOW_SHARE = 0.20
#: 馬場の偏りのロジック: その日の偏りの z の大きさの線。
BIAS_Z = 1.5

Rule = Callable[[pd.DataFrame], pd.Series]


def every(t: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=t.index)


def slow_pace(t: pd.DataFrame) -> pd.Series:
    """逃げ・先行が少なくペースが遅くなりそうなレースで、◎ が差し・追込なら見送る。"""
    return ~((t["front_runners"] / t["field_size"] <= SLOW_SHARE) & t["top_style"].isin(_BACK))


def track_bias(t: pd.DataFrame) -> pd.Series:
    """その日の馬場が前寄りなのに ◎ が差し・追込、後ろ寄りなのに ◎ が逃げ・先行なら見送る。"""
    return ~(((t["bias_z"] <= -BIAS_Z) & t["top_style"].isin(_BACK)) | ((t["bias_z"] >= BIAS_Z) & t["top_style"].isin(_FRONT)))


RULES: dict[str, Rule] = {
    "今のまま（AI だけ）": every,
    "(a) 展開": slow_pace,
    "(b) 展開＋馬場の偏り": lambda t: slow_pace(t) & track_bias(t),
}


def parts() -> dict[str, pd.DataFrame]:
    periods = pickle.load(open(outcomes.OUT / "periods.pkl", "rb"))
    latest = periods[2].races
    return {"参考1": periods[0].races, "参考2": periods[1].races, "作る": latest[latest["day"] < VERIFY_FROM],
            "確かめる": latest[latest["day"] >= VERIFY_FROM]}


def metrics(t: pd.DataFrame, keep: pd.Series) -> dict:
    bought = t[t["bought"] & keep]
    paid, back = bought["stake"].sum(), bought["back"].sum()
    return {"買う": len(bought), "回収率": back / paid, "的中率": (bought["back"] > 0).mean(), "1日の儲け": (back - paid) / t["day"].nunique()}


def main() -> None:
    for part, table in parts().items():
        base = metrics(table, every(table))
        for name, rule in RULES.items():
            m = metrics(table, rule(table))
            print(f"{part:<5} {name:<16} 買う {m['買う']:4d} 回収率 {m['回収率']:6.1%}（{m['回収率'] - base['回収率']:+5.1%}） "
                  f"的中率 {m['的中率']:5.1%}（{m['的中率'] - base['的中率']:+4.1%}） 1日の儲け {m['1日の儲け']:7,.0f}円")


if __name__ == "__main__":
    main()
