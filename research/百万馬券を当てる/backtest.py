"""手順4・7 と docs/06: レース選びと、荒れる前提の予想の買い目を確かめる（研究「百万馬券を当てる」の入口③）。

    uv run python research/百万馬券を当てる/backtest.py races    # 手順4: 1日1レース選んだとき、帯がどれだけ集まったか
    uv run python research/百万馬券を当てる/backtest.py horses   # 手順7の前半: 荒れたレースで、予想の上位の馬が来たか（今の予想と比べる）
    uv run python research/百万馬券を当てる/backtest.py bets     # 手順7: 選んだレースで、甲・乙・丙を1レース1万円で買ったとき
    uv run python research/百万馬券を当てる/backtest.py select   # docs/06 の 2: 同じレース数を選んだとき、実際に 1,000倍以上だった割合（点数ごと）
    uv run python research/百万馬券を当てる/backtest.py flat     # docs/06 の 3: 線以上のレースを全部買い、一律の買い方で 1,000倍以上の組を買ったとき

先に walk.py の race・big・baseline・horses を回しておく。races・horses・bets は、まだ見ていない 2021〜2022年で確かめ、2023〜2026年を参考として並べる。
select・flat は 2021〜2026年の全部で数え、2021〜2022年と 2023〜2026年にも分けて並べる。
bets・flat は元DB から選んだレースの3連単（bets は3連複も）の確定オッズを読む（初回は数分。``cache/`` にとっておく）。
出るもの（Git 対象外）: ``reports/百万馬券を当てる/レース選びの結果.md``・``来る馬の予想の結果.md``・``買い目の結果.md``・``買い目/<買い方>.csv``・
``レース選びの精度.md``・``一律の買い目の結果.md``・``一律の買い目/<買い方>.csv``。
"""

from __future__ import annotations

import argparse
import pickle
import sys
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.shared.betting import TicketType  # noqa: E402
from yosou.shared.dataset import RACE_DATE, RACE_ID  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.upset_premise.betting import FLAT_STAKE_CHOICES, FlatPlan, FormationPlan, ObiStakePlan, TicketPlan  # noqa: E402

from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402
from 百万馬券を当てる.analysis.betting_summary import BettingSummary  # noqa: E402
from 百万馬券を当てる.analysis.big_chance_table import BigChanceTable  # noqa: E402
from 百万馬券を当てる.analysis.big_combo_odds import BigComboOdds  # noqa: E402
from 百万馬券を当てる.analysis.day_race_picker import DayRacePicker  # noqa: E402
from 百万馬券を当てる.analysis.finish_loader import FinishLoader  # noqa: E402
from 百万馬券を当てる.analysis.flat_hit_summary import FlatHitSummary  # noqa: E402
from 百万馬券を当てる.analysis.obi_rules import BIG, CHECK_YEARS, OBI, REFERENCE_FIRST_YEAR  # noqa: E402
from 百万馬券を当てる.analysis.plain_flat_plan import PlainFlatPlan  # noqa: E402
from 百万馬券を当てる.analysis.prediction_coverage import PredictionCoverage  # noqa: E402
from 百万馬券を当てる.analysis.race_frame import PAYOUT_CLASS, YEAR, race_frame  # noqa: E402
from 百万馬券を当てる.analysis.race_horses_builder import RaceHorsesBuilder  # noqa: E402
from 百万馬券を当てる.analysis.race_selection_scores import (  # noqa: E402
    BASELINE,
    BIG_BASELINE,
    BLEND,
    RULE,
    RaceSelectionScores,
    big_model_column,
    model_column,
)
from 百万馬券を当てる.analysis.race_table_loader import RaceTableLoader  # noqa: E402
from 百万馬券を当てる.analysis.selected_combo_odds import SelectedComboOdds  # noqa: E402
from 百万馬券を当てる.analysis.selection_precision import SelectionPrecision  # noqa: E402
from 百万馬券を当てる.analysis.selection_summary import SelectionSummary  # noqa: E402
from 百万馬券を当てる.analysis.ticket_maker import TicketMaker  # noqa: E402
from 百万馬券を当てる.analysis.ticket_settler import TicketSettler  # noqa: E402
from 百万馬券を当てる.analysis.winning_combos import trifecta_winners, trio_winners  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
DEFAULT_ROOT = _REPORTS / "百万馬券を当てる"
DEFAULT_HORSE_TABLES = _REPORTS / "既存モデルの改善" / "tables"
#: 今の予想（本番の当日の 3着以内と1着）を 2021年から区切りごとに学んだ予測（研究「複勝以外の回収率100超」の入口③）。
CURRENT_PREDICTIONS = _REPORTS / "複勝以外の回収率100超" / "predictions-2021から"
#: 比べるレースの選び方（点数の列）。
SELECTIONS: tuple[str, ...] = (*(model_column(timing) for timing in PredictionTiming), BASELINE, RULE)
#: 第3段で使うレースの選び方（手順4で採用したもの。docs/04 の 1）。新しく作った帯になる確率のモデルは、確かめの期間で
#: 比べる目安を上回らなかった（同じだった）ので採用せず、条件を満たした比べる目安（今の荒れ具合の予想）を使う。
DEFAULT_SELECTION = BASELINE
#: 予想の名前 → （1着の予測, 3着以内の予測）の置き場所（予想の名前, 作り方）。
FORECASTS: dict[str, tuple[tuple[str, str], tuple[str, str]]] = {
    "荒れる前提の予想": (("dscore_finish_race_day", "wild-win-race_day"), ("dscore_race_day", "wild-top3-race_day")),
    "今の予想": (("dscore_finish_race_day", "win-race_day"), ("dscore_race_day", "top3-race_day")),
}
#: 着順を読む馬ごとの表。
FINISH_TABLE = "dscore_race_day"
#: 「荒れる」と決める線の既定（本番の道具「帯狙い」と同じ。docs/06 の 4）。
DEFAULT_LINE = 0.40
#: select で並べる点数の列。
SELECTION_COLUMNS: tuple[str, ...] = (BASELINE, BIG_BASELINE, BLEND, *(big_model_column(timing) for timing in PredictionTiming),
                                      *(model_column(timing) for timing in PredictionTiming), RULE)
