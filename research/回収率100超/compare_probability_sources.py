"""複勝の買い方はそのままに、確率の出どころだけを替えて比べる（研究「回収率100超」の入口⑦。docs/04-買い方.md の 8）。

    uv run python research/回収率100超/compare_probability_sources.py          # 当日のモデルを年ごとに学習し直して比べる（30〜60分）
    uv run python research/回収率100超/compare_probability_sources.py --reuse  # 残した予測から表だけを書き直す

比べる出どころは3つ。元（全券種のオッズから取り出した確率。``backtest.py`` が残した ``place_predictions.parquet``）、
新（予想「近走と適性から3着以内を予想」の当日のモデル。券種の支持 N を含む。その年より前だけで学習し直す）、2つの平均。
先に ``backtest.py`` と、``research/一番人気を疑う/port_check.py tables``（当日のモデルの学習データの表 ``form_pool``）が要る。
ここでは元DB を開かない。本番の保存済みモデルも使わない。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。

出るもの（Git 対象外）: ``reports/回収率100超/cache/race_day_model_predictions.parquet``（新しい確率）と
``…-log.csv``（木の数）、``reports/回収率100超/確率の出どころの比べ.md``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 一番人気を疑う.analysis.port import port_table_named, variant_keyed  # noqa: E402
from 回収率100超.analysis.probability_source import (  # noqa: E402
    ORIGINAL,
    SOURCES,
    PCoreAffinity,
    ProbabilitySourceBacktest,
    ProbabilitySourceTable,
    RaceDayModelPredictions,
    SourceAdoptionRule,
    SourceComparisonReport,
    SourceLogLoss,
    SourceVerdicts,
    TrainingThreads,
    YearlyWindows,
)
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import WalkForwardRunner, WindowTrainer  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = _REPO_ROOT / "reports" / "回収率100超" / "cache"
DEFAULT_OUT = _REPO_ROOT / "reports" / "回収率100超"
#: 当日のモデルの学習データの表（研究「一番人気を疑う」の ``port_check.py tables`` が作る）。
DEFAULT_TABLES = _REPO_ROOT / "reports" / "一番人気を疑う" / "移したあとの確かめ" / "tables"
#: 元の予測（``backtest.py`` が残す）と、新しい予測の置き場所。
ORIGINAL_PREDICTIONS = "place_predictions.parquet"
MODEL_PREDICTIONS = "race_day_model_predictions.parquet"
MODEL_LOG = "race_day_model_predictions-log.csv"
REPORT_FILE = "確率の出どころの比べ.md"
#: 学習データの表と、その作り方（移したあとの確かめで採用した当日のモデルと同じ）。
TABLE_NAME = "form_pool"
VARIANT_KEY = "pool-race_day"


def main() -> None:
    args = _parser().parse_args()
    original = pd.read_parquet(args.cache / ORIGINAL_PREDICTIONS)
    model = pd.read_parquet(args.cache / MODEL_PREDICTIONS) if args.reuse else _predict(args)
    table = ProbabilitySourceTable().build(original, model)
    results = {source: ProbabilitySourceBacktest().run(table, source) for source in SOURCES}
    rule = SourceAdoptionRule()
    verdicts = SourceVerdicts({name: rule.judge(result, results[ORIGINAL])
                               for name, result in results.items() if name != ORIGINAL})
    log_loss = SourceLogLoss().by_year(table, SOURCES)
    years = (int(table["year"].min()), int(table["year"].max()))
    text = SourceComparisonReport().build(results, verdicts, log_loss, len(table), years)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / REPORT_FILE).write_text(text, encoding="utf-8")
    print(f"書き出しました: {args.out / REPORT_FILE}", flush=True)
    for name, verdict in verdicts.by_source.items():
        print(f"{name}: {verdict.text}", flush=True)


def _predict(args: argparse.Namespace) -> pd.DataFrame:
    """当日のモデルを年ごとに学習し直して、新しい確率を残す。"""
    PCoreAffinity().apply()
    settings = TrainingThreads(args.threads).apply(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH))
    data = TableStore(args.tables).read(TABLE_NAME, port_table_named(TABLE_NAME).catalog)
    print(f"学習データの表: {len(data):,} 行・特徴量 {data.features.shape[1]} 個", flush=True)
    windows = YearlyWindows(args.first_test_year, args.last_test_year).build()
    runner = WalkForwardRunner(WindowTrainer(settings), windows)
    predictions, log = RaceDayModelPredictions(runner, variant_keyed(VARIANT_KEY)).run(data)
    args.cache.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(args.cache / MODEL_PREDICTIONS, index=False)
    log.to_csv(args.cache / MODEL_LOG, index=False, encoding="utf-8-sig")
    print(f"新しい確率を残しました: {args.cache / MODEL_PREDICTIONS}（{len(predictions):,} 頭）", flush=True)
    return predictions


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="確率の出どころを替えて、同じ複勝の買い方で比べる", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="元の予測と、新しい予測の置き場所")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES, help="当日のモデルの学習データの表の置き場所")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="結果の文書の置き場所")
    parser.add_argument("--first-test-year", type=int, default=2019)
    parser.add_argument("--last-test-year", type=int, default=2026)
    parser.add_argument("--threads", type=int, default=6, help="学習のスレッド数（既定: 6）")
    parser.add_argument("--reuse", action="store_true", help="学習し直さずに、残した新しい予測から表だけを書き直す")
    return parser


if __name__ == "__main__":
    main()
