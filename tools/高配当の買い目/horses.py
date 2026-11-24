"""高配当の買い目（馬ごとの表）: 予想「高配当の組が当たるかを予想」が学習に使う、1頭1行の表を作る。

    uv run python tools/高配当の買い目/horses.py                                   # 今の本番の予想の予測で、全部の期間を作る
    uv run python tools/高配当の買い目/horses.py --from 2020-01-01 --to 2026-12-31  # 残す開催日の範囲
    uv run python tools/高配当の買い目/horses.py --form <予想>/<作り方> --win <予想>/<作り方> --danger <予想>/<作り方>   # 予測のファイルを替える
    uv run python tools/高配当の買い目/horses.py --out reports/高配当の買い目/確かめ/horses.parquet   # 書く先を替える

過去レースの「学習に使っていない期間の予測」（研究「既存モデルの改善」の walk_forward.py・win_check.py が書く
reports/既存モデルの改善/predictions/<予想>/<作り方>.pkl のテスト期間の行）に、今週の予想の当日の予想と同じ決め方で、
印（◎○▲△☆注消）・危険な人気馬・単勝と複勝の期待値を付ける（道具「印の成績」の部品を順に呼ぶ）。
オッズは確定オッズ（過去のレースには締め切り前のオッズが無い）。複勝の見込みの倍率は --models の place_price.json。
書く列は、レースID・開催日・馬番と、予想の材料の列（3着以内と1着の確率・市場の見立て・単勝と複勝のオッズ・人気・順位・
危険な人気馬かと危険度・印・上げ下げ・単勝と複勝の期待値）。馬ID・区切り・着順などもあれば残す。
書く先は reports/高配当の組が当たるかを予想/horses/<最初の年>-<最後の年>.parquet。予想のパッケージはこのフォルダの parquet を
全部読んでつなぐので、同じフォルダのほかのファイルに同じ出走があるときは書かずに止まる（古いファイルを消すか --out で別の場所へ）。
作ったあとは、予想のパッケージで組の表・学習・年ごとの予測を作り直す（python -m yosou.high_payout_combos tables / train / walk）。

元DB から結果・3連単のオッズ・時系列オッズを読むので、全部の期間で 20〜30分かかる（--from・--to で絞ると、3連単のオッズを読むレースが減って速い）。
元DB を開いているのは読む間だけで、印付けの計算は閉じてから行う。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

import pandas as pd  # noqa: E402

from 共通 import cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.place_value import PlacePriceEstimator  # noqa: E402
from yosou.shared.repository import PlacePriceRepository  # noqa: E402

from 今週の予想.model_folders import DEFAULT_MODELS  # noqa: E402
from 印の成績.prediction_file import TEST, PredictionFile  # noqa: E402

from 高配当の買い目.folders import DEFAULT_HORSES_FOLDER  # noqa: E402
from 高配当の買い目.horse_marker import HorseMarker  # noqa: E402
from 高配当の買い目.horse_table_columns import RACE_DATE, RACE_ID  # noqa: E402
from 高配当の買い目.horse_table_selector import HorseTableSelector  # noqa: E402
from 高配当の買い目.marking_input_reader import MarkingInputReader  # noqa: E402
from 高配当の買い目.repository.horse_table_store import HorseTableStore  # noqa: E402

#: 既定の予測。今の本番の当日の予想と同じ作り（全頭の予想・1着の予想）と、今の本番と同じ作りの人気馬の予想。
DEFAULT_FORM = "graded_race_day/odds_move-top3"
DEFAULT_WIN = "graded_race_day/odds_move-win"
DEFAULT_DANGER = "favorites_out_of_top3/people_market"


def main(args) -> None:
    selector = HorseTableSelector(_day(args.date_from), _day(args.date_to))
    form, win, danger = PredictionFile(args.form), PredictionFile(args.win), PredictionFile(args.danger)
    predictions = form.load()
    tested = predictions[predictions["period"] == TEST]
    tested = tested[selector.in_range(tested[RACE_DATE])]
    if tested.empty:
        raise LookupError(f"テスト期間の行がありません（開催日の範囲を確かめてください）: {form.path}")
    wins, favorites = win.load(), danger.load()
    marked_race_ids = tested[RACE_ID].drop_duplicates()
    print(f"{form.path} のテスト期間 {len(marked_race_ids):,} レースの結果とオッズを読みます", file=sys.stderr, flush=True)
    with db.open_db(args.db) as con:
        # 元DB を開いているのは読む間だけ（印付けの計算は閉じてから）
        inputs = MarkingInputReader().read(con, pd.concat([tested[RACE_ID], favorites[RACE_ID], wins[RACE_ID]]), marked_race_ids)
    print("元DB を閉じました。印を付けます", file=sys.stderr, flush=True)
    marked = HorseMarker(_estimator(args.models)).mark(tested, wins, favorites, inputs)
    table = selector.select(marked)
    store = HorseTableStore(DEFAULT_HORSES_FOLDER)
    saved = store.save(table, args.out or store.default_path(table))
    render.write(render.render(_summary(table, saved, (form, win, danger))), None)


def _summary(table: pd.DataFrame, saved: Path, files: tuple[PredictionFile, ...]) -> Table:
    """作った表の大きさ（行・レース・開催日の数と期間）と書いた先。値そのものは出さない。"""
    days = pd.to_datetime(table[RACE_DATE])
    rows = [["行（1頭1行）", f"{len(table):,}"], ["レース", f"{table[RACE_ID].nunique():,}"], ["開催日", f"{days.nunique():,}"],
            ["期間", f"{days.min():%Y-%m-%d} 〜 {days.max():%Y-%m-%d}"], ["列", "・".join(table.columns)], ["書いた先", str(saved)]]
    note = "予測: " + "・".join(file.name for file in files) + "。このあと、予想のパッケージで組の表・学習・年ごとの予測を作り直す"
    return Table(["項目", "値"], rows, title="馬ごとの表（高配当の組が当たるかを予想）", note=note)


def _day(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def _estimator(models: Path) -> PlacePriceEstimator | None:
    state = PlacePriceRepository(models).load()
    return PlacePriceEstimator.from_state(state) if state is not None else None


def build_parser() -> argparse.ArgumentParser:
    # --out は馬ごとの表（parquet）の書く先なので、共通の引数（--format・--out）は使わない。まとめの表は標準出力に出す
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help=db.JRA.help())
    parser.add_argument("--form", default=DEFAULT_FORM,
                        help=f"全頭の予想（3着以内に入る確率）の予測。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_FORM}）")
    parser.add_argument("--win", default=DEFAULT_WIN,
                        help=f"1着の予想（1着になる確率）の予測。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_WIN}）")
    parser.add_argument("--danger", default=DEFAULT_DANGER,
                        help=f"危険な人気馬を判定する人気馬の予想の予測。<予想>/<作り方> か pkl のパス（既定: {DEFAULT_DANGER}）")
    parser.add_argument("--from", dest="date_from", default=None, metavar="YYYY-MM-DD", help="残す開催日の最初の日（省略すると予測の最初から）")
    parser.add_argument("--to", dest="date_to", default=None, metavar="YYYY-MM-DD", help="残す開催日の最後の日（省略すると予測の最後まで）")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS,
                        help="複勝の見込みの倍率（place_price.json）の置き場所（既定: reports/近走と適性から3着以内を予想/models）")
    parser.add_argument("--out", type=Path, default=None, metavar="parquet",
                        help="馬ごとの表を書く先（既定: reports/高配当の組が当たるかを予想/horses/<最初の年>-<最後の年>.parquet）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
