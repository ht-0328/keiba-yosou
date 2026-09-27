"""事例の型ごとにレースを選び、一覧を書く（研究「展開の理論の検証」の入口②）。

    uv run python research/展開の理論の検証/collect_cases.py

先に extract.py で中間データを作っておく。型（``analysis/cases/case_patterns.py``）ごとに、当てはまるレースの数と、
``--from`` 以降から無作為に選んだ ``--count`` レースの一覧を、``reports/展開の理論の検証/cases/一覧.md`` に書く。
一覧の rid は、そのまま ``tools/レース詳細/race.py`` に渡せる。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli  # noqa: E402
from 共通.render import Table  # noqa: E402

from 展開の理論の検証.analysis.cache_store import CacheStore  # noqa: E402
from 展開の理論の検証.analysis.cases import PATTERNS, CasePicker  # noqa: E402
from 展開の理論の検証.analysis.pace import (  # noqa: E402
    NO_BASELINE,
    PACE,
    PACE_GAP,
    PACE_Z,
    WINNER_STYLE,
    WINNER_STYLE_BEFORE,
)
from 展開の理論の検証.extract import DEFAULT_CACHE  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUT = _REPO_ROOT / "reports" / "展開の理論の検証" / "cases" / "一覧.md"
#: 数を数える最初の年（前半タイムの基準に前の3年がそろう年）。
_FIRST_YEAR = 2014
#: 一覧に並べる列と見出し。
_CASE_COLUMNS: dict[str, str] = {
    "race_id": "rid", "race_date": "開催日", "venue": "競馬場", "course": "コース", "distance_m": "距離",
    "condition": "馬場", "class_name": "クラス", "field_size": "頭数", "lead_candidates": "逃げそうな馬",
    PACE: "ペース", PACE_Z: "前半の速さ（z）", PACE_GAP: "基準との差（秒）",
    WINNER_STYLE: "勝ち馬の脚質", WINNER_STYLE_BEFORE: "勝ち馬の推定脚質",
}


def main(args) -> None:
    races = CacheStore(args.cache).read("races")
    counted = races[(races["year"] >= _FIRST_YEAR) & (races[PACE] != NO_BASELINE)]
    recent = counted[pd.to_datetime(counted["race_date"]) >= pd.Timestamp(args.from_date)]
    picker = CasePicker(args.count, args.seed)
    tables = [_count_table(counted)]
    tables += [_case_table(picker.pick(recent, pattern), pattern) for pattern in PATTERNS]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cli.emit(tables, args)


def _count_table(races: pd.DataFrame) -> Table:
    rows = []
    for pattern in PATTERNS:
        matched = int(pattern.matches(races).fillna(False).sum())
        rows.append([pattern.key, pattern.name, pattern.relation, matched, round(matched / len(races) * 100, 1)])
    return Table(["型", "中身", "理論との関係", "レース数", "全体に対する%"], rows,
                 title=f"型ごとのレース数（{_FIRST_YEAR}年から、{len(races)}レース）")


def _case_table(picked: pd.DataFrame, pattern) -> Table:
    shown = picked[list(_CASE_COLUMNS)].rename(columns=_CASE_COLUMNS)
    shown = shown.assign(開催日=pd.to_datetime(shown["開催日"]).dt.strftime("%Y-%m-%d"),
                         **{"前半の速さ（z）": shown["前半の速さ（z）"].round(2),
                            "基準との差（秒）": shown["基準との差（秒）"].round(2)})
    return Table(list(shown.columns), shown.values.tolist(),
                 title=f"{pattern.key}: {pattern.name}（{pattern.relation}）")


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.set_defaults(out=_DEFAULT_OUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="中間データの置き場")
    parser.add_argument("--from", dest="from_date", default="2023-01-01", help="事例を選ぶ最初の開催日")
    parser.add_argument("--count", type=int, default=20, help="型ごとに選ぶレースの数")
    parser.add_argument("--seed", type=int, default=0, help="無作為に選ぶときの種")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
