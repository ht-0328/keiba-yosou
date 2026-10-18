"""手順5: 組の期待値で組を選ぶ買い方（ワイド・馬連・馬単・3連複・3連単）を作って確かめる（研究「複勝以外の回収率100超」の入口④。docs/04）。

    uv run python research/複勝以外の回収率100超/combo_value.py mark --from-year 2019   # 2019年からの当日の予測に印を付ける（15分ほど）
    uv run python research/複勝以外の回収率100超/combo_value.py fit                     # 2023〜2026年で、券種ごとの組の確率の重みを推定する
    uv run python research/複勝以外の回収率100超/combo_value.py grid                    # 2023〜2026年で、線 × 上限 × 対象を数える（選ぶ）
    uv run python research/複勝以外の回収率100超/combo_value.py check                   # 道具「印の成績」の買い目から、期間ごとの成績と運用の目安を出す
    uv run python research/複勝以外の回収率100超/combo_value.py fold-weights --from-year 2015   # 手順6: 区切りごとに、検証期間で重みを推定する（比べた案）
    uv run python research/複勝以外の回収率100超/combo_value.py rolling --from-year 2015        # 手順6: 区切りごとに、直前1年のテスト期間で重みを推定する（3時間ほど）
    uv run python research/複勝以外の回収率100超/combo_value.py rolling --latest-only --save-models   # 本番の重み（いちばん新しい1年。ワイド・3連複・3連単）

``mark`` は ``early_years.py combine`` が作った予測（``predictions-2019から/`` か ``predictions-2021から/``）に、道具「印の成績」と同じ決め方で印を付け、
``組の期待値/marked-<年>から.parquet`` に書く。``fit`` と ``grid`` は、その表と元DB の確定オッズの板・払戻の明細から、本番と同じ部品（``yosou.shared.combo_value``）で
組の表を月ごとに作る（3連単は組が多いので、レースID を 3 で割った余りが 0 のレースだけ）。``fit`` は重みを ``組の期待値/combo_blend.json`` に書く
（``--save-models`` で本番のモデルの置き場所にも書く）。``check`` は、道具「印の成績」を 2019年からの予測で回した買い目の CSV
（``印の成績-2019から/買い目/``）から数える。出るものは全部 Git 対象外の ``reports/複勝以外の回収率100超/組の期待値/``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.shared.betting import TicketType  # noqa: E402
from yosou.shared.combo_value import ComboBlend, ComboBlendFitter  # noqa: E402
from yosou.shared.repository import ComboBlendWeightsRepository  # noqa: E402

from 今週の予想.model_folders import DEFAULT_MODELS  # noqa: E402
from 今週の予想.ticket_rules import COMBO_VALUE_RULES  # noqa: E402
from 今週の予想.wallet import COMBO_WALLET, POINT_RATE  # noqa: E402
from 複勝以外の回収率100超.analysis.backtest_marking import BacktestMarking  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_month_frames import ComboMonthFrames  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_operation_report import ComboOperationReport  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_period_report import PERIODS, PERIODS_STEP6, ComboPeriodReport  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_rule_grid import ComboRuleGrid  # noqa: E402
from 複勝以外の回収率100超.analysis.fold_weights_file import FoldWeightsFile  # noqa: E402
from 複勝以外の回収率100超.analysis.validation_horses import ValidationHorses  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
ROOT = _REPORTS / "複勝以外の回収率100超"
OUT = ROOT / "組の期待値"
#: 重みと線を決める開発の期間（今の本番の7つの区切りのテスト期間）。
DEV_YEARS = (2023, 2026)
#: 券種（docs/04 の順）。3連単は組の表を軽くするため、3つに1つのレースだけ使う。
TICKET_TYPES = (TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA, TicketType.TRIO, TicketType.TRIFECTA)
SAMPLE = {TicketType.TRIFECTA: 3}
#: 直前1年の重みを使う券種（docs/05。馬単は 2023〜2026年で推定した重みのまま）と、これからのレースに使う重みの区切りの名前。
ROLLING_TYPES = tuple(rule.ticket_type for rule in COMBO_VALUE_RULES if rule.rolling)
NEXT = "これから"
#: 実際に買う買い方と、1点の重み（組の期待値用の財布の券種ごとの割合の比。馬単を 1 にする）。手順5 のときは 馬連 1・馬単 2 だった。
OPERATION_WEIGHTS = {f"{label}（組の期待値）": rate / POINT_RATE[COMBO_WALLET]["馬単"] for label, rate in POINT_RATE[COMBO_WALLET].items()}


def main() -> None:
    args = _parser().parse_args()
    {"mark": _mark, "fit": _fit, "grid": _grid, "check": _check, "fold-weights": _fold_weights, "rolling": _rolling}[args.step](args)


def _rolling(args: argparse.Namespace) -> None:
    """区切りごとに、直前の2つの区切り（1年）のテスト期間の組の表で重みを推定する（docs/05 の 2）。``--latest-only`` は、
    いちばん新しい2つの区切りだけで、これからのレースに使う重み（本番の重み）を推定する。``--save-models`` で、
    直前1年の重みを使う券種（``ROLLING_TYPES``）の重みを本番のモデルの置き場所の combo_blend.json に書く（ほかの券種の重みは残す）。"""
    marked = pd.read_parquet(OUT / f"marked-{args.from_year}から.parquet")
    folds = list(marked.groupby("fold")["race_date"].min().sort_values().index)
    wanted = folds[-2:] if args.latest_only else folds
    frames: dict[str, dict[TicketType, pd.DataFrame]] = {}
    with db.open_db(args.db) as con:
        builder = ComboMonthFrames(con, SAMPLE)
        for fold in wanted:
            rows = marked[marked["fold"] == fold]
            parts: dict[TicketType, list[pd.DataFrame]] = {ticket_type: [] for ticket_type in TICKET_TYPES}
            for _, month in rows.groupby(pd.to_datetime(rows["race_date"]).dt.to_period("M"), sort=True):
                for ticket_type, frame in builder.build(month, TICKET_TYPES).items():
                    parts[ticket_type].append(frame)
            frames[fold] = {ticket_type: pd.concat(part, ignore_index=True) for ticket_type, part in parts.items()}
            print(f"組の表: {fold}", file=sys.stderr, flush=True)
    store = FoldWeightsFile(OUT / f"rolling_weights-{args.from_year}から-入口.json")
    targets = [*wanted[2:], NEXT] if not args.latest_only else [NEXT]
    for at, fold in enumerate(targets):
        before = wanted[at:at + 2]
        weights = {ticket_type: ComboBlendFitter().fit(pd.concat([frames[name][ticket_type] for name in before], ignore_index=True))
                   for ticket_type in TICKET_TYPES}
        store.save(fold, weights)
        print(f"{fold}（{'・'.join(before)} で推定）: " + "・".join(f"{t.label} 比 {w.ratio:.2f}" for t, w in weights.items()), flush=True)
    if args.save_models:
        latest = store.load()[NEXT]
        current = ComboBlendWeightsRepository(DEFAULT_MODELS).load()
        merged = {**current, **{ticket_type: latest[ticket_type] for ticket_type in ROLLING_TYPES}}
        print(ComboBlendWeightsRepository(DEFAULT_MODELS).save(merged), flush=True)


def _fold_weights(args: argparse.Namespace) -> None:
    """区切りごとに、その区切りのモデルの検証期間（テストの直前の半年）の組の表で、券種ごとの重みを推定する（docs/05 の 2）。"""
    store = FoldWeightsFile(OUT / f"fold_weights-{args.from_year}から.json")
    with db.open_db(args.db) as con:
        horses = ValidationHorses(ROOT / f"predictions-{args.from_year}から").by_fold(con)
        frames = ComboMonthFrames(con, SAMPLE)
        for fold, rows in horses.items():
            if store.has(fold) and not args.force:
                print(f"{fold}: 済んでいるので飛ばします", flush=True)
                continue
            parts: dict[TicketType, list[pd.DataFrame]] = {ticket_type: [] for ticket_type in TICKET_TYPES}
            for _, month in rows.groupby(pd.to_datetime(rows["race_date"]).dt.to_period("M"), sort=True):
                for ticket_type, frame in frames.build(month, TICKET_TYPES).items():
                    parts[ticket_type].append(frame)
            weights = {ticket_type: ComboBlendFitter().fit(pd.concat(frames_of, ignore_index=True)) for ticket_type, frames_of in parts.items()}
            store.save(fold, weights)
            print(f"{fold}: " + "・".join(f"{t.label} 比 {w.ratio:.2f}" for t, w in weights.items()), flush=True)


def _mark(args: argparse.Namespace) -> None:
    with db.open_db(args.db) as con:
        marked = BacktestMarking(ROOT / f"predictions-{args.from_year}から", DEFAULT_MODELS).mark(con)
    path = OUT / f"marked-{args.from_year}から.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    marked.to_parquet(path)
    print(f"{len(marked):,}頭・{marked['race_id'].nunique():,}レース → {path}", flush=True)


def _dev_frames(args: argparse.Namespace) -> dict[TicketType, pd.DataFrame]:
    """開発の期間の、券種ごとの組の表（月ごとに作ってつなぐ）。"""
    marked = pd.read_parquet(OUT / f"marked-{args.from_year}から.parquet")
    years = pd.to_datetime(marked["race_date"]).dt.year
    marked = marked[years.between(*DEV_YEARS)]
    parts: dict[TicketType, list[pd.DataFrame]] = {ticket_type: [] for ticket_type in TICKET_TYPES}
    with db.open_db(args.db) as con:
        frames = ComboMonthFrames(con, SAMPLE)
        for month, group in marked.groupby(pd.to_datetime(marked["race_date"]).dt.to_period("M"), sort=True):
            print(f"組の表: {month}", file=sys.stderr, flush=True)
            for ticket_type, frame in frames.build(group, TICKET_TYPES).items():
                parts[ticket_type].append(frame)
    return {ticket_type: pd.concat(frames_of, ignore_index=True) for ticket_type, frames_of in parts.items()}


def _fit(args: argparse.Namespace) -> None:
    frames = _dev_frames(args)
    weights = {ticket_type: ComboBlendFitter().fit(frame) for ticket_type, frame in frames.items()}
    for ticket_type, value in weights.items():
        print(f"{ticket_type.label}: {value}", flush=True)
    print(ComboBlendWeightsRepository(OUT).save(weights), flush=True)
    if args.save_models:
        print(ComboBlendWeightsRepository(DEFAULT_MODELS).save(weights), flush=True)


def _grid(args: argparse.Namespace) -> None:
    weights = ComboBlendWeightsRepository(OUT).load()
    lines = []
    for ticket_type, frame in _dev_frames(args).items():
        valued = ComboBlend().of(ticket_type, frame, weights[ticket_type])
        table = ComboRuleGrid().table(ticket_type, valued)
        lines += [f"\n## {ticket_type.label}\n", table.head(args.top).to_markdown(index=False)]
    _write(OUT / "線と上限の選び方.md", "# 線・オッズの上限・対象の選び方（2023〜2026年だけ。幅の下の端の高い順）\n" + "\n".join(lines))


def _check(args: argparse.Namespace) -> None:
    path = args.tickets or ROOT / f"印の成績-{args.from_year}から" / "買い目" / "dscore_race_day_top3-race_day.csv"
    tickets = pd.read_csv(path, dtype={"レースID": str, "組番": str})
    labels = tuple(rule.label for rule in COMBO_VALUE_RULES)
    step6 = args.from_year == "2015"
    periods, yearly = ComboPeriodReport(PERIODS_STEP6 if step6 else PERIODS).tables(tickets, labels)
    dates = pd.to_datetime(pd.read_parquet(OUT / f"marked-{args.from_year}から.parquet", columns=["race_date"])["race_date"])
    days = dates[dates.dt.year >= (2016 if step6 else 2019)].nunique()
    tickets = tickets[pd.to_datetime(tickets["開催日"]).dt.year >= (2016 if step6 else 2019)]
    report = ComboOperationReport()
    text = ["# 組の期待値の買い方の成績（当日の予想・確定オッズ・1点 100円）\n", periods.to_markdown(index=False),
            "\n\n## 年ごとの回収率（%）\n", yearly.to_markdown(),
            f"\n\n## 運用の目安（馬単の1点 = 100円。ほかの券種は財布の割合の比で小さくした額）\n", *report.lines(tickets, OPERATION_WEIGHTS, days), "",
            report.yearly(tickets, OPERATION_WEIGHTS).to_markdown()]
    _write(OUT / ("確かめの結果-手順6.md" if step6 else "確かめの結果.md"), "\n".join(text))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    print(text, flush=True)
    print(f"\n保存先: {path}", file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="組の期待値で組を選ぶ買い方を作って確かめる（docs/04）", allow_abbrev=False)
    parser.add_argument("step", choices=("mark", "fit", "grid", "check", "fold-weights", "rolling"),
                        help="mark・fit・grid・check・fold-weights・rolling")
    parser.add_argument("--latest-only", action="store_true", help="rolling で、いちばん新しい2つの区切りだけで、これからの重みを推定する")
    parser.add_argument("--from-year", choices=("2015", "2019", "2021"), default="2019", help="使う予測（predictions-<年>から。既定: 2019）")
    parser.add_argument("--force", action="store_true", help="fold-weights で、済んだ区切りも推定し直す")
    parser.add_argument("--save-models", action="store_true", help="fit で、本番のモデルの置き場所にも重みを書く")
    parser.add_argument("--top", type=int, default=8, help="grid で、券種ごとに出す行の数（既定: 8）")
    parser.add_argument("--tickets", type=Path, default=None,
                        help="check で読む、道具「印の成績」の買い目の CSV（既定: 印の成績-<--from-year>から/買い目/dscore_race_day_top3-race_day.csv）")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
