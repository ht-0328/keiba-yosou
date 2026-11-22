"""研究「AIとロジックの予想」: 材料の値ごとに、AI＋展開が買ったレースの回収率と的中率が、探す3つの期間とも平均より低い（高い）ものを洗い出す。

    uv run python research/AIとロジックの予想/analysis/logic_scan.py

探す期間は 参考1・参考2・作る。確かめる期間は見ない。``race_materials.py`` の ``materials.pkl`` を読む。
1つの期間で 12 レース未満の値は出さない。ここで出たものは候補で、採るかは ``logic_candidates.py`` で決める。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import logic_rules  # noqa: E402
import race_materials  # noqa: E402

SEARCH: tuple[str, ...] = ("参考1", "参考2", "作る")
MIN_RACES = 12


def _cut(values: pd.Series, edges: list[float], missing: str = "なし") -> pd.Series:
    return pd.cut(values, edges).astype(str).where(values.notna(), missing)


def bins(t: pd.DataFrame) -> pd.DataFrame:
    """材料ごとの区切り（1行 = 1レース、1列 = 1つの材料）。"""
    win_rate = t["h_wins_before"] / t["h_runs_before"].replace(0, np.nan)
    front = np.where(t["top_style"].isin(["逃げ", "先行"]), "前", np.where(t["top_style"].isin(["差し", "追込"]), "後", "なし"))
    return pd.DataFrame({
        "クラス": t["class_name"], "芝ダ": t["surface"], "馬場": t["condition"], "競馬場": t["venue"], "斤量の種類": t["weight_type"],
        "牝馬限定": np.where(t["mixed_sex"], "混合", "限定"), "月": t["month"].astype(str),
        "距離": _cut(t["distance_m"], [0, 1300, 1600, 2000, 2400, 9999]), "頭数": _cut(t["field_size"], [0, 8, 11, 14, 18]),
        "レース番号": _cut(t["race_no"], [0, 4, 8, 10, 11, 12]),
        "◎ の人気": _cut(t["top_popularity"], [0, 1, 2, 3, 5, 99]), "◎ の単勝": _cut(t["top_win_odds"], [0, 2, 3, 5, 8, 15, 20, 999]),
        "◎ の脚質": t["top_style"].fillna("なし"), "◎ の枠": t["h_frame_no"].astype(str), "◎ の性": t["h_sex"],
        "◎ の年齢": _cut(t["h_age"], [0, 2, 3, 4, 5, 99]), "◎ の間隔": _cut(t["h_interval_days"], [0, 14, 28, 63, 120, 9999], "初出走"),
        "◎ の前走着順": _cut(t["h_prev_finish"], [0, 1, 3, 5, 9, 99]), "◎ の前走人気": _cut(t["h_prev_popularity"], [0, 1, 3, 6, 99]),
        "◎ の乗り替わり": t["h_jockey_change"].fillna("なし"), "◎ の芝ダ替わり": t["h_surface_change"].fillna("なし"),
        "◎ の距離替わり": t["h_distance_change"].fillna("なし"), "◎ のクラス替わり": t["h_class_change"].fillna("なし"),
        "◎ の馬体重の増減": _cut(t["h_weight_change"], [-99, -10, -4, 4, 10, 99]),
        "◎ の出走数": _cut(t["h_runs_before"].fillna(0), [-1, 0, 2, 5, 10, 15, 999]), "◎ の勝率": _cut(win_rate, [-1, 0, 0.1, 0.2, 0.34, 1]),
        "◎ の持ち時計の順位": _cut(t["h_best_time_dist_rank"], [0, 1, 3, 6, 99]),
        "◎ の前走の上がりの順位": _cut(t["h_prev_last3f_rank"], [0, 1, 3, 6, 99]),
        "初出走の頭数": _cut(t["n_first"], [-1, 0, 2, 99]), "逃げの候補の頭数": _cut(t["n_lead"].fillna(0), [-1, 0, 1, 2, 99]),
        "逃げ・先行の割合 × ◎ の脚質": _cut(t["front_runners"] / t["field_size"], [-1, 0.2, 0.3, 0.4, 0.5, 2]) + " " + front,
        "2番人気の単勝": _cut(t["odds2"], [0, 3, 4, 5, 7, 99]), "1番人気の単勝": _cut(t["favorite_odds"], [0, 1.5, 2, 2.5, 3.5, 99]),
        "消の人気": t["out_popularity"].fillna(0).astype(int).astype(str),
        "◎ の単勝の期待値": _cut(t["top_win_value"], [0, 1.0, 1.15, 1.3, 1.6, 99]),
        "◎ のオッズの動き": _cut(t["top_odds_move"], [-9, -0.15, -0.05, 0.05, 0.15, 9]),
        "◎ の3連単の支持": _cut(t["top_pool_support"], [-9, 0.85, 0.95, 1.05, 1.15, 9]),
        "見込みの回収率": _cut(t["expected"], [0, 1.1, 1.25, 1.5, 2, 99]),
        "その日の馬場の偏り": _cut(t["bias_z"], [-99, -1.5, -0.5, 0.5, 1.5, 99], "不明"),
    }, index=t.index)


def bought(table: pd.DataFrame) -> pd.DataFrame:
    """AI＋展開（今の AI＋ロジック予想）が買ったレース。"""
    return table[table["bought"] & logic_rules.slow_pace(table)]


def scan(parts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """材料 × 値ごとの、期間ごとのレース数・回収率・的中率の、期間の平均との差。"""
    tables = {name: bought(parts[name]) for name in SEARCH}
    groups = {name: bins(table) for name, table in tables.items()}
    rows = []
    for column in groups[SEARCH[0]].columns:
        for value in sorted(set().union(*(set(group[column].astype(str)) for group in groups.values()))):
            row: dict[str, object] = {"材料": column, "値": value}
            for name, table in tables.items():
                part = table[groups[name][column].astype(str) == value]
                row[f"{name} 数"] = len(part)
                row[f"{name} 回収率の差"] = part["back"].sum() / max(part["stake"].sum(), 1) - table["back"].sum() / table["stake"].sum()
                row[f"{name} 的中率の差"] = (part["back"] > 0).mean() - (table["back"] > 0).mean()
            rows.append(row)
    return pd.DataFrame(rows)


def consistent(found: pd.DataFrame, sign: int) -> pd.DataFrame:
    """3つの期間とも数が足り、回収率と的中率の差の符号が ``sign``（−1 = 低い、+1 = 高い）の行。"""
    enough = (found[[f"{name} 数" for name in SEARCH]] >= MIN_RACES).all(axis=1)
    differences = found[[f"{name} {kind}" for name in SEARCH for kind in ("回収率の差", "的中率の差")]]
    return found[enough & ((differences * sign) > 0).all(axis=1)]


def main() -> None:
    found = scan(pd.read_pickle(race_materials.PATH))
    pd.set_option("display.width", 300)
    for title, sign in (("3つの期間とも回収率・的中率が平均より低い", -1), ("3つの期間とも高い", 1)):
        print(f"== {title}")
        print(consistent(found, sign).to_string(index=False, float_format=lambda value: f"{value:+.2f}"))


if __name__ == "__main__":
    main()
