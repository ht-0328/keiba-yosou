"""重賞（2015〜2022年）で、今の予想が外れた事例を集めて並べる（研究「重賞の事例から材料を作る」の段1）。

    uv run python research/重賞の事例から材料を作る/cases.py      # 事例の一覧を reports/重賞の事例から材料を作る/事例.md に書く

読むもの（どれも先に作っておく。DB は開かない）:
- ``reports/重賞の事例から材料を作る/facts.parquet``: 事実表（元DB の写しから作ったもの）
- ``reports/既存モデルの改善/predictions/graded_race_day/``: 今の予想の3着以内の確率（2015〜2019年は前日の予想、2020〜2022年は当日の予想。どちらもテストの年の値）

事例は2種類。
- 見落とし: 予想の順位が6位以下なのに3着以内に来た馬
- 買いかぶり: 予想の順位が1〜2位なのに4着以下だった馬
どちらも、前走のレース名・格・着順・人気・間隔・騎手の乗り替わり・斤量の増減などを並べ、人が読んで理由を考える材料にする。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
_OUT = _ROOT / "reports" / "重賞の事例から材料を作る"
_PREDICTIONS = _ROOT / "reports" / "既存モデルの改善" / "predictions" / "graded_race_day"
#: 予想の確率のファイルと、使う年。
_SOURCES = (("dayb-top3-early.pkl", "2015", "2019"), ("general-top3.pkl", "2020", "2022"))
_GRADED = ("A", "B", "C")
_GRADE_NAMES = {"A": "G1", "B": "G2", "C": "G3"}


def main() -> None:
    facts = pd.read_parquet(_OUT / "facts.parquet")
    runs = _with_previous_race(facts)
    graded = runs[runs["grade_code"].isin(_GRADED) & runs["surface"].ne("障害") & runs["year"].between(2015, 2022)]
    rows = graded.merge(_predictions(), on=["race_id", "horse_id"], how="inner")
    rows = rows.assign(予想の順位=rows.groupby("race_id")["p"].rank(ascending=False, method="first").astype(int))
    missed = rows[rows["予想の順位"].ge(6) & rows["finish"].le(3)]
    over = rows[rows["予想の順位"].le(2) & rows["finish"].ge(4)]
    lines = ["# 重賞の事例（2015〜2022年）", "",
             f"重賞の行 {len(rows):,}（{rows['race_id'].nunique():,} レース）。見落とし {len(missed):,}・買いかぶり {len(over):,}。", ""]
    lines += _section("見落とし（予想6位以下で3着以内）", missed)
    lines += _section("買いかぶり（予想1〜2位で4着以下）", over)
    out = _OUT / "事例.md"
    out.write_bytes("\n".join(lines).encode("utf-8"))
    print(out)


def _with_previous_race(facts: pd.DataFrame) -> pd.DataFrame:
    """出走ごとに、前走のレース名・格・頭数を足す（走った出走だけを前走にする）。"""
    ran = facts[facts["ran"]].sort_values(["horse_id", "race_date", "race_id"])
    previous = ran.groupby("horse_id")[["race_name", "grade_code", "class_name", "race_date", "carried"]].shift(1)
    previous.columns = ["前走のレース名", "前走のグレード", "前走のクラス", "前走の日", "前走の斤量"]
    return ran.join(previous)


def _predictions() -> pd.DataFrame:
    frames = []
    for name, first, last in _SOURCES:
        frame = pd.read_pickle(_PREDICTIONS / name)
        frame = frame[frame["期間"].eq("テスト")]
        year = frame["レースID"].astype(str).str[:4]
        frame = frame[year.between(first, last)]
        frames.append(pd.DataFrame({"race_id": frame["レースID"].astype(str), "horse_id": frame["馬ID"].astype(str),
                                    "p": frame["確率"].to_numpy()}))
    return pd.concat(frames, ignore_index=True).drop_duplicates(["race_id", "horse_id"], keep="last")


def _section(title: str, rows: pd.DataFrame) -> list[str]:
    header = ("| 日 | レース | 格 | 馬番 | 年齢 | 人気 | 予想の順位 | 確率 | 着順 | 前走 | 前走の格 | 前走の着順 | 前走の人気 | 間隔 | 乗り替わり | 斤量の増減 |\n"
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    lines = [f"## {title}", "", header]
    for _, r in rows.sort_values(["race_date", "race_id", "finish"]).iterrows():
        prev_grade = _GRADE_NAMES.get(str(r["前走のグレード"]).strip(), r["前走のクラス"])
        lines.append(f"| {r['race_date']} | {r['race_name']} | {_GRADE_NAMES[r['grade_code']]} | {r['horse_no']} | {r['age']} | {r['popularity']} | "
                     f"{r['予想の順位']} | {r['p']:.2f} | {r['finish']} | {r['前走のレース名']} | {prev_grade} | {r['prev_finish']} | "
                     f"{r['prev_popularity']} | {r['interval_days']} | {r['jockey_change']} | {r['carried'] - _prev_carried(r):+.1f} |")
    return lines + [""]


def _prev_carried(row: pd.Series) -> float:
    return row["carried"] if pd.isna(row.get("前走の斤量")) else row["前走の斤量"]


if __name__ == "__main__":
    sys.exit(main())