#: flat でレースを選ぶ点数（--score）。
FLAT_SCORES: dict[str, str] = {"平均": BLEND, "大荒れ＋超荒れ": BIG_BASELINE}
#: flat で比べる組の確率の付け方の名前。
ADOPTED, PLAIN, USUAL_ONLY = ("採用（1着は荒れる前提・2着3着は両方の3着以内の平均）", "元の Harville（荒れる前提の1着だけ）",
                             "今の予想だけ（1着は今の1着・2着3着は今の3着以内）")


def main() -> None:
    args = _parser().parse_args()
    {"races": _races, "horses": _horses, "bets": _bets, "select": _select, "flat": _flat}[args.step](args)


def _split_years(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """2021〜2026年の全部と、まだ見ていなかった 2021〜2022年・参考の 2023〜2026年。"""
    return {"2021〜2026年": frame, **_periods(frame)}


def _select(args: argparse.Namespace) -> None:
    scored = _scored(args, with_chance=True)
    scored = scored[scored[YEAR].ge(min(CHECK_YEARS))]
    precision = SelectionPrecision()
    lines = ["# レース選びの精度", "",
             "点数の高い順に「1開催日あたり n レース」ぶん選んだとき、実際に3連単が 1,000倍以上で決まった割合（docs/06 の 2）。",
             "選ぶ数を同じにして比べる。AUC は点数の並べ方の良さ（1 なら 1,000倍以上のレースを全部上に並べられている）。",
             "JV-Data 由来の値を含むため Git の対象外。", ""]
    for period, frame in _split_years(scored).items():
        wild = int(frame[PAYOUT_CLASS].isin([OBI, BIG]).sum())
        lines += [f"## {period}（{len(frame)}レース・うち 1,000倍以上 {wild}・開催日 {frame[RACE_DATE].nunique()}）", "",
                  precision.table(frame, list(SELECTION_COLUMNS)).to_markdown(index=False), ""]
    _write(args.root / "レース選びの精度.md", lines)


def _flat(args: argparse.Namespace) -> None:
    score = FLAT_SCORES[args.score]
    scored = _scored(args, with_chance=score == BLEND)
    picked = scored[scored[YEAR].ge(min(CHECK_YEARS)) & scored[score].ge(args.line)]
    odds = {True: _big_odds(args, picked)}
    finishes = FinishLoader(args.horse_tables, FINISH_TABLE).finishes(picked[RACE_ID])
    winners = {race: trifecta_winners(found) for race, found in finishes.items()}
    horses = {name: builder.build(picked[RACE_ID]) for name, builder in _flat_builders(args).items()}
    settled = {(name, plan.name): TicketSettler().settle(TicketMaker(plan, f"{plan.name}・{name}").make(picked, horses[name], odds), winners)
               for name, plan in _flat_plans()}
    _write_tickets(args.root / "一律の買い目", settled)
    hits, summary = FlatHitSummary(), BettingSummary()
    lines = ["# 一律の買い目の結果（1レース 1万円）", "",
             f"レースの選び方: {score} が {args.line} 以上のレースを全部（1日何レースでも）。オッズは確定オッズ。",
             "買い方: 1,000倍以上の3連単の組を、組の確率の高い順に、一律の金額で予算ぶん買う（docs/06 の 3）。",
             "JV-Data 由来の値を含むため Git の対象外。", ""]
    for period, frame in _split_years(picked).items():
        years = frame[YEAR].nunique()
        lines += [f"## {period}（{len(frame)}レースを選んだ）", ""]
        rows = []
        for (name, plan), tickets in settled.items():
            part = tickets[tickets[RACE_ID].isin(frame[RACE_ID])]
            betting = summary.row(part, years)
            rows.append({"組の確率": name, "買い方": plan, **hits.row(part, frame),
                         **{key: betting.get(key) for key in ("回収率", "90%の幅（下）", "90%の幅（上）", "いちばん大きい当たりを除いた回収率",
                                                            "いちばん深い落ち込み", "最大の連敗", "1年の投資")}})
        lines += [pd.DataFrame(rows).to_markdown(index=False), ""]
    _write(args.root / "一律の買い目の結果.md", lines)


def _flat_builders(args: argparse.Namespace) -> dict[str, RaceHorsesBuilder]:
    """組の確率の付け方ごとの、出走馬の予想の作り方。"""
    wild, usual = FORECASTS["荒れる前提の予想"], FORECASTS["今の予想"]
    store, usual_store = PredictionStore(args.root / "predictions"), PredictionStore(CURRENT_PREDICTIONS)
    wild_win, wild_top3 = store.read(*wild[0]), store.read(*wild[1])
    usual_win, usual_top3 = usual_store.read(*usual[0]), usual_store.read(*usual[1])
    return {ADOPTED: RaceHorsesBuilder(wild_win, wild_top3, usual_top3), PLAIN: RaceHorsesBuilder(wild_win, wild_top3),
            USUAL_ONLY: RaceHorsesBuilder(usual_win, usual_top3)}


def _flat_plans() -> list[tuple[str, TicketPlan]]:
    """（組の確率の付け方, 買い方）の並び。元の Harville は ``PlainFlatPlan``、ほかは本番の ``FlatPlan``。"""
    pairs: list[tuple[str, TicketPlan]] = []
    for stake in FLAT_STAKE_CHOICES:
        pairs += [(ADOPTED, FlatPlan(stake)), (PLAIN, PlainFlatPlan(stake)), (USUAL_ONLY, FlatPlan(stake))]
    return pairs


def _big_odds(args: argparse.Namespace, picked: pd.DataFrame) -> BigComboOdds:
    """選んだレースの 1,000倍以上の3連単の確定オッズ。同じ線の2回目からは ``cache/`` から読む。"""
    cache = args.root / "cache" / f"1000倍以上の組-{args.score}-線{args.line}.pkl"
    if cache.exists():
        table = pd.read_pickle(cache)
        if set(picked[RACE_ID]) <= set(table[RACE_ID]):
            return BigComboOdds(table)
    with db.open_db(args.db) as con:
        found = BigComboOdds.read(con, picked)
    cache.parent.mkdir(parents=True, exist_ok=True)
    found.table.to_pickle(cache)
    return found


def _periods(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {"確かめ（2021〜2022年）": frame[frame[YEAR].isin(CHECK_YEARS)],
            "参考（2023〜2026年）": frame[frame[YEAR].ge(REFERENCE_FIRST_YEAR)]}


def _scored(args: argparse.Namespace, with_chance: bool = False) -> pd.DataFrame:
    races = race_frame(RaceTableLoader(args.root / "tables").read())
    chance = _chance(args, races[races[YEAR].ge(min(CHECK_YEARS))]) if with_chance else None
    return RaceSelectionScores(PredictionStore(args.root / "predictions"), chance).scores(races)


def _chance(args: argparse.Namespace, races: pd.DataFrame) -> pd.Series:
    """2021年からの全レースの、予想が見た 1,000倍以上になる確率。2回目からは ``cache/`` から読む（初回は元DB から数分）。"""
    cache = args.root / "cache" / "予想が見た1000倍以上になる確率.pkl"
    if cache.exists():
        saved = pd.read_pickle(cache)
        if set(races[RACE_ID]) <= set(saved.index):
            return saved
    (win_model, win_key), (top3_model, top3_key) = FORECASTS["今の予想"]
    store = PredictionStore(CURRENT_PREDICTIONS)
    builder = RaceHorsesBuilder(store.read(win_model, win_key), store.read(top3_model, top3_key))
    with db.open_db(args.db) as con:
        found = BigChanceTable(builder).build(con, races)
    cache.parent.mkdir(parents=True, exist_ok=True)
    found.to_pickle(cache)
    return found


def _races(args: argparse.Namespace) -> None:
    summary = SelectionSummary()
    lines = ["# レース選びの結果", "",
             "開催日ごとに、点数がいちばん高いレースを1つ選んだとき。帯の集まり方 = 選んだレースの帯の割合 ÷ 全レースの帯の割合（90% の幅は開催日のブートストラップ）。",
             "採用の条件（docs/01 の 8）: 確かめの期間で帯の集まり方が 2倍以上・90% の幅の下の端が 1倍超え・比べる目安より高い。",
             "JV-Data 由来の値を含むため Git の対象外。", ""]
    for period, frame in _periods(_scored(args)).items():
        rows = [{"選び方": column, **summary.row(DayRacePicker(column).pick(frame), frame)}
                for column in SELECTIONS if column in frame.columns and frame[column].notna().any()]
        lines += [f"## {period}", "", pd.DataFrame(rows).to_markdown(index=False), ""]
    _write(args.root / "レース選びの結果.md", lines)


def _horses(args: argparse.Namespace) -> None:
    scored = _scored(args)
    loader = FinishLoader(args.horse_tables, FINISH_TABLE)
    forecasts = {name: _builder(args, name) for name in FORECASTS}
    coverage = PredictionCoverage()
    lines = ["# 来る馬の予想の結果", "",
             "荒れたレース（3連単の払戻が 10万円以上）と、第1段で選んだレースで、予想の上位の馬が実際に1〜3着に来たか。人気薄 = 6番人気以下。",
             "採用の条件（docs/01 の 8）: 確かめの期間の荒れたレースで、上位の馬が1〜3着に来た割合が今の予想より高い。",
             "JV-Data 由来の値を含むため Git の対象外。", ""]
    for period, frame in _periods(scored).items():
        groups = {"荒れたレース": frame[frame[PAYOUT_CLASS].isin([OBI, BIG])], "帯のレース": frame[frame[PAYOUT_CLASS].eq(OBI)],
                  "選んだレース": DayRacePicker(args.selection).pick(frame), "全レース": frame}
        rows = [{"対象": group, "予想": name, **coverage.row(builder.build(races[RACE_ID]), loader.finishes(races[RACE_ID]),
                                                         loader.popularity(races[RACE_ID]))}
                for (group, races), (name, builder) in product(groups.items(), forecasts.items())]
        lines += [f"## {period}", "", pd.DataFrame(rows).to_markdown(index=False), ""]
    _write(args.root / "来る馬の予想の結果.md", lines)


def _bets(args: argparse.Namespace) -> None:
    scored = _scored(args)
    picked = DayRacePicker(args.selection).pick(scored[scored[YEAR].ge(min(CHECK_YEARS))])
    odds = _odds(args, picked)
    loader = FinishLoader(args.horse_tables, FINISH_TABLE)
    finishes = loader.finishes(picked[RACE_ID])
    winners = {True: {race: trifecta_winners(found) for race, found in finishes.items()},
               False: {race: trio_winners(found) for race, found in finishes.items()}}
    plans = (ObiStakePlan(ordered=True), FormationPlan(), ObiStakePlan(ordered=False))
    settled = {(name, plan.name): TicketSettler().settle(
        TicketMaker(plan, f"{plan.name}・{name}").make(picked, _builder(args, name).build(picked[RACE_ID]), odds), winners[plan.ordered])
        for name, plan in product(FORECASTS, plans)}
    _write_tickets(args.root / "買い目", settled)
    summary = BettingSummary()
    lines = ["# 買い目の結果（1レース 1万円）", "",
             f"レースの選び方: {args.selection}（開催日ごとに1レース）。オッズは確定オッズ。",
             "採用の条件（docs/01 の 8）: 勝負用 = 回収率と 90% の幅の下の端が 100% 超え。帯狙いの財布 = 確かめの2年で帯が1回以上、いちばん大きい当たりを除いた回収率が 80% 以上。",
             "JV-Data 由来の値を含むため Git の対象外。", ""]
    for period, frame in _periods(picked).items():
        years = frame[YEAR].nunique()
        lines += [f"## {period}（{len(frame)}レースを選んだ。うち帯 {int(frame[PAYOUT_CLASS].eq(OBI).sum())}レース）", ""]
        rows = [{"予想": name, "買い方": plan, **summary.row(tickets[tickets[RACE_ID].isin(frame[RACE_ID])], years)}
                for (name, plan), tickets in settled.items()]
        lines += [pd.DataFrame(rows).to_markdown(index=False), ""]
    _write(args.root / "買い目の結果.md", lines)


def _builder(args: argparse.Namespace, name: str) -> RaceHorsesBuilder:
    (win_model, win_key), (top3_model, top3_key) = FORECASTS[name]
    store = PredictionStore(args.root / "predictions" if name != "今の予想" else CURRENT_PREDICTIONS)
    return RaceHorsesBuilder(store.read(win_model, win_key), store.read(top3_model, top3_key))


def _odds(args: argparse.Namespace, picked: pd.DataFrame) -> dict[bool, dict[str, dict[tuple[int, ...], float]]]:
    """選んだレースの3連単（真）・3連複（偽）の確定オッズ。同じ選び方の2回目からは ``cache/`` から読む。"""
    cache = args.root / "cache" / f"オッズ-{args.selection}.pkl"
    saved = pickle.loads(cache.read_bytes()) if cache.exists() else None
    if saved is not None and set(picked[RACE_ID]) <= set(saved[True]):
        return saved
    with db.open_db(args.db) as con:
        reader = SelectedComboOdds(con)
        found = {True: reader.read(TicketType.TRIFECTA, picked), False: reader.read(TicketType.TRIO, picked)}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(found))
    return found


def _write_tickets(folder: Path, settled: dict[tuple[str, str], pd.DataFrame]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for (name, plan), tickets in settled.items():
        tickets.assign(**{RACE_DATE: tickets[RACE_DATE].dt.strftime("%Y-%m-%d")}).to_csv(
            folder / f"{plan}・{name}.csv", index=False, encoding="utf-8-sig")


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"書き出しました: {path}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="レース選びと、荒れる前提の予想の買い目を確かめる", allow_abbrev=False)
    parser.add_argument("step", choices=("races", "horses", "bets", "select", "flat"),
                        help="races（手順4）・horses（手順7の前半）・bets（手順7）・select（docs/06 の 2）・flat（docs/06 の 3）")
    parser.add_argument("--line", type=float, default=DEFAULT_LINE, help=f"flat で「荒れる」と決める線（既定: {DEFAULT_LINE}）")
    parser.add_argument("--score", choices=tuple(FLAT_SCORES), default="平均",
                        help="flat でレースを選ぶ点数（平均: 本番と同じ大荒れ＋超荒れと予想が見た確率の平均 / 大荒れ＋超荒れ。既定: 平均）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="この研究の置き場所（tables/ と predictions/）")
    parser.add_argument("--horse-tables", type=Path, default=DEFAULT_HORSE_TABLES, help="馬ごとの表の置き場所（着順を読む）")
    parser.add_argument("--selection", default=DEFAULT_SELECTION, choices=SELECTIONS, help="第3段で使うレースの選び方")
    parser.add_argument("--db", default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb）")
    return parser


if __name__ == "__main__":
    main()
