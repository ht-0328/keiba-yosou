"""研究「重賞の買い方」5回目の入口: 重賞に特化した予想の印で全部の重賞を買う形を、前半の年（2020〜2022年）で選び、後半の年（2023〜2026年）で一度だけ数える
（設計書「重賞に特化して3着以内と1着を予想」16 の 6）。

    uv run python research/重賞の買い方/graded_model.py mark --top3 graded_race_day/graded-top3 --win graded_race_day/graded-win --name 重賞特化
    uv run python research/重賞の買い方/graded_model.py count --name 重賞特化     # 形の候補を全部の重賞で数える（元DB で組のオッズと払戻を読む）
    uv run python research/重賞の買い方/graded_model.py search --name 重賞特化    # 前半の年だけで、券種ごとの形とレースごとの券種の選び方を選ぶ
    uv run python research/重賞の買い方/graded_model.py check --name 重賞特化     # 選んだものを後半の年で一度だけ数える
    uv run python research/重賞の買い方/graded_model.py plan --name 前日-前の年   # 決めておいた買い方（案A・案B。docs/06 の 6）を年ごとに数える

予測は研究「既存モデルの改善」の 7つの区切り（1年ずつ）のもの（``reports/既存モデルの改善/predictions/<表>/<作り方>.pkl``）。
``--family 全部`` を付けると、印の形に加えて、組の期待値の高い順に N 点を買う形（4回目の形。全部の組の表から数える）からも選ぶ（印の形で届かなかったときの次の候補）。
出るもの（Git 対象外）: ``reports/重賞の買い方/5回目/<名前>/``（印を付けた表・組の表・数え上げ・選んだもの-<範囲>.json・選んだ形-<範囲>.md・確かめ-<範囲>.md）。
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_ROOT / "research"), str(_ROOT / "tools")]

from 共通 import db  # noqa: E402

from yosou.form_aptitude_top3.command.yosou_name import YOSOU_NAME  # noqa: E402
from yosou.shared.place_value import PlacePriceEstimator  # noqa: E402
from yosou.shared.repository import PlacePriceRepository  # noqa: E402

from 印の成績.backtest_marker import BacktestMarker  # noqa: E402
from 印の成績.prediction_file import PredictionFile  # noqa: E402
from 全レース全券種の買い方.analysis.recovery_bootstrap import RecoveryBootstrap  # noqa: E402
from 重賞の買い方.analysis.graded_model import (  # noqa: E402
    CURRENT_RULE_SHAPES,
    GRADE,
    MEAN_VALUE,
    POINTS,
    RACE_GRADE,
    RETURN,
    SHAPE,
    SHAPES,
    TICKETS,
    UNIT,
    ComboUniverse,
    GradedRaceMarker,
    ShapeChooser,
    ShapeCounter,
    TicketShape,
    TopValueRule,
)
from 重賞の買い方.analysis.graded_model.value_rank_counter import ValueRankCounter, value_rank_shapes  # noqa: E402

OUT = _ROOT / "reports" / "重賞の買い方" / "5回目"
#: 前半の年（選ぶ）と後半の年（確かめる）。
SELECT_YEARS, CONFIRM_YEARS = range(2020, 2023), range(2023, 2027)
#: 数える形（印の形の候補・今の印の買い目・組の期待値の高い順に買う形）。番号は、この並びの中の位置。
VALUE_SHAPES = value_rank_shapes()
ALL_SHAPES = (*SHAPES, *CURRENT_RULE_SHAPES, *VALUE_SHAPES)
#: 形を選ぶ範囲。「印」は設計書 16 の 6.3 の候補だけ（初めの確かめ）、「全部」は組の期待値の高い順に買う形も入れる（届かなかったときの次の候補）。
FAMILIES = {"印": range(len(SHAPES)), "全部": [*range(len(SHAPES)), *range(len(SHAPES) + len(CURRENT_RULE_SHAPES), len(ALL_SHAPES))]}
#: 研究「複勝以外の回収率100超」の全部の組の表。
COMBOS = _ROOT / "reports" / "複勝以外の回収率100超" / "組の期待値" / "combos"
#: 後半の年を見たあとに見つけ、まだ見ていない年（2015〜2019年）で一度だけ確かめる買い方（docs/06 の 6 の「4回目の確かめ」）。
_TRIFECTA_FLOW = TicketShape("3連単", "◎→○▲→無印に流す")
_TRIO_FLOW = TicketShape("3連複", "◎軸−相手−相手", "無印に流す", cap=1000.0, line=1.2)
PLANS: dict[str, tuple[TicketShape, ...]] = {
    "案A": (_TRIFECTA_FLOW, TicketShape("単勝", "◎")),
    "案B": (_TRIFECTA_FLOW, TicketShape("単勝", "◎"), _TRIO_FLOW),
}
#: レースごとの券種の選び方の候補（16 の 6.5 のア）。
RULES = tuple(TopValueRule(k, line) for k in (2, 3, 4) for line in (None, 1.0))


def main() -> None:
    args = _parser().parse_args()
    folder = OUT / args.name
    folder.mkdir(parents=True, exist_ok=True)
    {"mark": _mark, "count": _count, "search": _search, "check": _check, "plan": _plan}[args.command](args, folder)


def _mark(args: argparse.Namespace, folder: Path) -> None:
    state = PlacePriceRepository(_ROOT / "reports" / YOSOU_NAME / "models").load()
    marker = GradedRaceMarker(BacktestMarker(PlacePriceEstimator.from_state(state) if state is not None else None))
    with db.open_db(args.db) as con:
        marked = marker.mark(con, PredictionFile(args.top3).load(), PredictionFile(args.win).load())
    marked["race_date"] = pd.to_datetime(marked["race_date"])
    marked.to_pickle(folder / "印.pkl")
    (folder / "予測.json").write_text(json.dumps({"top3": args.top3, "win": args.win}, ensure_ascii=False), encoding="utf-8")
    print(f"{marked['race_id'].nunique():,} 重賞・{len(marked):,} 頭に印を付けました（{marked['race_date'].min():%Y-%m-%d} 〜 {marked['race_date'].max():%Y-%m-%d}）")


def _count(args: argparse.Namespace, folder: Path) -> None:
    marked = pd.read_pickle(folder / "印.pkl")
    with db.open_db(args.db) as con:
        universe = ComboUniverse().build(con, marked, ALL_SHAPES[:len(SHAPES) + len(CURRENT_RULE_SHAPES)])
    universe.to_pickle(folder / "組.pkl")
    counts = ShapeCounter().count(marked, universe, ALL_SHAPES[:len(SHAPES) + len(CURRENT_RULE_SHAPES)])
    ranked = ValueRankCounter(COMBOS).count(marked, VALUE_SHAPES, sorted(marked["race_date"].dt.year.unique()),
                                            offset=len(SHAPES) + len(CURRENT_RULE_SHAPES))
    counts = pd.concat([counts, ranked], ignore_index=True)
    counts.to_pickle(folder / "数え上げ.pkl")
    print(f"組 {len(universe):,}・数え上げ {len(counts):,} 行")


def _years(frame: pd.DataFrame, years: range) -> pd.DataFrame:
    return frame[frame["race_date"].dt.year.isin(list(years))]


def _search(args: argparse.Namespace, folder: Path) -> None:
    counts = _years(pd.read_pickle(folder / "数え上げ.pkl"), SELECT_YEARS)
    chooser = ShapeChooser()
    summary = chooser.summary(counts, ALL_SHAPES)
    chosen = chooser.choose(summary[summary[SHAPE].isin(FAMILIES[args.family])])
    rule_rows = [_rule_row(rule.name, rule.pick(counts, chosen), counts) for rule in RULES]
    best_rule = max(range(len(RULES)), key=lambda index: rule_rows[index]["lower"])
    fixed = _best_fixed(counts, chosen)
    saved = {"shapes": chosen, "rule": {"k": RULES[best_rule].k, "line": RULES[best_rule].line}, "fixed": list(fixed[0])}
    (folder / f"選んだもの-{args.family}.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 5回目 {args.name}（形の範囲: {args.family}）: 前半の年（{SELECT_YEARS[0]}〜{SELECT_YEARS[-1]}年）で選んだもの", "",
             f"重賞 {counts['race_id'].nunique()}レース。当たった重賞が 15 以上の形のうち、回収率の 90% の幅の下の端がいちばん高い形。", "",
             "## 券種ごとに選んだ形", "", "| 券種 | 形 | 買った重賞 | 当たった重賞 | 点数 | 回収率 | 下の端 |", "|---|---|---|---|---|---|---|"]
    for ticket in TICKETS:
        if ticket in chosen:
            row = summary.loc[chosen[ticket]]
            lines.append(f"| {ticket} | {row['name']} | {row['races']} | {row['hits']} | {row['points']} | {row['rate']:.1%} | {row['lower']:.1%} |")
    lines += ["", "## レースごとの券種の選び方（ア）", "", "| 決まり | 買った券種の数 | 回収率 | 下の端 | 的中率 |", "|---|---|---|---|---|"]
    lines += [f"| {'**' if index == best_rule else ''}{row['name']}{'**' if index == best_rule else ''} | {row['tickets']} | {row['rate']:.1%} | {row['lower']:.1%} | {row['hit_rate']:.1%} |"
              for index, row in enumerate(rule_rows)]
    lines += ["", f"比べる行（全部の重賞で同じ券種）: {'・'.join(fixed[0])} 回収率 {fixed[1]['rate']:.1%}・下の端 {fixed[1]['lower']:.1%}", "",
              "## 券種ごとの上位10の形（下の端の順。参考）", ""]
    for ticket in TICKETS:
        top = summary[(summary["ticket"] == ticket) & summary[SHAPE].isin(FAMILIES[args.family])].sort_values("lower", ascending=False).head(10)
        lines += [f"### {ticket}", "", "| 形 | 当たった重賞 | 回収率 | 下の端 |", "|---|---|---|---|"]
        lines += [f"| {row['name']} | {row['hits']} | {row['rate']:.1%} | {row['lower']:.1%} |" for _, row in top.iterrows()]
        lines.append("")
    (folder / f"選んだ形-{args.family}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:40]))


def _rule_row(name: str, picked: pd.DataFrame, counts: pd.DataFrame) -> dict:
    """決まり1つの合計（回収率・下の端・的中率・1レースあたりの券種の数）。"""
    days = sorted(counts["race_date"].unique())
    stake, payback = _by_day(picked, days)
    lower = float(RecoveryBootstrap(len(days)).lower(stake[None, :], payback[None, :])[0])
    hits = picked.groupby("race_id")[RETURN].sum().gt(0).sum()
    races = counts["race_id"].nunique()
    return {"name": name, "rate": payback.sum() / stake.sum() if stake.sum() else np.nan, "lower": lower,
            "hit_rate": hits / races, "tickets": f"{len(picked) / races:.2f}"}


def _by_day(picked: pd.DataFrame, days: list) -> tuple[np.ndarray, np.ndarray]:
    position = {day: index for index, day in enumerate(days)}
    stake, payback = np.zeros(len(days)), np.zeros(len(days))
    columns = picked["race_date"].map(position).to_numpy()
    np.add.at(stake, columns, picked[POINTS].to_numpy() * UNIT)
    np.add.at(payback, columns, picked[RETURN].to_numpy())
    return stake, payback


def _best_fixed(counts: pd.DataFrame, chosen: dict[str, int]) -> tuple[tuple[str, ...], dict]:
    """全部の重賞で同じ 2〜4券種を買う組のうち、下の端がいちばん高い組。"""
    best = None
    for size in (2, 3, 4):
        for tickets in combinations([ticket for ticket in TICKETS if ticket in chosen], size):
            picked = counts[counts[SHAPE].isin([chosen[ticket] for ticket in tickets]) & (counts[POINTS] > 0)]
            row = _rule_row("・".join(tickets), picked, counts)
            if best is None or row["lower"] > best[1]["lower"]:
                best = (tickets, row)
    return best


def _check(args: argparse.Namespace, folder: Path) -> None:
    saved = json.loads((folder / f"選んだもの-{args.family}.json").read_text(encoding="utf-8"))
    chosen = {ticket: int(shape) for ticket, shape in saved["shapes"].items()}
    rule = TopValueRule(saved["rule"]["k"], saved["rule"]["line"])
    marked = pd.read_pickle(folder / "印.pkl")
    counts_all = pd.read_pickle(folder / "数え上げ.pkl")
    races = marked.drop_duplicates("race_id").set_index("race_id")[[RACE_GRADE, GRADE]]
    lines = [f"# 5回目 {args.name}（形の範囲: {args.family}）: 確かめ", ""]
    for label, years in (("前半の年（選んだ年）", SELECT_YEARS), ("後半の年（確かめる年）", CONFIRM_YEARS)):
        counts = _years(counts_all, years)
        days = sorted(counts["race_date"].unique())
        lines += [f"## {label} {years[0]}〜{years[-1]}年・重賞 {counts['race_id'].nunique()}レース", "",
                  "| 券種 | 形 | 買った重賞 | 当たった重賞 | 平均点数 | 回収率 | 90% の幅の下の端 | 100% を超えた年 |", "|---|---|---|---|---|---|---|---|"]
        for ticket in TICKETS:
            if ticket not in chosen:
                continue
            picked = counts[(counts[SHAPE] == chosen[ticket]) & (counts[POINTS] > 0)]
            lines.append(_line(ticket, ALL_SHAPES[chosen[ticket]].name, picked, days))
        for shape in CURRENT_RULE_SHAPES:
            index = len(SHAPES) + CURRENT_RULE_SHAPES.index(shape)
            picked = counts[(counts[SHAPE] == index) & (counts[POINTS] > 0)]
            lines.append(_line(f"今の印の買い目 {shape.ticket}", shape.name, picked, days))
        picked = rule.pick(counts, chosen)
        lines += ["", f"レースごとの券種の選び方: {rule.name}", "", "| 区分 | 重賞 | 回収率 | 下の端 | 的中率 |", "|---|---|---|---|---|"]
        lines.append(_rule_line("全体", picked, counts, days))
        for year in years:
            year_picked, year_counts = _years(picked, range(year, year + 1)), _years(counts, range(year, year + 1))
            if len(year_counts):
                lines.append(_rule_line(f"{year}年", year_picked, year_counts, sorted(year_counts["race_date"].unique())))
        for column, values in ((RACE_GRADE, ("G1", "G2", "G3")), (GRADE, ("S", "A", "B", "C", "見送り"))):
            for value in values:
                ids = races.index[races[column] == value]
                sub_counts = counts[counts["race_id"].isin(ids)]
                if len(sub_counts):
                    lines.append(_rule_line(value, picked[picked["race_id"].isin(ids)], sub_counts, sorted(sub_counts["race_date"].unique())))
        lines += ["", "選ばれた券種の回数: " + "・".join(f"{ticket} {count}" for ticket, count in picked["ticket"].value_counts().items()), ""]
    (folder / f"確かめ-{args.family}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _plan(args: argparse.Namespace, folder: Path) -> None:
    """決めておいた買い方（``PLANS``）を、全部の重賞で年ごとに数える（どの重賞も、その券種を全部買う）。"""
    counts = pd.read_pickle(folder / "数え上げ.pkl")
    lines = [f"# 5回目 {args.name}: 決めておいた買い方", ""]
    for plan, shapes in PLANS.items():
        indices = [ALL_SHAPES.index(shape) for shape in shapes]
        picked = counts[counts[SHAPE].isin(indices) & (counts[POINTS] > 0)].assign(ticket=lambda frame: frame[SHAPE].map(lambda index: ALL_SHAPES[index].ticket))
        days = sorted(counts["race_date"].unique())
        lines += [f"## {plan}: " + "・".join(f"{shape.ticket} {shape.name}" for shape in shapes), "",
                  "| 区分 | 重賞 | 回収率 | 下の端 | 的中率 |", "|---|---|---|---|---|", _rule_line("全体", picked, counts, days)]
        for year in sorted(counts["race_date"].dt.year.unique()):
            year_counts = _years(counts, range(year, year + 1))
            lines.append(_rule_line(f"{year}年", _years(picked, range(year, year + 1)), year_counts, sorted(year_counts["race_date"].unique())))
        lines += ["", "| 券種 | 形 | 買った重賞 | 当たった重賞 | 平均点数 | 回収率 | 下の端 | 100% を超えた年 |", "|---|---|---|---|---|---|---|---|"]
        lines += [_line(shape.ticket, shape.name, picked[picked[SHAPE] == index], days) for shape, index in zip(shapes, indices)]
        lines.append("")
    (folder / "決めておいた買い方.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _line(ticket: str, name: str, picked: pd.DataFrame, days: list) -> str:
    stake, payback = _by_day(picked, days)
    lower = float(RecoveryBootstrap(len(days)).lower(stake[None, :], payback[None, :])[0]) if stake.sum() else np.nan
    years = picked.assign(year=picked["race_date"].dt.year).groupby("year").apply(
        lambda group: group[RETURN].sum() / (group[POINTS].sum() * UNIT), include_groups=False)
    over = f"{int((years > 1).sum())}/{len(years)}"
    rate = payback.sum() / stake.sum() if stake.sum() else np.nan
    return (f"| {ticket} | {name} | {len(picked)} | {int((picked[RETURN] > 0).sum())} | {picked[POINTS].mean():.1f} | "
            f"{rate:.1%} | {lower:.1%} | {over} |")


def _rule_line(label: str, picked: pd.DataFrame, counts: pd.DataFrame, days: list) -> str:
    stake, payback = _by_day(picked, days)
    lower = float(RecoveryBootstrap(len(days)).lower(stake[None, :], payback[None, :])[0]) if stake.sum() else np.nan
    races = counts["race_id"].nunique()
    hits = picked.groupby("race_id")[RETURN].sum().gt(0).sum()
    rate = payback.sum() / stake.sum() if stake.sum() else np.nan
    return f"| {label} | {races} | {rate:.1%} | {lower:.1%} | {hits / races:.1%} |"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="重賞の買い方 5回目", allow_abbrev=False)
    parser.add_argument("command", choices=("mark", "count", "search", "check", "plan"))
    parser.add_argument("--name", required=True, help="結果の置き場所の名前（reports/重賞の買い方/5回目/<名前>/）")
    parser.add_argument("--top3", help="mark: 3着以内の予測（<表>/<作り方>）")
    parser.add_argument("--win", help="mark: 1着の予測（<表>/<作り方>）")
    parser.add_argument("--family", choices=tuple(FAMILIES), default="印",
                        help="search・check で形を選ぶ範囲（印: 設計書の印の形だけ。全部: 組の期待値の高い順に買う形も入れる）")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
