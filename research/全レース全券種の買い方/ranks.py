"""選んだ型で買ったときの成績を、◎ランク（S・A・B・C）ごとにまとめる（docs/01 の手順5 の見方。確かめる期間）。

    uv run python research/全レース全券種の買い方/ranks.py --trial 1   # ランクごと-1回目.md
    uv run python research/全レース全券種の買い方/ranks.py --trial 2   # ランクごと-2回目.md

券種ごとに、◎ランクごとのレース数・回収率・的中率・1レースの点数と、配当率のランクごとに選んだ型を1つの表にする。
出るものは Git 対象外の ``reports/全レース全券種の買い方/ランクごと-<n>回目.md``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 全レース全券種の買い方.analysis.candidate_counter import CandidateCounter  # noqa: E402
from 全レース全券種の買い方.analysis.cell_selector import CellChoice  # noqa: E402
from 全レース全券種の買い方.analysis.choice_summary import ChoiceSummary  # noqa: E402
from 全レース全券種の買い方.analysis.day_table import HIT_RACES, PAYOUT, POINTS, RACES  # noqa: E402
from 全レース全券種の買い方.analysis.formation import MAX_POINTS, candidates  # noqa: E402
from 全レース全券種の買い方.formations import CONFIRM_YEARS, GRADES, OUT  # noqa: E402


def main() -> None:
    args = _parser().parse_args()
    chosen = json.loads((OUT / f"選んだ型-{args.trial}回目.json").read_text(encoding="utf-8"))
    tables: list[Table] = []
    for label, cells_chosen in chosen.items():
        values, cells, days, labels = CandidateCounter.load(OUT / "候補" / f"{label}.npz")
        if args.trial < 2:
            full = [index for index, formation in enumerate(candidates(label)) if formation.max_points == MAX_POINTS]
            values = values[full]
        choices = [CellChoice(**choice) for choice in cells_chosen]
        selected = ChoiceSummary.selected(values, choices)
        mask = np.array([day.year in CONFIRM_YEARS for day in days])
        rows = []
        for hit in GRADES:
            picked = [index for index, cell in enumerate(cells) if cell.startswith(hit + "/")]
            part = selected[picked][:, mask].sum(axis=0)
            stake, payout = part[:, POINTS].sum() * 100.0, part[:, PAYOUT].sum()
            races, hits = part[:, RACES].sum(), part[:, HIT_RACES].sum()
            forms = [f"{pay}: {choices[cells.index(f'{hit}/{pay}')].label}" for pay in GRADES
                     if f"{hit}/{pay}" in cells and choices[cells.index(f"{hit}/{pay}")].races > 0]
            rows.append([hit, f"{races:,.0f}", _pct(payout / stake) if stake > 0 else "—", _pct(hits / races) if races > 0 else "—",
                         f"{part[:, POINTS].sum() / races:.1f}" if races > 0 else "—", "<br>".join(forms)])
        tables.append(Table(["◎ランク", "レース", "回収率", "的中率", "1レースの点数", "配当率のランクごとに選んだ型"], rows,
                            title=f"{label}: ◎ランクごと（{CONFIRM_YEARS.start}〜{CONFIRM_YEARS.stop - 1}年。{args.trial}回目）",
                            note="1点 100円。型は 2015〜2018年だけで選んだもの（配当率のランク S・A・B・C ごと）。レースは買い目が1点以上あったレース。"))
    path = OUT / f"ランクごと-{args.trial}回目.md"
    render.write(render.render(tables, "markdown"), path, fmt="markdown")
    print(f"保存先: {path}", file=sys.stderr)


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--trial", type=int, default=1, help="何回目の確かめか（選んだ型-<n>回目.json を使う）")
    return parser


if __name__ == "__main__":
    main()
