"""現行・オッズだけ・変更版を比べる表を出す（研究「既存モデルの改善」の入口④）。

    uv run python research/既存モデルの改善/compare.py                          # 4つの予想の表を全部
    uv run python research/既存モデルの改善/compare.py --only longshots_in_top3  # 1つだけ
    uv run python research/既存モデルの改善/compare.py --only form_experiments   # 材料の実験（base と比べた採否）

先に walk_forward.py（と、荒れ具合は upset_calc.py）で予測を作っておく。
出すもの: reports/既存モデルの改善/compare/<予想の名前>.md（予想ごとの比べ方の表）。
材料の実験（form_experiments）は、省略時には出さない（--only で名前を指定したときだけ。終わった作り方だけで比べる）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 既存モデルの改善.analysis.comparison import (  # noqa: E402
    ExperimentComparison,
    FavoriteComparison,
    FormComparison,
    LongshotComparison,
    UpsetComparison,
)
from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402
from 既存モデルの改善.analysis.variants import variants_of  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
_DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions"
_DEFAULT_COMPARE = _REPO_ROOT / "reports" / "既存モデルの改善" / "compare"
#: 1頭ごとの予想の比べ方のクラス。
_HORSE_COMPARISONS = {
    "form_aptitude_top3": FormComparison,
    "longshots_in_top3": LongshotComparison,
    "favorites_out_of_top3": FavoriteComparison,
    "form_experiments": ExperimentComparison,
}
#: 引数なしで出す予想（材料の実験は、名前を指定したときだけ）。
_DEFAULT_NAMES = ("form_aptitude_top3", "longshots_in_top3", "favorites_out_of_top3", "upset_level")
#: 荒れ具合の、方法の保存名 → 表に出す名前。
_UPSET_METHODS = {"current": "現行（レース単位で学ぶ）", "calc_market": "計算（オッズだけの勝率）",
                  "calc_model": "計算（3つの予想を組み合わせた勝率）"}


def main(args) -> None:
    names = args.only or list(_DEFAULT_NAMES)
    store, tables = PredictionStore(args.predictions), TableStore(args.tables)
    args.compare.mkdir(parents=True, exist_ok=True)
    rows = [_write(name, _tables_of(name, store, tables), args.compare) for name in names]
    cli.emit(Table(["予想", "表の数", "ファイル"], rows, title="比べ方の表"), args)


def _tables_of(name: str, store: PredictionStore, tables: TableStore) -> list[Table]:
    spec = spec_named(name)
    data = tables.read(spec.name, spec.catalog)
    if name == "upset_level":
        predictions = {label: store.read(name, key) for key, label in _UPSET_METHODS.items() if store.exists(name, key)}
        return UpsetComparison(data, predictions).tables()
    variants = [variant for variant in variants_of(name) if store.exists(name, variant.key)]
    predictions = {variant.key: store.read(name, variant.key) for variant in variants}
    labels = {variant.key: variant.name for variant in variants}
    return _HORSE_COMPARISONS[name](data, predictions, labels, WINDOWS).tables()


def _write(name: str, result: list[Table], folder: Path) -> list[object]:
    path = folder / f"{name}.md"
    path.write_text(render.render(result, "markdown"), encoding="utf-8")
    return [name, len(result), str(path)]


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--only", nargs="*", default=None, metavar="予想の名前", help="表を出す予想（省略すると4つ全部。材料の実験は form_experiments）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS, help="予測の表の置き場所")
    parser.add_argument("--compare", type=Path, default=_DEFAULT_COMPARE, help="比べ方の表を書く場所")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
