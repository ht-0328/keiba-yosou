"""穴馬の予想の確率のずれを、7つの区切りで確かめる（研究「既存モデルの改善」の入口⑦。issue #31）。

    uv run python research/既存モデルの改善/calibration.py

先に walk_forward.py で、穴馬の変更版の3つの時点の予測を作っておく（当日は --timing なしの improved.pkl）:

    uv run python research/既存モデルの改善/walk_forward.py --model longshots_in_top3 --variants improved
    uv run python research/既存モデルの改善/walk_forward.py --model longshots_in_top3 --variants improved --timing 木曜
    uv run python research/既存モデルの改善/walk_forward.py --model longshots_in_top3 --variants improved --timing 前日

出すもの: reports/穴馬が3着以内に入るかを予想/calibration-walk-forward.md（本番の calibration コマンドと同じ4つの表と、
較正の方法ごとの比べ方の表）。学習データは build_tables.py で保存した表を読む（元DB は開かない）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.command import CalibrationReportTables  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402

from 既存モデルの改善.analysis.calibration import (  # noqa: E402
    CalibrationComparison,
    CalibrationFrameBuilder,
    IsotonicCalibration,
    PlattCalibration,
)
from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
_DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions"
_DEFAULT_OUT = _REPO_ROOT / "reports" / "穴馬が3着以内に入るかを予想" / "calibration-walk-forward.md"
_MODEL = "longshots_in_top3"
#: 時点 → 予測を保存した名前（当日は、時点を付けずに回した変更版）。
_PREDICTION_KEYS = {
    PredictionTiming.THURSDAY: "improved-thursday",
    PredictionTiming.DAY_BEFORE: "improved-day_before",
    PredictionTiming.RACE_DAY: "improved",
}
#: 比べる較正の方法。
_METHODS = {"Platt scaling": PlattCalibration, "isotonic regression": IsotonicCalibration}


def main(args) -> None:
    spec = spec_named(_MODEL)
    data = TableStore(args.tables).read(spec.name, spec.catalog)
    store = PredictionStore(args.predictions)
    present = {timing: key for timing, key in _PREDICTION_KEYS.items() if store.exists(_MODEL, key)}
    if not present:
        raise FileNotFoundError(f"穴馬の変更版の予測がありません（{args.predictions / _MODEL}）。先に walk_forward.py を回してください。")
    builder = CalibrationFrameBuilder(data, WINDOWS)
    frame = pd.concat([builder.build(store.read(_MODEL, key), timing) for timing, key in present.items()],
                      ignore_index=True)
    tables = [*CalibrationReportTables(frame).tables(), CalibrationComparison(frame, _METHODS).table()]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render.render(tables, "markdown"), encoding="utf-8")
    missing = [timing.label for timing in _PREDICTION_KEYS if timing not in present]
    note = f"予測の無い時点: {'・'.join(missing)}" if missing else ""
    cli.emit(Table(["時点", "予測の名前"], [[timing.label, key] for timing, key in present.items()],
                   title=f"確率のずれの表を書いた: {args.report}", note=note), args)


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--report", type=Path, default=_DEFAULT_OUT,
                        help="表を書くファイル（既定: reports/穴馬が3着以内に入るかを予想/calibration-walk-forward.md）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS, help="予測の表の置き場所")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
