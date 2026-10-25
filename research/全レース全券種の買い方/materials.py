"""研究「全レース全券種の買い方」の材料を作る（docs/01 の手順2）。

    uv run python research/全レース全券種の買い方/materials.py upset    # 配当率: 荒れ具合の予想（当日）を半年の区切りごとに学び直して、2015年からのレースに当てる（1時間半ほど）
    uv run python research/全レース全券種の買い方/materials.py upset --from-year 2024   # 区切りを限る（試し）
    uv run python research/全レース全券種の買い方/materials.py frames   # 枠連のための枠番（馬番 → 枠番）を元DB から読む
    uv run python research/全レース全券種の買い方/materials.py grades   # レースごとの的中率・配当率とその等級（セル）の表
    uv run python research/全レース全券種の買い方/materials.py baseline # 比べる相手（今の印の買い目を全レースで買ったもの）を道具「印の成績」の買い目の CSV からまとめる（数分）

出るものは全部 Git 対象外の ``reports/全レース全券種の買い方/``。
- ``配当率/upset_walk_forward.parquet``: 1行 = 1レース × 1券種（固い・中荒れ・大荒れ・超荒れの確率と、中荒れ以上の確率）。
- ``配当率/payout_rates.parquet``: 1行 = 1レース（券種ごとの中荒れ以上の確率と、その平均 = 配当率）。
- ``枠番.parquet``: 1行 = 1頭（race_id・horse_no・frame）。
- ``等級.parquet``: 1行 = 1レース（的中率・配当率とその等級・セル）。
- ``比べる相手.parquet``: 券種ごと・開催日ごとの点数・払戻・レース数・当たったレース数（今の印の買い目）。
元DB を読むのは学習データと枠番を作る段だけで、学習と予測は DB を閉じてから行う。
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import db  # noqa: E402

from yosou.shared.dataset import TrainingPeriod  # noqa: E402
from yosou.shared.repository import RaceDayRange  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402
from yosou.upset_level.dataset import race_dataset_builder  # noqa: E402
from yosou.upset_level.setting import DEFAULT_SETTINGS_PATH  # noqa: E402

from レースの種類ごとの買い方.analysis.bracket_source import BracketSource  # noqa: E402
from 全レース全券種の買い方.analysis.baseline_tickets import BaselineTickets  # noqa: E402
from 全レース全券種の買い方.analysis.grades_table import GradesTable  # noqa: E402
from 全レース全券種の買い方.analysis.half_year_folds import half_year_folds  # noqa: E402
from 全レース全券種の買い方.analysis.upset_walk_forward import UpsetWalkForward  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
OUT = _REPORTS / "全レース全券種の買い方"
#: 印を付けた表（研究「複勝以外の回収率100超」の手順6。2015年からの当日の予想）。
MARKED = _REPORTS / "複勝以外の回収率100超" / "組の期待値" / "marked-2015から.parquet"
#: 比べる相手の元になる、道具「印の成績」の買い目の CSV（2015年からの当日の予想。研究「レースの種類ごとの買い方」が回したもの）。
BASELINE_CSV = _REPORTS / "レースの種類ごとの買い方" / "印の成績-2015から" / "買い目" / "dscore_race_day_top3-race_day.csv"
#: 学習データの始まり（荒れ具合の予想の本番と同じ。DB にある全部）。
TRAIN_FIRST_DAY = date(2012, 1, 1)
#: 枠番を読む期間（枠連の表は 2016年から）。
FRAMES_RANGE = RaceDayRange(date(2016, 1, 1), date(2026, 12, 31))


def main() -> None:
    args = _parser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"upset": _upset, "frames": _frames, "grades": _grades, "baseline": _baseline}[args.command](args)


def _upset(args: argparse.Namespace) -> None:
    folds = [fold for fold in half_year_folds(args.from_year, args.to_year)]
    first = folds[0]
    period = TrainingPeriod.starting(TRAIN_FIRST_DAY, first.valid_first_day, first.first_day)
    started = time.monotonic()
    print("荒れ具合の学習データを作っています（学習の始まりから DB の最後まで）…", file=sys.stderr, flush=True)
    with db.open_db(args.db, default=db.JRA) as con:
        data = race_dataset_builder(con).build_training_data(period)
    print(f"  {len(data):,} レース（{time.monotonic() - started:.0f}秒）。区切り {len(folds)} 個を順に学び直します", file=sys.stderr, flush=True)
    settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    predictions = UpsetWalkForward(settings, TRAIN_FIRST_DAY).run(data, folds)
    folder = OUT / "配当率"
    folder.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(folder / "upset_walk_forward.parquet", index=False)
    rates = UpsetWalkForward.payout_rates(predictions)
    rates.to_parquet(folder / "payout_rates.parquet", index=False)
    print(f"保存先: {folder}（レース {rates['race_id'].nunique():,}。{time.monotonic() - started:.0f}秒）", file=sys.stderr)


def _frames(args: argparse.Namespace) -> None:
    with db.open_db(args.db, default=db.JRA) as con:
        frames = BracketSource(con).frames(FRAMES_RANGE)
    path = OUT / "枠番.parquet"
    frames.to_parquet(path, index=False)
    print(f"保存先: {path}（{frames['race_id'].nunique():,} レース・{len(frames):,} 頭）", file=sys.stderr)


def _grades(args: argparse.Namespace) -> None:
    marked = pd.read_parquet(MARKED, columns=["race_id", "race_date", "fold", "mark", "probability", "win_probability", "win_value", "win_odds"])
    rates_path = OUT / "配当率" / "payout_rates.parquet"
    rates = pd.read_parquet(rates_path) if rates_path.is_file() else None
    if rates is None:
        print("配当率の表が無いので、配当率の等級は「－」になります（materials.py upset）", file=sys.stderr)
    grades = GradesTable().build(marked, rates)
    path = OUT / "等級.parquet"
    grades.to_parquet(path, index=False)
    counts = grades["cell"].value_counts().sort_index()
    print(f"保存先: {path}（{len(grades):,} レース）\nセルごとのレース数:\n{counts.to_string()}", file=sys.stderr)


def _baseline(args: argparse.Namespace) -> None:
    summary = BaselineTickets().summarize(BASELINE_CSV)
    path = OUT / "比べる相手.parquet"
    summary.to_parquet(path, index=False)
    print(f"保存先: {path}（{summary['券種'].nunique()} 券種・{len(summary):,} 行）", file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
    subparsers = parser.add_subparsers(dest="command", required=True)
    upset = subparsers.add_parser("upset", help="配当率（荒れ具合の予想の区切りごとの予測）を作る")
    upset.add_argument("--from-year", type=int, default=2015, help="最初の区切りの年（既定: 2015）")
    upset.add_argument("--to-year", type=int, default=2026, help="最後の年（1年を1つの区切りにする。既定: 2026）")
    subparsers.add_parser("frames", help="枠番（馬番 → 枠番）を元DB から読む")
    subparsers.add_parser("grades", help="レースごとの的中率・配当率とその等級の表を作る")
    subparsers.add_parser("baseline", help="比べる相手（今の印の買い目）を開催日ごとにまとめる")
    return parser


if __name__ == "__main__":
    main()
