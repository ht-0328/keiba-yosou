"""研究「全レース全券種の買い方」の入口: 型の候補を数え上げ、セルごとに選び、2019〜2026年で確かめる（docs/01 の手順3〜5）。

    uv run python research/全レース全券種の買い方/formations.py cases                 # 手順3: セルごとの決着の型の表（事例.md）
    uv run python research/全レース全券種の買い方/formations.py count                 # 手順4: 8券種の型の候補を全部数え上げる（候補/<券種>.npz。1〜2時間）
    uv run python research/全レース全券種の買い方/formations.py count --ticket 馬連    # 1券種だけ
    uv run python research/全レース全券種の買い方/formations.py select --trial 2      # 手順4: 2015〜2018年でセルごとに型を選ぶ（選んだ型-2回目.md・.json）
    uv run python research/全レース全券種の買い方/formations.py confirm --trial 2     # 手順5: 選んだ型を 2019〜2026年で一度だけ数える（確かめ-2回目.md）

``--trial`` は何回目の確かめか（docs/01 の 6〜8）。1回目は上限 12点の型だけから選ぶ。2回目は、選ぶ期間で下の端が 100% に届かないセルを同じ型の上限 1点（最小の額）に落とす。
3回目は 2回目に加えて、◎ が 2倍以下のレース（セル ``<ランク>/2倍以下``）では単勝・複勝を買わず、馬単・3連単は ◎ 頭固定（軸 ◎ だけ）の型から選ぶ。

出るものは全部 Git 対象外の ``reports/全レース全券種の買い方/``。先に ``materials.py upset``・``frames``・``grades``・``baseline`` で材料を作る。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.repository import ComboBlendWeightsRepository  # noqa: E402

from 今週の予想.model_folders import DEFAULT_MODELS  # noqa: E402
from 全レース全券種の買い方.analysis.candidate_counter import CandidateCounter  # noqa: E402
from 全レース全券種の買い方.analysis.cases_report import CasesReport  # noqa: E402
from 全レース全券種の買い方.analysis.cell_selector import CellChoice, CellSelector  # noqa: E402
from 全レース全券種の買い方.analysis.choice_summary import ChoiceSummary  # noqa: E402
from 全レース全券種の買い方.analysis.combos_source import BRACKET_LABEL, TICKET_LABELS, CombosSource  # noqa: E402
from 全レース全券種の買い方.analysis.formation import MAX_POINTS, Formation, candidates  # noqa: E402
from 全レース全券種の買い方.analysis.grades_table import CELL, LOW_ODDS_BAND  # noqa: E402
from 全レース全券種の買い方.analysis.horse_slots import HorseSlots  # noqa: E402
from 全レース全券種の買い方.materials import MARKED, OUT  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
COMBOS = _REPORTS / "複勝以外の回収率100超" / "組の期待値" / "combos"
KINDS = _REPORTS / "レースの種類ごとの買い方" / "kinds.parquet"
BRACKET = _REPORTS / "レースの種類ごとの買い方" / "valued" / "now" / "bracket.parquet"
#: 選ぶ期間と確かめる期間（docs/01 の 5・6）。
SELECT_YEARS = range(2015, 2019)
CONFIRM_YEARS = range(2019, 2027)
ALL_YEARS = range(2015, 2027)
#: セルの並び（◎ランク × 配当率の等級。配当率の無いレースは －、◎ が 2倍以下のレースは 2倍以下）。
GRADES = ("S", "A", "B", "C")
CELLS: tuple[str, ...] = tuple(f"{hit}/{payout}" for hit in GRADES for payout in (*GRADES, "－", LOW_ODDS_BAND))
#: 3回目の決まり（docs/01 の 8）: ◎ が 2倍以下のレースでは、単勝・複勝は買わず、馬単・3連単は ◎ 頭固定（軸 ◎ だけ）の型から選ぶ。
LOW_ODDS_SKIP: tuple[str, ...] = ("単勝", "複勝")
LOW_ODDS_TOP_ONLY: tuple[str, ...] = ("馬単", "3連単")


def main() -> None:
    args = _parser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"cases": _cases, "count": _count, "select": _select, "confirm": _confirm}[args.command](args)


def _load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """印を付けた表・馬の位置・等級の表。"""
    marked = pd.read_parquet(MARKED)
    grades = pd.read_parquet(OUT / "等級.parquet")
    return marked, HorseSlots().build(marked), grades


def _source(marked: pd.DataFrame, slots: pd.DataFrame, grades: pd.DataFrame) -> CombosSource:
    frames_path = OUT / "枠番.parquet"
    return CombosSource(COMBOS, marked, pd.read_parquet(KINDS), ComboBlendWeightsRepository(DEFAULT_MODELS).load(), slots, grades,
                        bracket=pd.read_parquet(BRACKET) if BRACKET.is_file() else None,
                        frames=pd.read_parquet(frames_path) if frames_path.is_file() else None)


def _days(grades: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(pd.to_datetime(grades["race_date"]).drop_duplicates())


def _cases(args: argparse.Namespace) -> None:
    marked, slots, grades = _load()
    table = CasesReport().table(marked, slots, grades)
    path = OUT / "事例.md"
    render.write(render.render([_table(table, "セルごとの決着の型（2015〜2026年の当日の予想）",
                                       "セルは ◎ランク/配当率の等級。割合はレースあたり。3着以内の印はレースあたりの頭数。位置は ◎ が 0、ほかは ◎ と消を除いた3着以内の確率の順。")],
                               "markdown"), path, fmt="markdown")
    print(f"保存先: {path}", file=sys.stderr)


def _count(args: argparse.Namespace) -> None:
    marked, slots, grades = _load()
    source = _source(marked, slots, grades)
    days = _days(grades)
    folder = OUT / "候補"
    for label in ([args.ticket] if args.ticket else TICKET_LABELS):
        print(f"{label}: 候補 {len(candidates(label))} 個を数えます", file=sys.stderr, flush=True)
        counter = CandidateCounter(source, label, candidates(label), CELLS, days)
        years = [year for year in ALL_YEARS if not (label == BRACKET_LABEL and year == 2015)]
        counter.count(years)
        print(f"  保存: {counter.save(folder / f'{label}.npz')}", file=sys.stderr, flush=True)


def _select(args: argparse.Namespace) -> None:
    chosen: dict[str, list[dict[str, object]]] = {}
    tables: list[Table] = []
    for label in TICKET_LABELS:
        path = OUT / "候補" / f"{label}.npz"
        if not path.is_file():
            print(f"{label}: 候補の集計がありません（formations.py count）", file=sys.stderr)
            continue
        values, cells, days, labels = CandidateCounter.load(path)
        day_mask = np.array([day.year in SELECT_YEARS for day in days])
        if args.trial < 2:
            full = [index for index, formation in enumerate(candidates(label)) if formation.max_points == MAX_POINTS]
            selector = CellSelector([labels[index] for index in full], cells)
            values = values[full]
        else:
            selector = CellSelector(labels, cells, formations=candidates(label), token=True,
                                    allowed=_low_odds_rule(label) if args.trial >= 3 else None,
                                    skip_cells=[cell for cell in cells if _is_low_odds(cell)] if args.trial >= 3 and label in LOW_ODDS_SKIP else ())
        choices = selector.select(values, day_mask)
        selector.table(values, day_mask).to_csv(OUT / "候補" / f"{label}-成績.csv", index=False, encoding="utf-8-sig")
        chosen[label] = [choice.__dict__ for choice in choices]
        rows = [[choice.cell, choice.label, _pct(choice.recovery), _pct(choice.lower), choice.hits, choice.races, f"{choice.points_per_race:.1f}",
                 "・".join(part for part in ("" if choice.enough else "当たり不足", "1点に落とした" if choice.token else "", "買わない" if choice.skip else "") if part)] for choice in choices]
        tables.append(Table(["セル", "選んだ型", "回収率", "下の端", "当たったレース", "レース", "1レースの点数", "注意"], rows,
                            title=f"{label}: セルごとに選んだ型（{SELECT_YEARS.start}〜{SELECT_YEARS.stop - 1}年。{args.trial}回目）",
                            note="当たったレースが 30 以上の候補のうち、回収率の 90% の幅の下の端がいちばん高い型。「当たり不足」は、足りる候補が無く全候補から選んだセル。"
                                 "「1点に落とした」は、下の端が 100% に届かないので同じ型の上限 1点にしたセル（2回目から。成績は落とす前の型のもの）。"
                                 "「買わない」は、◎ が 2倍以下のレースで単勝・複勝を買わないセル（3回目から。成績は買った場合の参考）。"))
    (OUT / f"選んだ型-{args.trial}回目.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=1), encoding="utf-8")
    path = OUT / f"選んだ型-{args.trial}回目.md"
    render.write(render.render(tables, "markdown"), path, fmt="markdown")
    print(f"保存先: {path}", file=sys.stderr)


def _confirm(args: argparse.Namespace) -> None:
    chosen = json.loads((OUT / f"選んだ型-{args.trial}回目.json").read_text(encoding="utf-8"))
    baseline_path = OUT / "比べる相手.parquet"
    baseline = pd.read_parquet(baseline_path) if baseline_path.is_file() else None
    tables: list[Table] = []
    totals: list[list[object]] = []
    grand = None
    for label in TICKET_LABELS:
        if label not in chosen:
            continue
        values, cells, days, labels = CandidateCounter.load(OUT / "候補" / f"{label}.npz")
        choices = [CellChoice(**choice) for choice in chosen[label]]
        if args.trial < 2:
            full = [index for index, formation in enumerate(candidates(label)) if formation.max_points == MAX_POINTS]
            values = values[full]
        summary_of = ChoiceSummary(days)
        selected = ChoiceSummary.selected(values, choices)
        confirm_mask = np.array([day.year in CONFIRM_YEARS for day in days])
        summary = summary_of.summary(selected, confirm_mask)
        yearly = summary_of.yearly(selected)
        yearly = yearly[yearly["年"].isin(CONFIRM_YEARS)]
        passed, reason = ChoiceSummary.passes(summary, yearly)
        base = _baseline_summary(baseline, label, days, confirm_mask)
        totals.append([label, _pct(summary["回収率"]), _pct(summary["下の端"]), _pct(summary["的中率"]), f"{summary['レース']:,.0f}",
                       f"{summary['1レースの点数']:.1f}", "満たす" if passed else "満たさない", reason,
                       _pct(base["回収率"]) if base else "―", _pct(base["的中率"]) if base else "―"])
        tables.append(Table(["年", "回収率", "下の端", "的中率", "レース", "1レースの点数"],
                            [[int(row["年"]), _pct(row["回収率"]), _pct(row["下の端"]), _pct(row["的中率"]), f"{row['レース']:,.0f}", f"{row['1レースの点数']:.1f}"]
                             for _, row in yearly.iterrows()], title=f"{label}: 年ごと（{CONFIRM_YEARS.start}〜{CONFIRM_YEARS.stop - 1}年）"))
        by_cell = summary_of.by_cell(selected, cells, choices, confirm_mask)
        tables.append(Table(["セル", "型", "回収率", "下の端", "的中率", "レース", "1レースの点数"],
                            [[row["セル"], row["型"], _pct(row["回収率"]), _pct(row["下の端"]), _pct(row["的中率"]), f"{row['レース']:,.0f}", f"{row['1レースの点数']:.1f}"]
                             for _, row in by_cell.iterrows()], title=f"{label}: セルごと（確かめる期間）"))
        grand = selected.sum(axis=0) if grand is None else grand + selected.sum(axis=0)
    if grand is not None:
        summary_of = ChoiceSummary(days)
        total = summary_of.summary(grand[np.newaxis], confirm_mask)
        yearly = summary_of.yearly(grand[np.newaxis])
        yearly = yearly[yearly["年"].isin(CONFIRM_YEARS)]
        passed, reason = ChoiceSummary.passes(total, yearly)
        totals.append(["合計（8券種）", _pct(total["回収率"]), _pct(total["下の端"]), "―", f"{total['レース']:,.0f}", f"{total['1レースの点数']:.1f}",
                       "満たす" if passed else "満たさない", reason, "―", "―"])
    tables.insert(0, Table(["券種", "回収率", "下の端", "的中率", "レース", "1レースの点数", "採用の基準", "理由", "比べる相手の回収率", "比べる相手の的中率"], totals,
                           title=f"券種ごとの結果（{CONFIRM_YEARS.start}〜{CONFIRM_YEARS.stop - 1}年。1点 100円・全レース。{args.trial}回目）",
                           note="採用の基準は docs/01 の 6（回収率と 90% の幅の下の端が 100% 超え、100% 超えの年が 8年のうち 5年以上）。"
                                "比べる相手は今の印の買い目（08 の 2 の形）を全レースで買ったもの（枠連は無い）。確定オッズでの検証なので、実際に買うときより良く出る。"))
    path = OUT / f"確かめ-{args.trial}回目.md"
    render.write(render.render(tables, "markdown"), path, fmt="markdown")
    print(f"保存先: {path}", file=sys.stderr)


def _is_low_odds(cell: str) -> bool:
    return cell.endswith("/" + LOW_ODDS_BAND)


def _low_odds_rule(label: str):
    """3回目の決まり: ◎ が 2倍以下のセルで、馬単・3連単は ◎ 頭固定（軸 ◎ だけ）の型だけを候補にする。ほかは全部。"""
    def allowed(cell: str, formation: Formation) -> bool:
        return formation.axis_size == 1 if (_is_low_odds(cell) and label in LOW_ODDS_TOP_ONLY) else True
    return allowed


def _baseline_summary(baseline: pd.DataFrame | None, label: str, days: list[pd.Timestamp], day_mask: np.ndarray) -> dict[str, float] | None:
    if baseline is None:
        return None
    rows = baseline[baseline["券種"] == label]
    if rows.empty:
        return None
    chosen_days = set(pd.Timestamp(day) for day, picked in zip(days, day_mask, strict=True) if picked)
    rows = rows[pd.to_datetime(rows["race_date"]).isin(chosen_days)]
    stake = rows["points"].sum() * 100.0
    return {"回収率": rows["payout"].sum() / stake if stake > 0 else np.nan, "的中率": rows["hits"].sum() / rows["races"].sum() if rows["races"].sum() > 0 else np.nan}


def _table(frame: pd.DataFrame, title: str, note: str) -> Table:
    rows = [[_cell_text(value) for value in row] for row in frame.itertuples(index=False)]
    return Table(list(frame.columns), rows, title=title, note=note)


def _cell_text(value: object) -> str:
    if isinstance(value, float):
        return "—" if np.isnan(value) else (f"{value:.1%}" if 0 <= value <= 1 else f"{value:.2f}")
    return str(value)


def _pct(value: float) -> str:
    return "—" if value is None or (isinstance(value, float) and np.isnan(value)) else f"{value:.1%}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("cases", help="手順3: セルごとの決着の型の表")
    count = subparsers.add_parser("count", help="手順4: 型の候補を全部数え上げる")
    count.add_argument("--ticket", choices=TICKET_LABELS, default=None, help="1券種だけ数える（省略すると 8券種）")
    select = subparsers.add_parser("select", help="手順4: 2015〜2018年でセルごとに型を選ぶ")
    select.add_argument("--trial", type=int, default=1, help="何回目の確かめか（1: 上限 12点の型だけ、2: 届かないセルは 1点に落とす、3: 2倍以下は単複を買わず馬単・3連単は ◎ 頭固定）")
    confirm = subparsers.add_parser("confirm", help="手順5: 選んだ型を 2019〜2026年で一度だけ数える")
    confirm.add_argument("--trial", type=int, default=1, help="何回目の確かめか（選んだ型-<n>回目.json を使う）")
    return parser


if __name__ == "__main__":
    main()
