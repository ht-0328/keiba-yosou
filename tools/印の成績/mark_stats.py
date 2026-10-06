"""印の成績: 7つの区切りの予測（学習に使っていない期間）に、今週の予想と同じ決め方で印（◎○▲△☆注消と無印）とレースの期待度を付け、印ごとの成績を数える。

    uv run python tools/印の成績/mark_stats.py                                          # 今の本番と同じ作り（前日）で数える
    uv run python tools/印の成績/mark_stats.py --form h2h_pool_ability/h2h-race_day --win h2h_pool_ability/win-race_day --timing 当日   # 当日の予測
    uv run python tools/印の成績/mark_stats.py --form h2h_ability/h2h-thursday --win pace_thursday/win-thursday --timing 木曜   # 木曜の予測（オッズを使わない決め方）
    uv run python tools/印の成績/mark_stats.py --form form_experiments/new --no-danger  # 危険な人気馬の判定を使わない
    uv run python tools/印の成績/mark_stats.py --no-win                                 # 1着の予想を使わない（◎ は3着以内の確率の1位。前の決め方）
    uv run python tools/印の成績/mark_stats.py --danger-bands 1番人気 2〜3番人気 --out-dir reports/印の成績/比べ  # 消にできる人気帯を替えて比べる

予測は、研究「既存モデルの改善」の入口② walk_forward.py（1着の予想は入口⑪ win_check.py）が書く
reports/既存モデルの改善/predictions/<予想>/<作り方>.pkl。区切りごとに、それより前で学習したモデルで次の半年を予測したもので、
テスト期間（学習にも線にも使っていない期間）の行だけを数える。新しいモデル（作り方）を作ったら、予測を作って --form・--win にその名前を渡すと、
いつも同じ形の表が出る。

出す表は12。1. 印ごとの成績（成績7つと、同じ人気の馬全体との比べ。◎ は1番人気かどうかと期待度でも分け、消（危険な人気馬）は1番人気かどうかの内訳も）、
2. ◎○▲の3頭のうち3着以内に来た頭数（1〜3番人気と比べる）、3. 2頭とも3着以内の組、4. 年ごと、5. 区切りごとの危険の線、
6. ◎の期待度ごとの単勝の成績（回収率と 90% の幅。設計書「近走と適性から3着以内を予想」の 16 の 6 の採用の基準を見る表。「高」の内訳として、
2モデル一致・3連単の支持ありの絞り込みの行も出す）、
7. 印のルールの買い目（設計書「買うレースと買い目を決める」08 の 2。全券種。3連複・3連単は元の買い目（◎−○▲☆−○▲△☆・◎→○▲☆→○▲△☆）を必ず出し、
軸の1頭から ○▲△☆ への流し（3連複）とマルチ（3連単。組の期待値が 1.0 以上の買い目だけ）を、◎軸・軸馬の2パターンで足す）の買い方ごとの成績
（点数・投資・払戻・回収率・90% の幅。トリガミは外す。合計は「元の買い目だけ」と、それに ◎軸・軸馬の買い目を足したものの3つ。
対象は 全レース・期待度「高」・高で2モデル一致・高で3連単の支持あり・その両方。複勝と期待値で絞った3連複・3連単には「2モデル一致」の行も添える）、
8. 買い方ごとの年ごとの回収率、9. 期待値の線を動かしたときの 3連複・3連単の成績（参考）、
10. 場面（クラス・競馬場・頭数・単勝の売上・芝ダ）ごとの ◎ の成績と上乗せ（参考）、
11. 前日夜 → 当日朝の単勝オッズの動きごとの ◎ の単勝の成績（参考。時系列オッズのある約1年のレースだけ）、
12. 人気帯ごとの、危険度が線以上の馬の成績（人気帯の全体と比べる。区切りごとに回収率が全体を下回った数も）。
買い目は reports/印の成績/買い目/<全頭の予想の名前>.csv にも書く（1行 = 1点。3連複・3連単は組の期待値と確率も）。
◎ は単勝 30倍以下の馬の中で単勝の期待値（1着になる確率 × 確定の単勝オッズ）が1位の馬、期待度はその期待値が 1.00 以上なら高、未満なら低。
絞り込み（研究「回収率100超の施策」）: 「2モデル一致」は ◎ の単勝の期待値が LightGBM と CatBoost のそれぞれの確率でも 1.00 以上のレース、
「3連単の支持あり」は ◎ の 3連単から見た勝率（3連単の確定オッズから取り出す）が単勝から見た勝率以上のレース。
オッズは確定オッズ（過去のレースには締め切り前のオッズが無い。表11 だけ、時系列オッズの前日夜と当日朝の断面を使う）。
危険な人気馬は --danger の予測で、区切りごとに検証期間で線を決め直す。消にできる人気帯は --danger-bands（既定は今週の予想と同じ。1レース1頭で1番人気を優先）。
--timing 木曜 にすると、本番の木曜と同じく、オッズから出すもの（市場の見立て・複勝と単勝の期待値・危険な人気馬・絞り込み）を使わずに印を付ける
（◎ は1着になる確率の1位。☆・注・期待度は付かない）。
結果は reports/印の成績/<全頭の予想の名前>.md にも書く。元DB の事実表を作り、買い目の払戻とオッズ・3連単のオッズ・時系列オッズも読むので、10〜15分かかる。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

import pandas as pd  # noqa: E402

from 共通 import cli, db, render  # noqa: E402

from yosou.favorites_out_of_top3.dataset import FavoriteBand  # noqa: E402
from yosou.form_aptitude_top3.command.yosou_name import YOSOU_NAME  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.shared.place_value import PlacePriceEstimator  # noqa: E402
from yosou.shared.repository import PlacePriceRepository  # noqa: E402

from 今週の予想.danger_picker import MARKED_BANDS  # noqa: E402
from 今週の予想.mark_tickets import MarkTickets  # noqa: E402
from 今週の予想.torigami_filter import TorigamiFilter  # noqa: E402

from 印の成績.backtest_marker import BacktestMarker  # noqa: E402
from 印の成績.danger_band_report import DangerBandReport  # noqa: E402
from 印の成績.favorite_danger_judge import COLUMNS as DANGER_COLUMNS, FavoriteDangerJudge  # noqa: E402
from 印の成績.line_sensitivity_report import LineSensitivityReport  # noqa: E402
from 印の成績.mark_report import MarkReport  # noqa: E402
from 印の成績.movement_report import MovementReport  # noqa: E402
from 印の成績.odds_snapshot_repository import OddsSnapshotRepository  # noqa: E402
from 印の成績.pool_win_reader import PoolWinReader  # noqa: E402
from 印の成績.prediction_file import TEST, PredictionFile  # noqa: E402
from 印の成績.race_results import RaceResults  # noqa: E402
from 印の成績.race_scene_repository import RaceSceneRepository  # noqa: E402
from 印の成績.scene_bands import SceneBands  # noqa: E402
from 印の成績.scene_scheme import JRA_SCENE_SCHEME, SCENE_SCHEMES  # noqa: E402
from 印の成績.scene_report import SceneReport  # noqa: E402
from 印の成績.ticket_payouts import TicketPayouts  # noqa: E402
from 印の成績.ticket_report import TicketReport  # noqa: E402
from 印の成績.win_pool_size_repository import WinPoolSizeRepository  # noqa: E402
from 印の成績.win_value_attacher import WinValueAttacher  # noqa: E402

#: 既定の予測。全頭の予想は今の本番の前日のモデルと同じ作り（馬の力の材料 + 対戦レーティング）、1着の予想はその同じ材料で目的変数を1着にしたもの、
#: 人気馬の予想は今の本番と同じ作り。
DEFAULT_FORM = "h2h_ability/h2h-day_before"
DEFAULT_WIN = "h2h_ability/win-day_before"
DEFAULT_DANGER = "favorites_out_of_top3/people_market"
#: 危険と判定した馬を消にできる人気帯。
FAVORITE_BANDS: tuple[str, ...] = tuple(band.label for band in FavoriteBand)
#: 複勝の見込みの倍率（全頭の予想の学習済みモデルと一緒に保存したもの）の既定の置き場所。
DEFAULT_MODELS = HERE.parents[1] / "reports" / YOSOU_NAME / "models"
#: 結果を書く場所。
DEFAULT_OUT_DIR = HERE.parents[1] / "reports" / "印の成績"


def main(args) -> None:
    form = PredictionFile(args.form)
    win = None if args.no_win else PredictionFile(args.win)
    danger = None if args.no_danger else PredictionFile(args.danger)
    predictions = form.load()
    tested = predictions[predictions["period"] == TEST]
    if tested.empty:
        raise LookupError(f"テスト期間の行がありません: {form.path}")
    print(f"{form.path} のテスト期間 {tested['race_id'].nunique():,} レースに印を付けます", file=sys.stderr, flush=True)
    odds_known = args.timing is not PredictionTiming.THURSDAY
    marker = BacktestMarker(_estimator(args.models), odds_known=odds_known)
    test_race_ids = tested["race_id"].drop_duplicates()
    scheme = SCENE_SCHEMES[args.scene]
    database = db.LOCAL if scheme is not JRA_SCENE_SCHEME else db.JRA
    with db.open_db(args.db, default=database) as con:
        favorites = danger.load() if danger else None
        win_predictions = win.load() if win else None
        race_ids = pd.concat([frame["race_id"] for frame in (tested, favorites, win_predictions) if frame is not None])
        places = marker.places(RaceResults().read(con, race_ids))
        scenes = RaceSceneRepository().read(con, test_race_ids)
        pool_sizes = WinPoolSizeRepository().read(con, test_race_ids)
        pools = movements = None
        if odds_known:
            print("3連単のオッズから見た勝率と、前日夜・当日朝の単勝オッズを読みます", file=sys.stderr, flush=True)
            pools = PoolWinReader().read(con, test_race_ids)
            movements = OddsSnapshotRepository().read(con, test_race_ids)
    dangers, lines = (FavoriteDangerJudge(tuple(args.danger_bands)).judge(favorites, places) if favorites is not None and odds_known
                      else (pd.DataFrame(columns=list(DANGER_COLUMNS)), {}))
    wins = WinValueAttacher().attach(win_predictions, places) if win_predictions is not None else None
    marked = marker.mark(tested, places, dangers, wins, pools, movements)
    conditions = (f"時点: {args.timing.label}。全頭の予想: {form.name}。1着の予想: {win.name if win else '使わない'}。"
                  f"危険な人気馬: {danger.name if danger and odds_known else '使わない'}。"
                  f"期間: {marked['race_date'].min():%Y-%m-%d} 〜 {marked['race_date'].max():%Y-%m-%d}（7つの区切りのテスト期間）。")
    tables = MarkReport().tables(marked, conditions, lines)
    tickets = MarkTickets().build(marked)
    print(f"買い目 {len(tickets):,} 点の払戻と確定オッズを読みます", file=sys.stderr, flush=True)
    with db.open_db(args.db, default=database) as con:
        tickets = TorigamiFilter().apply(TicketPayouts(con).attach(tickets))
    report = TicketReport()
    tables += report.tables(tickets, marked["race_id"].nunique(), marked["race_date"].nunique())
    tables.append(LineSensitivityReport().table(tickets))
    scene_bands = SceneBands(scheme)
    tables.append(SceneReport(scene_bands.bands).table(marked, tickets, scene_bands.build(scenes, pool_sizes)))
    tables.append(MovementReport().table(marked))
    if not dangers.empty:
        tables.append(DangerBandReport().table(marked))
    cli.emit(tables, args)
    saved = Path(args.out_dir) / f"{form.label()}.md"
    saved.parent.mkdir(parents=True, exist_ok=True)
    render.write(render.render(tables, "markdown"), saved, fmt="markdown")
    tickets_csv = Path(args.out_dir) / "買い目" / f"{form.label()}.csv"
    tickets_csv.parent.mkdir(parents=True, exist_ok=True)
    report.csv_frame(tickets).to_csv(tickets_csv, index=False, encoding="utf-8-sig")
    print(f"\n保存先: {saved}\n買い目: {tickets_csv}", file=sys.stderr)


def _estimator(models: Path) -> PlacePriceEstimator | None:
    state = PlacePriceRepository(models).load()
    return PlacePriceEstimator.from_state(state) if state is not None else None


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--form", default=DEFAULT_FORM,
                        help=f"全頭の予想（3着以内に入る確率）の予測。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_FORM}）")
    parser.add_argument("--win", default=DEFAULT_WIN,
                        help=f"1着の予想（1着になる確率）の予測。◎ と期待度に使う。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_WIN}）")
    parser.add_argument("--no-win", action="store_true", help="1着の予想を使わない（◎ は3着以内の確率の1位。期待度は付かない）")
    parser.add_argument("--timing", type=PredictionTiming.parse, default=PredictionTiming.DAY_BEFORE,
                        help="予測の時点: 木曜・前日・当日（既定: 前日）。木曜は、オッズから出すもの（期待値・市場の見立て・危険な人気馬・絞り込み）を使わずに印を付ける")
    parser.add_argument("--danger", default=DEFAULT_DANGER,
                        help=f"危険な人気馬を判定する人気馬の予想の予測。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_DANGER}）")
    parser.add_argument("--no-danger", action="store_true", help="危険な人気馬の判定を使わない（◎〜△ は確率の順だけで付ける）")
    parser.add_argument("--danger-bands", nargs="+", choices=FAVORITE_BANDS, default=list(MARKED_BANDS), metavar="人気帯",
                        help=f"危険と判定した馬を消にできる人気帯（{'・'.join(FAVORITE_BANDS)}。1レース1頭で、1番人気を優先。"
                             f"既定: 今週の予想と同じ {'・'.join(MARKED_BANDS)}）")
    parser.add_argument("--scene", choices=tuple(SCENE_SCHEMES), default=JRA_SCENE_SCHEME.name,
                        help="場面の表（表10）のクラス・競馬場の帯の区分（既定: 中央）。地方の予想の予測を数えるときは 地方（--db を省くと地方の元DB を開く）")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS,
                        help="複勝の見込みの倍率（place_price.json）の置き場所（既定: reports/近走と適性から3着以内を予想/models）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="結果を書く場所（既定: reports/印の成績）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
