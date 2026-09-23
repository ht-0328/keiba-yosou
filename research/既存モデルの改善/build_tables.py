"""4つの予想の学習データを、全期間（2017年1月〜DB の最後）ぶん作って保存する（研究「既存モデルの改善」の入口①）。

    uv run python research/既存モデルの改善/build_tables.py                            # 4つ全部
    uv run python research/既存モデルの改善/build_tables.py --only form_aptitude_top3  # 1つだけ

出るもの: reports/既存モデルの改善/tables/<予想の名前>/（ids・features・targets・evaluation・baseline の pickle と meta.json）。
学習データを作るのは、予想のパッケージの dataset_builder そのもの（特徴量の作り方はこの研究に持たない）。
元DB を開くのは特徴量を作る間だけ（予想ごとに開いて閉じる）。1つにつき十数分かかる。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from 既存モデルの改善.analysis.tables import MODEL_TABLES, TABLE_PERIOD, ModelTableSpec, TableStore  # noqa: E402

#: リポジトリ直下（research/既存モデルの改善/ から2つ上）。
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUT = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"


def main(args) -> None:
    specs = [spec for spec in MODEL_TABLES if not args.only or spec.name in args.only]
    store = TableStore(args.tables)
    rows = [_build(spec, store, args) for spec in specs]
    cli.emit(Table(["予想", "行数", "特徴量の数", "秒", "フォルダ"], rows, title="学習データ（全期間）"), args)


def _build(spec: ModelTableSpec, store: TableStore, args) -> list[object]:
    started = time.perf_counter()
    print(f"{spec.label}: 学習データを作っています …", file=sys.stderr, flush=True)
    with db.open_db(args.db) as con:
        data = spec.builder_factory(con).build_training_data(TABLE_PERIOD)
    folder = store.write(spec.name, data)
    seconds = round(time.perf_counter() - started)
    print(f"{spec.label}: {len(data)}行・{seconds}秒", file=sys.stderr, flush=True)
    return [spec.label, len(data), data.features.shape[1], seconds, str(folder)]


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--only", nargs="*", default=None, metavar="予想の名前",
                        help="作る予想（form_aptitude_top3 / longshots_in_top3 / favorites_out_of_top3 / upset_level）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_OUT, help="保存する場所（既定: reports/既存モデルの改善/tables）")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
