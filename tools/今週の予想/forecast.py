"""今週の予想: 今週のレースを今のモデルで予想し、全頭の順位・印（◎○▲△☆注消）・良い点と悪い点・総合の理由を出す。

    uv run python tools/今週の予想/forecast.py                                    # 今日以降の全レース（出馬表のあるもの）
    uv run python tools/今週の予想/forecast.py --date 2026-10-04                  # その日の全レース
    uv run python tools/今週の予想/forecast.py --date 2026-10-04 --venue 東京     # その日・その競馬場の全レース
    uv run python tools/今週の予想/forecast.py --date 2026-10-04 --venue 東京 --race 11 --detail   # 1レースと、各馬の理由
    uv run python tools/今週の予想/forecast.py 2026100405040211 --timing 木曜     # rid と時点を指定
    uv run python tools/今週の予想/forecast.py --skip-saved                       # 同じ時点で作ってあるレースは作り直さない

予想は「近走と適性から3着以内を予想」の学習済みモデル（reports/近走と適性から3着以内を予想/models/）で、
3着以内に入る確率の高い順に全頭を並べ、設計書「買うレースと買い目を決める」07 の 5 の決め方で印を付ける。
前日・当日は、危険な1番人気を「人気馬が4着以下になるかを予想」の学習済みモデルで判定して「消」にし、残りの馬に ◎〜△ を付ける。
印の付かなかった馬も「消」。時点（木曜・前日・当日）は、DB に入っている情報（オッズ・馬番・馬体重）から自動で選ぶ。
先に jvdata-store で今週の出馬表（jvstore sync）と速報（jvstore realtime --date <開催日>）を取り込んでおく。
結果は reports/今週の予想/<開催日>/<rid>.json にも書き、検索画面の「今週の予想」タブがそれを見せる。
1レースに数十秒かかる（はじめの1レースは、事実表とスピード指数を作るので数分）。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import card, cli, db, race  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.favorites_out_of_top3.command.yosou_name import YOSOU_NAME as FAVORITE_YOSOU_NAME  # noqa: E402
from yosou.form_aptitude_top3.command.yosou_name import YOSOU_NAME  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402

from 今週の予想.forecast_store import DEFAULT_FOLDER, ForecastStore  # noqa: E402
from 今週の予想.forecast_table import ForecastTable  # noqa: E402
from 今週の予想.race_forecaster import FORECAST_VERSION, RaceForecaster  # noqa: E402
from 今週の予想.timing_chooser import TimingChooser  # noqa: E402

#: 学習済みモデルの既定の置き場所。
DEFAULT_MODELS = HERE.parents[1] / "reports" / YOSOU_NAME / "models"
#: 危険な人気馬を判定する予想（人気馬が4着以下になるかを予想）の学習済みモデルの既定の置き場所。
DEFAULT_FAVORITE_MODELS = HERE.parents[1] / "reports" / FAVORITE_YOSOU_NAME / "models"
_RID = card.CARD_LIST_HEADERS.index("rid")


def main(args) -> None:
    store = ForecastStore(args.out_dir)
    forecaster = RaceForecaster(args.models, args.favorite_models)
    tables: list[Table] = []
    with db.open_db(args.db) as con:
        race_ids = _race_ids(con, args)
        for number, race_id in enumerate(race_ids, start=1):
            print(f"[{number}/{len(race_ids)}] {race_id} を予想します", file=sys.stderr, flush=True)
            if args.skip_saved and _same_timing_saved(con, store, race_id):
                print("  同じ時点で作ってあるので飛ばします", file=sys.stderr, flush=True)
                continue
            try:
                forecast = forecaster.forecast(con, race_id, args.timing)
            except (ValueError, LookupError, FileNotFoundError) as error:
                print(f"  予想できません: {error}", file=sys.stderr, flush=True)
                continue
            store.save(forecast)
            tables.append(ForecastTable().table(forecast))
            if args.detail:
                tables.append(_detail_table(forecast))
    cli.emit(tables, args)
    print(f"\n保存先: {args.out_dir}", file=sys.stderr)


def _race_ids(con, args) -> list[str]:
    """予想するレース。rid か、開催日・競馬場・レース番号か、今日以降の全レース。"""
    if args.rid:
        return [args.rid]
    if args.date and args.venue and args.race:
        return [race.resolve_rid(con, args.date, args.venue, args.race)]
    start = args.date or date.today().isoformat()
    listed = card.list_cards(con, date_from=start, date_to=args.date, venue=args.venue, limit=card.MAX_LIST_LIMIT)
    if not listed.rows:
        raise LookupError(f"{start} 以降のレースが DB にありません。jvdata-store で今週の出馬表を取り込んでください")
    return [row[_RID] for row in listed.rows]


def _same_timing_saved(con, store: ForecastStore, race_id: str) -> bool:
    """作ってある結果が、今の作り方の版で、今選ぶ時点と同じか。"""
    saved = store.load(race_id)
    if saved is None or saved.get("version") != FORECAST_VERSION:
        return False
    return saved.get("timing") == TimingChooser().choose(con, race_id).timing.label


def _detail_table(forecast: dict) -> Table:
    """各馬の総合の理由の表。"""
    rows = [[horse["mark"], horse["horse_no"], horse["horse_name"], horse["summary"]] for horse in forecast["horses"]]
    return Table(["印", "馬番", "馬名", "総合"], rows, title=f"{forecast['title']} の各馬の理由")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
    parser.add_argument("--date", help="開催日 YYYY-MM-DD（省略すると今日以降の全部）")
    parser.add_argument("--venue", help="競馬場の名前かコード")
    parser.add_argument("--race", type=int, help="レース番号（--date と --venue と一緒に）")
    parser.add_argument("--timing", type=PredictionTiming.parse, default=None,
                        help="時点を決めて予想する: 木曜・前日・当日（省略すると DB の情報から自動で選ぶ）")
    parser.add_argument("--skip-saved", action="store_true", help="同じ時点・同じ作り方の版で作ってある結果は作り直さない")
    parser.add_argument("--detail", action="store_true", help="各馬の総合の理由の表も出す")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS,
                        help="学習済みモデルの置き場所（既定: reports/近走と適性から3着以内を予想/models）")
    parser.add_argument("--favorite-models", type=Path, default=DEFAULT_FAVORITE_MODELS,
                        help="危険な人気馬を判定する予想の学習済みモデルの置き場所（既定: reports/人気馬が4着以下になるかを予想/models）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_FOLDER, help="結果を書く場所（既定: reports/今週の予想）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
