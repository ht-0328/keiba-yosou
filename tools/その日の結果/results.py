"""その日の結果: 開催日の全レースについて、予想（印・実際に買う買い目・印の買い目・AI＋ロジック予想・高配当の買い目・的中実績の公開ルール）と結果（着順・払戻）を突き合わせる。

    uv run python tools/その日の結果/results.py                    # 今日
    uv run python tools/その日の結果/results.py --date 2026-11-22  # その日

読むのは、今週の予想が書いた予想の結果（``reports/今週の予想/<開催日>/<rid>.json``。発走前の通知が最後に書いた版）と、
元DB の着順・払戻（速報で届いたものも読む。レースの 10〜30 分後に入る）。まだ結果の届いていないレースは「結果待ち」と出す。
出す表は2つ。1. レースごと（印・1〜3着と印・◎ の着順・実際に買う買い目・AI の印の買い目・AI＋ロジック予想・高配当の買い目・公開ルール（◎ の単勝）の、買った額 → 戻った額）、
2. 合計（買い方ごとの買ったレース・当たったレース・投資・払戻・回収率。高配当の買い目は券種ごとと合計）。
高配当の買い目（予想「高配当の組が当たるかを予想」で選んだ、高配当の線以上の組）は 1点 100円で数える。予想に入っていないレース（前の版の予想・当日でない予想）は「買わない」。
印の買い目は、見込みの回収率 100% 以上（「買う」）のレースだけ数える。公開ルールは、◎ の単勝の期待値と単勝オッズが線に入るレースだけ ◎ の単勝を 100円で数える。AI＋ロジック予想は、展開・クラスのロジックで見送ったレースを除く。
合計の表の下に、消の数と1着になった数を、AI だけの予想と AI＋ロジック予想（消のロジックで取り消した馬を除く）で並べて出す。
結果は ``reports/その日の結果/<開催日>.md`` にも書く。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, render  # noqa: E402
from 今週の予想.forecast_store import ForecastStore  # noqa: E402
from 発走前の通知.race_styles import RaceStyles  # noqa: E402

from その日の結果.day_finishes import DayFinishes  # noqa: E402
from その日の結果.day_payouts import DayPayouts  # noqa: E402
from その日の結果.day_tables import DayTables  # noqa: E402
from その日の結果.race_result import RaceResult  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "reports" / "その日の結果"


def main(args) -> None:
    day = date.fromisoformat(args.date) if args.date else date.today()
    forecasts = ForecastStore().load_day(day)
    if not forecasts:
        raise LookupError(f"{day} の予想の結果がありません（reports/今週の予想/{day}/）")
    with db.open_db(args.db) as con:
        finishes = DayFinishes().read(con, day)
        payouts = DayPayouts().read(con, day)
    styles = RaceStyles(args.db)
    results = [(forecast, RaceResult(forecast, finishes.get(str(forecast["rid"]), []), payouts, styles.read(str(forecast["rid"]))))
               for forecast in forecasts]
    tables = DayTables().build(day, results)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render.write(render.render(tables, "markdown"), OUT_DIR / f"{day}.md", fmt="markdown")
    cli.emit(tables, args)


def build_parser():
    parser = cli.build_parser(__doc__)
    parser.add_argument("--date", help="開催日 YYYY-MM-DD（省略すると今日）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
