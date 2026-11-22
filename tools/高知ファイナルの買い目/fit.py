"""高知ファイナルの買い目: 1着と3着以内を予想するモデルを、元DB の高知の全部の走で学んで保存する。

    uv run python tools/高知ファイナルの買い目/fit.py           # reports/高知ファイナルの買い目/models/ に書く（数分）

学ぶのは高知の 1300〜1600m・9頭以上の走。材料は近走・騎手・調教師・その日の傾向・速さの指数・単勝オッズ（確定）。
研究は research/高知ファイナルの高配当/。開催中は元DB をじかに読まず、--db に写しを渡す。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from 共通 import cli, db  # noqa: E402
from 共通.facts import ensure_facts  # noqa: E402

from 高知ファイナルの買い目.final_columns import FEATURES  # noqa: E402
from 高知ファイナルの買い目.final_features import FinalFeatures  # noqa: E402
from 高知ファイナルの買い目.final_model_store import DEFAULT_FOLDER, POPULARITY_RATES, FinalModelStore  # noqa: E402
from 高知ファイナルの買い目.final_models import SEEDS, FinalModels  # noqa: E402
from 高知ファイナルの買い目.repository import KochiRunRepository  # noqa: E402


def main(args: argparse.Namespace) -> None:
    with db.open_db(args.db, default=db.LOCAL) as con:
        ensure_facts(con)
        runs = KochiRunRepository(con).read()
    features = FinalFeatures()
    rates = features.popularity_rates(runs)
    table = features.build(runs, rates)
    rows = FinalModels.scope(table[table["finish"].notna()])
    models = FinalModels.fit(rows)
    meta = {"学んだ日": date.today().isoformat(), "レース数": int(rows["race_id"].nunique()), "頭数": int(len(rows)),
            "最初の開催日": f"{rows['race_date'].min():%Y-%m-%d}", "最後の開催日": f"{rows['race_date'].max():%Y-%m-%d}",
            "特徴量": list(FEATURES), "種": list(SEEDS), POPULARITY_RATES: {str(popularity): rate for popularity, rate in rates.items()}}
    folder = FinalModelStore(args.out).save(models, meta)
    print(f"書きました: {folder}（{meta['レース数']:,} レース・{meta['最初の開催日']}〜{meta['最後の開催日']}）")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB（既定: 地方の nvdata-store。開催中は写しを渡す）")
    parser.add_argument("--out", type=Path, default=DEFAULT_FOLDER, help=f"モデルを書くフォルダ（既定: {DEFAULT_FOLDER}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
