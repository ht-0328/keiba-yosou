"""地方の直前の買い目: 2つのモデル（買う馬らしさ・単勝の戻りの見込み）を、学習用の表の全部で学んで保存する。

    uv run python tools/地方の直前の買い目/fit.py           # reports/地方の直前の買い目/models/ に書く（2〜3分）

学習用の表は、研究「地方の直前の材料で買う」の analysis/training_table.py が作る（reports/地方の直前の買い目/学習用の表.pkl）。
過去の成績の確かめ（時間の順を守って学び直す）は check.py。ここは本番用に全部の期間で学ぶだけ。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from 共通 import cli  # noqa: E402

from 地方の直前の買い目.late_columns import FEATURES, RACE_DATE, RACE_ID  # noqa: E402
from 地方の直前の買い目.late_model_store import DEFAULT_FOLDER, LateModelStore  # noqa: E402
from 地方の直前の買い目.late_models import SEEDS, LateModels  # noqa: E402
from 地方の直前の買い目.late_training_table import DEFAULT_PATH, LateTrainingTable  # noqa: E402


def main(args: argparse.Namespace) -> None:
    rows = LateTrainingTable(args.table).load()
    models = LateModels.fit(rows)
    meta = {"学んだ日": date.today().isoformat(), "レース数": int(rows[RACE_ID].nunique()), "頭数": int(len(rows)),
            "最初の開催日": f"{rows[RACE_DATE].min():%Y-%m-%d}", "最後の開催日": f"{rows[RACE_DATE].max():%Y-%m-%d}",
            "特徴量": list(FEATURES), "種": list(SEEDS)}
    folder = LateModelStore(args.out).save(models, meta)
    print(f"書きました: {folder}（{meta['レース数']:,} レース・{meta['最初の開催日']}〜{meta['最後の開催日']}）")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--table", type=Path, default=DEFAULT_PATH, help=f"学習用の表（既定: {DEFAULT_PATH}）")
    parser.add_argument("--out", type=Path, default=DEFAULT_FOLDER, help=f"モデルを書くフォルダ（既定: {DEFAULT_FOLDER}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
