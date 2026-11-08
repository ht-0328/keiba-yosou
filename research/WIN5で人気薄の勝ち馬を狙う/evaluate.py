"""WIN5で人気薄の勝ち馬を狙う: 人気薄の1着の予想を確かめる（段2 の入口②）。

    uv run python research/WIN5で人気薄の勝ち馬を狙う/evaluate.py                    # 並べ方・確率の当たり具合で作り方を選び、WIN5 の 50点で確かめる（十数分）
    uv run python research/WIN5で人気薄の勝ち馬を狙う/evaluate.py --variant longshot10 # 作り方を決めて WIN5 だけ確かめる

先に ``forecast.py train --timings 当日 前日`` で作り方ごとの予測を作っておく。今のモデルの予測は、道具「印の成績」の ``--win5`` の既定と同じ
（研究「複勝以外の回収率100超」の区切りごとの予測）。出るもの（Git 対象外）: ``reports/WIN5で人気薄の勝ち馬を狙う/段2の結果.md``・
``WIN5の精算.csv``・``predictions/combined-<作り方>-<race_day|day_before>.pkl``（人気薄を新しい確率に置き換えた予測）。
元DB は読むだけ。開催日のレースの時間には動かさない。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools"), str(_REPO_ROOT / "src")]

from 共通 import db  # noqa: E402

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402
from 共通.render import Table  # noqa: E402

from 印の成績.prediction_file import TEST, PredictionFile  # noqa: E402
from 印の成績.win5_prediction_files import DEFAULT_DAY_BEFORE, DEFAULT_RACE_DAY  # noqa: E402

from WIN5で人気薄の勝ち馬を狙う.analysis.case_report import CaseReport  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.combined_win_share import CombinedWinShare  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.evaluation_frame import EvaluationFrame  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_dataset import LongshotDataset  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_evaluation import LongshotEvaluation  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_prediction_store import LongshotPredictionStore  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_variants import VARIANTS, variant_named  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_window_trainer import LongshotWindowTrainer  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.type_feature_source import TypeFeatureSource  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.repository import Win5LegRepository  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.focus_day_runner import FocusDayRunner  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.hedge_candidates import CANDIDATES  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.win5_hedge_study import Win5HedgeStudy  # noqa: E402

DEFAULT_ROOT = _REPO_ROOT / "reports" / "WIN5で人気薄の勝ち馬を狙う"
REPORT_NAME = "段2の結果"
_HANDICAP_COLUMN = "型_ハンデの斤量差"


def main() -> None:
    args = _parser().parse_args()
    store = LongshotPredictionStore(args.root / "predictions")
    current = {timing: _tested(path) for timing, path in (("race_day", args.current[0]), ("day_before", args.current[1]))}
    with db.open_db(args.db, default=db.JRA) as con:
        win5_races = frozenset(Win5LegRepository(con).load(date(2019, 1, 1))["race_id"].astype(str))
        sections, chosen = _ordering_sections(store, current["race_day"], win5_races, args.variant)
        combined = tuple(_combined(store, chosen, timing, current[timing]) for timing in ("race_day", "day_before"))
        type_features = TypeFeatureSource(args.root).load()
        handicap = _handicap(type_features)
        result = Win5HedgeStudy(tuple(args.current), combined, handicap).run(con)
        focus = _focus(con, args, chosen, type_features, handicap, (result.chosen, result.rule))
    sections.append(("WIN5 の本線と抑えで確かめる", result.tables))
    sections.append((f"詳しく見る日 {args.focus}", focus))
    result.settled.to_csv(args.root / "WIN5の精算.csv", index=False, encoding="utf-8-sig")
    missing = [timing for timing in ("race_day", "day_before") if not store.exists(chosen.key, timing)]
    intro = (f"新しい予測の無い時点（{', '.join(missing)}）の確率を使うレースは、今のモデルの確率のまま。" if missing else "") + (
             f"人気薄の1着の予想（作り方: {chosen.label}）を、人気薄の中の並べ方・確率の当たり具合と、WIN5 の本線（今の買い目）に足す抑え（荒れる前提）で確かめた結果。"
             f"判定: {result.verdict}（選んだ抑え: {result.chosen}）。研究の文書は research/WIN5で人気薄の勝ち馬を狙う/docs/04-段2の結果.md。")
    print(f"書きました: {CaseReport(args.root).write(REPORT_NAME, 'WIN5で人気薄の勝ち馬を狙う: 段2 の結果', intro, sections)}")


def _tested(path: Path):
    table = PredictionFile(str(path)).load()
    return table.loc[table["period"] == TEST]


def _ordering_sections(store: LongshotPredictionStore, current, win5_races: frozenset[str], variant_key: str | None):
    predictions = {variant.label: store.read(variant.key, "race_day") for variant in VARIANTS if store.exists(variant.key, "race_day")}
    frame = EvaluationFrame().build(current, predictions)
    evaluation = LongshotEvaluation(frame, list(predictions), win5_races)
    label = variant_named(variant_key).label if variant_key else evaluation.chosen()
    chosen = next(variant for variant in VARIANTS if variant.label == label)
    choice = Table(["項目", "内容"], [["選んだ作り方", label],
                                    ["選び方", "2019〜2024年の平地の全レースで、人気薄が勝ったレースの勝ち馬を人気薄の中の上位3頭に置けた割合がいちばん大きいもの"]],
                   title="作り方の選び方")
    return [("人気薄の1着の予想の作り方を選ぶ", [choice, *evaluation.tables()])], chosen


def _combined(store: LongshotPredictionStore, variant, timing: str, current) -> Path:
    """人気薄を新しい確率に置き換えた予測の pkl。その時点の新しい予測が無ければ、今のモデルの予測のまま（前日の時点を学んでいない作り方）。"""
    longshot = store.read(variant.key, timing) if store.exists(variant.key, timing) else pd.DataFrame(columns=["レースID", "馬番", "確率", "人気"])
    combined = CombinedWinShare().combine(current, longshot)
    path = store.path(f"combined-{variant.key}", timing)
    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_pickle(path)
    return path


def _focus(con, args: argparse.Namespace, variant, type_features, handicap: frozenset[str], labels: tuple[str, str]) -> list[Table]:
    """詳しく見る日を、学習の表の最後の日までの全部の行で学んだ人気薄の予想で予想し直し、本線と、選んだ抑え・決まりの抑えを組む。"""
    settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    data = LongshotDataset(type_features).build(PredictionTiming.RACE_DAY, variant.min_popularity, variant.baseline)
    runner = FocusDayRunner(LongshotWindowTrainer(settings, args.threads), variant, data, type_features, handicap)
    by_label = {candidate.label: candidate for candidate in CANDIDATES}
    chosen = [by_label[label] for label in labels]
    return runner.tables(con, args.focus, chosen)


def _handicap(type_features) -> frozenset[str]:
    return frozenset(type_features.loc[type_features[_HANDICAP_COLUMN].notna(), "レースID"].astype(str))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--variant", default=None, help=f"作り方を決めて確かめる（{' / '.join(v.key for v in VARIANTS)}。省略すると選ぶ）")
    parser.add_argument("--current", nargs=2, type=Path, default=[DEFAULT_RACE_DAY, DEFAULT_DAY_BEFORE], metavar=("当日", "前日"),
                        help="今のモデルの当日と前日の区切りごとの予測の pkl")
    parser.add_argument("--focus", default="2026-11-08", help="詳しく見る WIN5 の日（既定: 2026-11-08）")
    parser.add_argument("--threads", type=int, default=14, help="詳しく見る日のための学習のスレッド数（既定: 14）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="出力の置き場所")
    return parser


if __name__ == "__main__":
    main()
