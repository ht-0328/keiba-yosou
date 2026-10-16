"""今週の予想: 今週のレースを今のモデルで予想し、全頭の順位・印（◎○▲△☆注消と無印）・良い点と悪い点・総合の理由を出す。

    uv run python tools/今週の予想/forecast.py                                    # 今日以降の全レース（出馬表のあるもの）
    uv run python tools/今週の予想/forecast.py --date 2026-10-04                  # その日の全レース
    uv run python tools/今週の予想/forecast.py --date 2026-10-04 --venue 東京     # その日・その競馬場の全レース
    uv run python tools/今週の予想/forecast.py --date 2026-10-04 --venue 東京 --race 11 --detail   # 1レースと、各馬の理由
    uv run python tools/今週の予想/forecast.py 2026100405040211 --timing 木曜     # rid と時点を指定
    uv run python tools/今週の予想/forecast.py --skip-saved                       # 同じ時点で作ってあるレースは作り直さない

予想は「近走と適性から3着以内を予想」の学習済みモデル（reports/近走と適性から3着以内を予想/models/。3着以内のモデルと1着のモデル）で、
3着以内に入る確率の高い順に全頭を並べ、設計書「買うレースと買い目を決める」07 の 5 の決め方で印を付ける。
◎ は単勝 30倍以下の馬の中で単勝の期待値（1着になる確率 × 単勝オッズ）が1位の馬、○▲△ は ◎ を除いた3着以内の確率の順。レースの期待度（◎ の期待値が 1.00 以上なら高）も出す。
前日・当日は、危険な人気馬を「人気馬が4着以下になるかを予想」の学習済みモデルで判定して「消」にし、残りの馬に ◎〜△ を付ける
（消は1レース1頭まで。1番人気が危険ならその馬、そうでなければ 2〜5番人気から）。印の付かなかった馬は無印（－）。時点（木曜・前日・当日）は、DB に入っている情報（オッズ・馬番・馬体重）から自動で選ぶ。
先に jvdata-store で今週の出馬表（jvstore sync）と速報（jvstore realtime --date <開催日>）を取り込んでおく。
印から、設計書「買うレースと買い目を決める」08 の 2 の買い目（単勝・複勝・ワイド・馬連・馬単・3連複・3連単。3連複・3連単は前からの形と、
◎軸・軸馬の1頭軸流し・マルチ）を組み、締め切り前のオッズで期待値・組の確率・トリガミを付けて出す（今の決まりで実際に買うのは、複勝と、当日の予想で期待度「高」のレースの単勝・馬単。ほかは参考）。
結果は reports/今週の予想/<開催日>/<rid>.json にも書き、検索画面の「今週の予想」タブがそれを見せる。
予想のあと、開催日ごとに買うレースの計画（勝負／ノルマ参加（重賞）／ノルマ参加（日）／買わない と、複勝の買い目と金額。設計書 03・08 の 1）を
財布（reports/回顧/財布.json。初めの額は利用者が決める）の予算で決めて、reports/今週の予想/<開催日>/plan.json と回顧の表1「買い目の記録」に書く
（前日・当日の予想だけ。木曜はオッズが無いので計画しない）。予想の前には、終わったレースの回顧（レースの回顧・馬の回顧ノート）を自動で書き足し、
買い目の記録に払戻を入れる（tools/回顧/review.py と同じ。--no-review で飛ばす）。
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

from yosou.review import DEFAULT_REVIEW_DB, ReviewStore, ReviewWorkflow, names as review_names  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402

from 今週の予想.bet_recorder import BetRecorder  # noqa: E402
from 今週の予想.day_planner import DayPlanner  # noqa: E402
from 今週の予想.forecast_paces import ForecastPaces  # noqa: E402
from 今週の予想.forecast_store import DEFAULT_FOLDER, ForecastStore  # noqa: E402
from 今週の予想.forecast_table import ForecastTable  # noqa: E402
from 今週の予想.forecast_version import FORECAST_VERSION  # noqa: E402
from 今週の予想.model_folders import DEFAULT_FAVORITE_MODELS, DEFAULT_MODELS  # noqa: E402
from 今週の予想.plan_store import PlanStore  # noqa: E402
from 今週の予想.plan_table import PlanTable  # noqa: E402
from 今週の予想.race_forecaster import RaceForecaster  # noqa: E402
from 今週の予想.ticket_table import TicketTable  # noqa: E402
from 今週の予想.timing_chooser import TimingChooser  # noqa: E402
from 今週の予想.ticket_rules import HIGH_RACE_LABELS  # noqa: E402
from 今週の予想.wallet import MATCH_WALLET, POLICY_WALLET, WIN_WALLET, Wallet  # noqa: E402

_RID = card.CARD_LIST_HEADERS.index("rid")


def main(args) -> None:
    store = ForecastStore(args.out_dir)
    review = ReviewStore(args.review_db)
    forecaster = RaceForecaster(args.models, args.favorite_models, review_store=review)
    tables: list[Table] = []
    with db.open_db(args.db) as con:
        if not args.no_review:
            _update_review(con, review, store)
        race_ids = _race_ids(con, args)
        if args.plan_only:
            cli.emit(_plan_days(con, store, review, race_ids), args)
            return
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
            print(f"  全頭の予想根拠: {store.reasons_path(race_id)}", file=sys.stderr, flush=True)
            tables.append(ForecastTable().table(forecast))
            tables.append(TicketTable().table(forecast))
            if args.detail:
                tables.append(_detail_table(forecast))
                tables.append(_story_table(forecast))
        if not args.no_plan:
            tables += _plan_days(con, store, review, race_ids)
    cli.emit(tables, args)
    print(f"\n保存先: {args.out_dir}", file=sys.stderr)


def _update_review(con, review: ReviewStore, store: ForecastStore) -> None:
    """終わったレースの回顧（表2・表3）を書き足し、買い目の記録（表1）に払戻を入れる（初めての1回は 2011年からさかのぼるので 2〜3分）。"""
    print("終わったレースの回顧を書き足しています …", file=sys.stderr, flush=True)
    written = ReviewWorkflow(review).run(con, None, ForecastPaces(store).table())
    print(f"  レースの回顧 {written[review_names.RACES_TABLE]:,} 行・馬の回顧ノート {written[review_names.HORSES_TABLE]:,} 行・"
          f"精算した買い目 {written[review_names.BETS_TABLE]:,} 点（{review.path}）", file=sys.stderr, flush=True)


def _plan_days(con, store: ForecastStore, review: ReviewStore, race_ids: list[str]) -> list[Table]:
    """予想したレースの開催日ごとに、その日の全部の予想（保存してあるもの）から買うレースの計画を決めて、保存と記録をする。"""
    wallet = Wallet(review)
    planner, recorder, plans_store = DayPlanner(wallet), BetRecorder(review), PlanStore(store)
    tables = []
    for day in sorted({date(int(rid[:4]), int(rid[4:6]), int(rid[6:8])) for rid in race_ids}):
        listed = card.list_cards(con, date_from=day.isoformat(), date_to=day.isoformat(), limit=card.MAX_LIST_LIMIT)
        forecasts = [forecast for forecast in (store.load(row[_RID]) for row in listed.rows) if forecast is not None]
        if not any(forecast.get("odds_known") for forecast in forecasts):
            continue
        plans = planner.plan(con, day, forecasts)
        summary = {**{name: wallet.balance(name, wallet.month_start(day)) for name in (MATCH_WALLET, POLICY_WALLET, WIN_WALLET)},
                   "予算": {kind: wallet.budget(kind, day) for kind in (review_names.MATCH, review_names.POLICY_STAKES, review_names.POLICY_DAY)},
                   "1点": wallet.unit(day), "単勝・馬単の1点": {label: wallet.point_yen(label, day) for label in HIGH_RACE_LABELS}}
        plans_store.save(day, plans, summary)
        odds_at = max((forecast.get("made_at") or "" for forecast in forecasts), default="")
        recorder.record(plans, odds_at)
        tables.append(PlanTable().table(day, plans, summary))
    return tables


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


def _story_table(forecast: dict) -> Table:
    """各馬の近走の文の表（1行 = 1走の文か、敗因の候補・評価の行）。"""
    rows = [[horse["mark"], horse["horse_no"], horse["horse_name"], line]
            for horse in forecast["horses"] for line in (horse.get("story") or {}).get("lines", [])]
    return Table(["印", "馬番", "馬名", "近走（古い順）"], rows, title=f"{forecast['title']} の各馬の近走の文",
                 note="近5走を1走ずつ文にしたもの。4着以下の走には敗因の候補、最後に評価のことば（上向き・大敗続き）。道具「近走の文」と同じ。")


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
    parser.add_argument("--review-db", type=Path, default=DEFAULT_REVIEW_DB, help="回顧の DuckDB の場所（既定: reports/回顧/review.duckdb）")
    parser.add_argument("--no-review", action="store_true", help="予想の前に、終わったレースの回顧を書き足さない")
    parser.add_argument("--no-plan", action="store_true", help="予想のあとに、買うレースの計画を決めない")
    parser.add_argument("--plan-only", action="store_true", help="予想はせず、保存してある予想から買うレースの計画だけを決め直す")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
