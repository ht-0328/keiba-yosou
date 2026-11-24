"""高配当の買い目（成績）: 予想「高配当の組が当たるかを予想」の年ごとの予測から買い目を選び、過去レースでの成績を出す。

    uv run python tools/高配当の買い目/stats.py                                   # 今の決まり（今週の予想と同じ期待値の線・上限の点数）で、5券種の全部
    uv run python tools/高配当の買い目/stats.py --value-line 1.10 --max-points 5   # 決まりを替える（--max-points 0 で上限なし）
    uv run python tools/高配当の買い目/stats.py --ticket ワイド 馬連               # 券種を絞る
    uv run python tools/高配当の買い目/stats.py --predictions <フォルダ> --out-dir <フォルダ>

予測は、予想のパッケージの walk（python -m yosou.high_payout_combos walk）が書く reports/高配当の組が当たるかを予想/predictions/<券種の英名>_<年>.parquet。
年ごとに、前の年までのレースだけで学んで、次の年の組の全部を予測したもの（学習に使っていない年の予測）。
買い目は、予想のパッケージの買い目の決まり（HighPayoutRule）で選ぶ: 組の確定オッズが券種ごとの高配当の線以上・上限未満で、
期待値（予想の確率 × 確定オッズ）が線以上の組を、1レース・1券種につき確率の高い順に上限の点数まで、1点 100円で買う（--max-points 0 で上限なし）。
既定の期待値の線・上限の点数は、今週の予想が実際に出す買い目と同じ（今週の予想/ticket_rules.py の HIGH_PAYOUT_…）。
券種は、今週の予想が出していない券種も含めて、予想のある5券種の全部を出す（出していない券種を出すかどうかを、成績を見て決め直せるように）。
予想を直したら（馬ごとの表・組の表・学習・walk を作り直したら）、これを回せば全券種の成績が出る。

出す表は5つ。1. 券種ごと（買ったレース・全レースに対する割合・点数・的中・当たったときの配当の中央・回収率と 90% の幅）、
2. 年ごとの回収率と的中数、3. 期間ごと（探す期間 = 2022年まで、確かめる期間 = 2023年から）、
4. 運用の目安（1開催日の買うレース・点数・金額、1年の投資と収支、いちばん深い落ち込み、外れが続いた最長のレース数、
高配当が1本以上当たった開催日の割合、1開催日の的中の平均）、5. 線の感度（期待値の線 1.00・1.05・1.10・1.20 × 上限の点数 なし・3・5・10）。
どの表も、券種ごとの行と、全部の券種を合わせた合計の行がある。
全レースの数（買わなかったレースも含む母数）と開催日の数は、馬ごとの表（reports/高配当の組が当たるかを予想/horses/。horses.py が作る）から、
予測のある年のレースを数える。オッズは確定オッズ（過去のレースには締め切り前のオッズが無い）。
結果は reports/高配当の買い目/成績.md にも書く。元DB は開かない。3連単の予測を読むので数分かかる。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import cli, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.high_payout_combos import DEFAULT_BANDS, HighPayoutRule, PredictionStore  # noqa: E402
from yosou.shared.betting import TicketType  # noqa: E402

from 今週の予想.ticket_rules import (  # noqa: E402
    HIGH_PAYOUT_LABELS,
    HIGH_PAYOUT_MAX_POINTS,
    HIGH_PAYOUT_VALUE_LINE,
    POINT_YEN,
)

from 高配当の買い目.backtest_picks import BacktestPicks  # noqa: E402
from 高配当の買い目.folders import DEFAULT_HORSES_FOLDER, DEFAULT_OUT_DIR, DEFAULT_PREDICTIONS_FOLDER, STATS_FILE  # noqa: E402
from 高配当の買い目.operation_table import OperationTable  # noqa: E402
from 高配当の買い目.period_table import PeriodTable  # noqa: E402
from 高配当の買い目.pick_columns import SENSITIVITY_VALUE_LINES  # noqa: E402
from 高配当の買い目.pick_groups import PickGroups  # noqa: E402
from 高配当の買い目.race_universe import RaceUniverse  # noqa: E402
from 高配当の買い目.repository.race_universe_reader import RaceUniverseReader  # noqa: E402
from 高配当の買い目.repository.yearly_prediction_reader import YearlyPredictionReader  # noqa: E402
from 高配当の買い目.search_verify_periods import SearchVerifyPeriods  # noqa: E402
from 高配当の買い目.sensitivity_table import NO_CAP, SensitivityTable  # noqa: E402
from 高配当の買い目.ticket_summary_table import TicketSummaryTable  # noqa: E402
from 高配当の買い目.year_table import YearTable  # noqa: E402


def main(args) -> None:
    ticket_types = _ticket_types(args.ticket)
    backtest = BacktestPicks(YearlyPredictionReader(PredictionStore(args.predictions)), _rule, ticket_types)
    universe = RaceUniverseReader(args.horses).read().of_years(backtest.years())
    print("年ごとの予測を読んで、買い目を選びます", file=sys.stderr, flush=True)
    candidates = backtest.candidates(min(args.value_line, *SENSITIVITY_VALUE_LINES))
    max_points = _max_points(args.max_points)
    picks = backtest.select(candidates, args.value_line, max_points)
    groups, periods = PickGroups(tuple(ticket_type.label for ticket_type in ticket_types)), SearchVerifyPeriods()
    conditions = _conditions(ticket_types, args.value_line, max_points, universe)
    tables: list[Table] = [
        TicketSummaryTable(universe, groups).table(picks, conditions),
        YearTable(groups).table(picks, sorted(backtest.years()), "買った点の無い年は回収率が「-」。"),
        PeriodTable(groups, periods).table(picks, "買い方は探す期間の成績を見て決めたので、決めたあとの成績は確かめる期間を見る。"),
        OperationTable(universe, groups).table(picks, "1開催日あたりと開催日の割合は、買い目の無かった開催日も数える。1年あたりは、対象の期間の長さ（年）で割ったもの。"
                                                      "落ち込みは、開催日ごとの収支を古い順に足して、いちばん高い所からいちばん大きく下がった幅。"),
        SensitivityTable(backtest, groups, periods).table(candidates, "期待値の線・上限の点数のほかは、上の表と同じ決まり。"
                                                                    "上限の点数は、1レース・1券種につき確率の高い順に残す点数。"),
    ]
    saved = Path(args.out_dir) / STATS_FILE
    render.write(render.render(tables, "markdown"), saved, fmt="markdown")
    cli.emit(tables, args)
    print(f"\n保存先: {saved}", file=sys.stderr)


def _rule(value_line: float, max_points: int | None) -> HighPayoutRule:
    """買い目の決まり（帯は予想のパッケージの既定）。"""
    return HighPayoutRule(DEFAULT_BANDS, value_line, max_points)


def _ticket_types(names: list[str] | None) -> tuple[TicketType, ...]:
    """成績を出す券種。省略すると、予想のある5券種の全部（今週の予想が出していない券種も数える）。"""
    if not names:
        return tuple(HIGH_PAYOUT_LABELS)
    chosen = tuple(TicketType.parse(name) for name in names)
    unknown = [ticket_type.label for ticket_type in chosen if ticket_type not in HIGH_PAYOUT_LABELS]
    if unknown:
        raise ValueError(f"高配当の買い目に無い券種です: {'・'.join(unknown)}（{'・'.join(ticket_type.label for ticket_type in HIGH_PAYOUT_LABELS)}）")
    return chosen


def _max_points(given: int | None) -> int | None:
    """上限の点数。0 以下と None は上限なし。"""
    return given if given and given > 0 else None


def _conditions(ticket_types: tuple[TicketType, ...], value_line: float, max_points: int | None, universe: RaceUniverse) -> str:
    """表の下に書く、買い目の決まりと対象の期間。"""
    bands = "・".join(f"{ticket_type.label} {DEFAULT_BANDS[ticket_type].high_line:g}倍以上 {DEFAULT_BANDS[ticket_type].cap:,g}倍未満"
                     for ticket_type in ticket_types)
    cap = f"1レース・1券種につき確率の高い順に {max_points}点まで" if max_points else f"上限の点数{NO_CAP}"
    return (f"決まり: 確定オッズが高配当の線以上・上限未満（{bands}）で、期待値（予想の確率 × 確定オッズ）が {value_line:.2f} 以上の組"
            f"（{cap}）、1点 {POINT_YEN}円。対象: 年ごとに前の年までで学んで次の年を予想した予測。期間 {universe.period_text()}"
            f"（全レース {universe.race_count:,}・開催日 {universe.day_count:,}）。回収率の 90% の幅は、開催日を単位に選び直して出したもの。")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--value-line", type=float, default=HIGH_PAYOUT_VALUE_LINE,
                        help=f"期待値の線（予想の確率 × オッズがこの値以上の組を買う。既定: 今週の予想と同じ {HIGH_PAYOUT_VALUE_LINE}）")
    parser.add_argument("--max-points", type=int, default=HIGH_PAYOUT_MAX_POINTS,
                        help=f"1レース・1券種の上限の点数（確率の高い順。既定: 今週の予想と同じ {HIGH_PAYOUT_MAX_POINTS or NO_CAP}。0 で上限なし）")
    parser.add_argument("--ticket", nargs="+", default=None, metavar="券種",
                        help=f"成績を出す券種（{'・'.join(ticket_type.label for ticket_type in HIGH_PAYOUT_LABELS)}。既定: 5券種の全部）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS_FOLDER,
                        help="年ごとの予測の置き場所（既定: reports/高配当の組が当たるかを予想/predictions）")
    parser.add_argument("--horses", type=Path, default=DEFAULT_HORSES_FOLDER,
                        help="馬ごとの表の置き場所。全レースの数と開催日の数を数える（既定: reports/高配当の組が当たるかを予想/horses）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="成績.md を書く場所（既定: reports/高配当の買い目）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
