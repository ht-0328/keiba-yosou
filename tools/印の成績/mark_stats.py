"""印の成績: 7つの区切りの予測（学習に使っていない期間）に、今週の予想と同じ決め方で印（◎○▲△☆注消）を付け、印ごとの成績を数える。

    uv run python tools/印の成績/mark_stats.py                                          # 今の本番と同じ作り（前日）で数える
    uv run python tools/印の成績/mark_stats.py --form h2h_ability/h2h-thursday          # 全頭の予想の予測を替える
    uv run python tools/印の成績/mark_stats.py --form form_experiments/new --no-danger  # 危険な人気馬の判定を使わない
    uv run python tools/印の成績/mark_stats.py --form reports/tmp/my.pkl --danger favorites_out_of_top3/improved

予測は、研究「既存モデルの改善」の入口② walk_forward.py が書く reports/既存モデルの改善/predictions/<予想>/<作り方>.pkl。
区切りごとに、それより前で学習したモデルで次の半年を予測したもので、テスト期間（学習にも線にも使っていない期間）の行だけを数える。
新しいモデル（作り方）を作ったら、walk_forward.py で予測を作り、--form にその名前を渡すと、いつも同じ形の表が出る。

出す表は5つ。1. 印ごとの成績（成績7つと、同じ人気の馬全体との比べ。◎ は1番人気かどうかでも分け、消は内訳も）、
2. ◎○▲の3頭のうち3着以内に来た頭数（1〜3番人気と比べる）、3. 2頭とも3着以内の組、4. 年ごと、5. 区切りごとの危険の線。
オッズは確定オッズ（過去のレースには締め切り前のオッズが無い）。危険な人気馬は --danger の予測で、区切りごとに検証期間で線を決め直す。
結果は reports/印の成績/<全頭の予想の名前>.md にも書く。元DB の事実表を作るので、数分かかる。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

import pandas as pd  # noqa: E402

from 共通 import cli, db, render  # noqa: E402

from yosou.form_aptitude_top3.command.yosou_name import YOSOU_NAME  # noqa: E402
from yosou.shared.place_value import PlacePriceEstimator  # noqa: E402
from yosou.shared.repository import PlacePriceRepository  # noqa: E402

from 印の成績.backtest_marker import BacktestMarker  # noqa: E402
from 印の成績.favorite_danger_judge import COLUMNS as DANGER_COLUMNS, FavoriteDangerJudge  # noqa: E402
from 印の成績.mark_report import MarkReport  # noqa: E402
from 印の成績.prediction_file import TEST, PredictionFile  # noqa: E402
from 印の成績.race_results import RaceResults  # noqa: E402

#: 既定の予測。全頭の予想は今の本番の前日のモデルと同じ作り（馬の力の材料 + 対戦レーティング）、人気馬の予想は今の本番と同じ作り。
DEFAULT_FORM = "h2h_ability/h2h-day_before"
DEFAULT_DANGER = "favorites_out_of_top3/people_market"
#: 複勝の見込みの倍率（全頭の予想の学習済みモデルと一緒に保存したもの）の既定の置き場所。
DEFAULT_MODELS = HERE.parents[1] / "reports" / YOSOU_NAME / "models"
#: 結果を書く場所。
DEFAULT_OUT_DIR = HERE.parents[1] / "reports" / "印の成績"


def main(args) -> None:
    form = PredictionFile(args.form)
    danger = None if args.no_danger else PredictionFile(args.danger)
    predictions = form.load()
    tested = predictions[predictions["period"] == TEST]
    if tested.empty:
        raise LookupError(f"テスト期間の行がありません: {form.path}")
    print(f"{form.path} のテスト期間 {tested['race_id'].nunique():,} レースに印を付けます", file=sys.stderr, flush=True)
    marker = BacktestMarker(_estimator(args.models))
    with db.open_db(args.db) as con:
        favorites = danger.load() if danger else None
        race_ids = pd.concat([tested["race_id"], favorites["race_id"]]) if favorites is not None else tested["race_id"]
        places = marker.places(RaceResults().read(con, race_ids))
    dangers, lines = (FavoriteDangerJudge().judge(favorites, places) if favorites is not None
                      else (pd.DataFrame(columns=list(DANGER_COLUMNS)), {}))
    marked = marker.mark(tested, places, dangers)
    conditions = (f"全頭の予想: {form.name}。危険な人気馬: {danger.name if danger else '使わない'}。"
                  f"期間: {marked['race_date'].min():%Y-%m-%d} 〜 {marked['race_date'].max():%Y-%m-%d}（7つの区切りのテスト期間）。")
    tables = MarkReport().tables(marked, conditions, lines)
    cli.emit(tables, args)
    saved = Path(args.out_dir) / f"{form.label()}.md"
    saved.parent.mkdir(parents=True, exist_ok=True)
    render.write(render.render(tables, "markdown"), saved, fmt="markdown")
    print(f"\n保存先: {saved}", file=sys.stderr)


def _estimator(models: Path) -> PlacePriceEstimator | None:
    state = PlacePriceRepository(models).load()
    return PlacePriceEstimator.from_state(state) if state is not None else None


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--form", default=DEFAULT_FORM,
                        help=f"全頭の予想（3着以内に入る確率）の予測。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_FORM}）")
    parser.add_argument("--danger", default=DEFAULT_DANGER,
                        help=f"危険な人気馬を判定する人気馬の予想の予測。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_DANGER}）")
    parser.add_argument("--no-danger", action="store_true", help="危険な人気馬の判定を使わない（◎〜△ は確率の順だけで付ける）")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS,
                        help="複勝の見込みの倍率（place_price.json）の置き場所（既定: reports/近走と適性から3着以内を予想/models）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="結果を書く場所（既定: reports/印の成績）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
