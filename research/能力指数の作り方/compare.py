"""スピード指数の補正と、能力指数のまとめ方の候補を比べる（研究「能力指数の作り方」の入口②）。

    uv run python research/能力指数の作り方/compare.py

先に extract.py で中間データを作っておく。基準タイム・ペースの基準・ペース補正の大きさは 2023年までのレースで求め、
候補を選ぶのは 2016〜2023年の走、選んだものを確かめるのは 2024年からの走（選ぶのに使っていない期間）。
``reports/能力指数の作り方/比べ/`` に次を書く。

- 01-スピード指数の補正.md: 補正を1つずつ足したときの、同じ馬の続けた走どうしの指数の相関
- 02-能力指数のまとめ方.md: まとめ方・近走の数・期間・適性を1つずつ変えたときの、能力指数とその走の指数の相関
- 03-確かめ.md: 既定の設定（``AbilitySettings``）の、2024年からの走での当たり具合と、年ごとの当たり具合
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, render  # noqa: E402
from 共通.ability import COURSE, DISTANCE, GOING, AbilityBuilder, AbilityIndex, AbilitySettings  # noqa: E402
from 共通.render import Table  # noqa: E402

from 展開の理論の検証.analysis.cache_store import CacheStore  # noqa: E402
from 能力指数の作り方.analysis import FigureConsistency, IndexAccuracy  # noqa: E402
from 能力指数の作り方.extract import DEFAULT_CACHE  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUT = _REPO_ROOT / "reports" / "能力指数の作り方" / "比べ"
#: 基準を求める最後の日・候補を選ぶ期間・確かめる期間。
UNTIL = pd.Timestamp("2023-12-31")
SELECT = ("2016-01-01", "2023-12-31")
HOLDOUT = ("2024-01-01", "2026-12-31")

_PLAIN = AbilitySettings(track_variant=False, weight_per_kg=0.0, pace=False, floor_gap=None)
#: スピード指数の補正の候補（補正を1つずつ足していく）。
FIGURE_VARIANTS: dict[str, AbilitySettings] = {
    "補正なし（基準タイムだけ）": _PLAIN,
    "＋馬場差": replace(_PLAIN, track_variant=True),
    **{f"＋馬場差＋斤量 {w}%/kg": replace(_PLAIN, track_variant=True, weight_per_kg=w) for w in (0.05, 0.1, 0.15, 0.2, 0.3)},
    "＋馬場差＋斤量 0.05＋ペース": replace(_PLAIN, track_variant=True, weight_per_kg=0.05, pace=True),
    **{f"＋馬場差＋斤量 0.05＋ペース＋切り上げ {g}点": replace(_PLAIN, track_variant=True, weight_per_kg=0.05, pace=True,
                                                          floor_gap=g) for g in (40.0, 30.0, 20.0, 15.0)},
}
#: 能力指数のまとめ方の候補（既定の設定から1つずつ変える）。
INDEX_VARIANTS: dict[str, dict] = {
    "既定": {},
    **{f"近走の数: {n}": {"runs": n} for n in (1, 3, 5, 8, 10)},
    **{f"期間: {d}日": {"window_days": d} for d in (365, 730, 1095)},
    **{f"古い走の重みの倍率: {r}": {"recency": r} for r in (0.5, 0.7, 0.85, 1.0)},
    "適性なし（新しさだけの平均）": {"aptitudes": ()},
    **{f"適性: {a}だけ": {"aptitudes": (a,)} for a in (DISTANCE, COURSE, GOING)},
    **{f"距離の近さ: {d}m": {"distance_scale": d} for d in (400.0, 800.0, 1600.0)},
    **{f"違う競馬場の倍率: {v}": {"other_venue": v} for v in (0.7, 0.9, 1.0)},
    **{f"違う馬場の組の倍率: {v}": {"other_going": v} for v in (0.6, 0.8, 1.0)},
    **{f"違う芝ダの倍率: {v}": {"other_surface": v} for v in (0.1, 0.4, 1.0)},
}


def main(args) -> None:
    runs = CacheStore(args.cache).read("runs")
    args.out.mkdir(parents=True, exist_ok=True)
    _write(args.out / "01-スピード指数の補正.md", [_figure_table(runs)])
    print("既定の設定でスピード指数を作っています …", file=sys.stderr, flush=True)
    result = AbilityBuilder(AbilitySettings(), UNTIL).build(runs)
    _write(args.out / "02-能力指数のまとめ方.md", [_index_table(result.runs)])
    _write(args.out / "03-確かめ.md", _holdout_tables(result))
    print(f"書きました: {args.out}", file=sys.stderr)


def _figure_table(runs: pd.DataFrame) -> Table:
    rows = []
    for name, settings in FIGURE_VARIANTS.items():
        print(f"  {name} …", file=sys.stderr, flush=True)
        built = AbilityBuilder(settings, UNTIL).build(runs).runs
        consistency = FigureConsistency().score(built, *SELECT)
        rows.append([name, *consistency.values(), *IndexAccuracy().score(built, *SELECT).values()])
    columns = ["補正", "組の数", "続けた走の相関", "指数の標準偏差", "走の数", "付いた割合", "能力指数との相関", "ずれ", "ばらつき"]
    return Table(columns, _rounded(rows), title=f"スピード指数の補正（{SELECT[0]}〜{SELECT[1]} の走）",
                 note="能力指数は既定のまとめ方。補正によって当てる指数そのものも変わるので、比べる主な物差しは「続けた走の相関」")


def _index_table(runs: pd.DataFrame) -> Table:
    rows = []
    for name, change in INDEX_VARIANTS.items():
        built = AbilityIndex(replace(AbilitySettings(), **change)).build(runs)
        rows.append([name, *IndexAccuracy().score(built, *SELECT).values()])
    return Table(["まとめ方", "走の数", "付いた割合", "相関", "ずれ", "ばらつき"], _rounded(rows),
                 title=f"能力指数のまとめ方（{SELECT[0]}〜{SELECT[1]} の走。既定から1つずつ変える）", note=str(AbilitySettings()))


def _holdout_tables(result) -> list[Table]:
    runs = result.runs
    accuracy = IndexAccuracy()
    rows = [[name, *accuracy.score(runs, *period).values()] for name, period in (("選んだ期間", SELECT), ("確かめる期間", HOLDOUT))]
    tables = [Table(["期間", "走の数", "付いた割合", "相関", "ずれ", "ばらつき"], _rounded(rows), title="既定の設定の当たり具合")]
    years = [[year, *accuracy.score(runs, f"{year}-01-01", f"{year}-12-31").values()] for year in range(2014, 2027)]
    tables.append(Table(["年", "走の数", "付いた割合", "相関", "ずれ", "ばらつき"], _rounded(years), title="年ごとの当たり具合"))
    offsets = result.pace_offsets.unstack().reindex(columns=["スロー", "ミドル", "ハイ"])
    tables.append(Table(["脚質", *offsets.columns], _rounded([[i, *v] for i, v in zip(offsets.index, offsets.to_numpy().tolist())], 3),
                        title="ペース補正の大きさ（%。その分を引く。プラスは得をした走）"))
    return tables


def _rounded(rows: list[list], digits: int = 3) -> list[list]:
    return [[round(v, digits) if isinstance(v, float) else v for v in row] for row in rows]


def _write(path: Path, tables: list[Table]) -> None:
    path.write_text(render.render(tables, "markdown"), encoding="utf-8")


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.set_defaults(out=_DEFAULT_OUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="中間データの置き場")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
