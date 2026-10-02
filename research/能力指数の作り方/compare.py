"""スピード指数の補正と、能力指数のまとめ方の候補を比べる（研究「能力指数の作り方」の入口②）。

    uv run python research/能力指数の作り方/compare.py

先に extract.py で中間データを作っておく。基準タイム・ペースの基準・ペース補正の大きさは 2023年までのレースで求め、
候補を選ぶのは 2016〜2023年の走、選んだものを確かめるのは 2024年からの走（選ぶのに使っていない期間）。
``reports/能力指数の作り方/比べ/`` に次を書く。

- 01-スピード指数の補正.md: 補正を1つずつ足したときの、同じ馬の続けた走どうしの指数の相関
- 02-能力指数のまとめ方.md: まとめ方・近走の数・期間・適性を1つずつ変えたときの、能力指数とその走の指数の相関
- 03-確かめ.md: 既定の設定（``AbilitySettings``）の、2024年からの走での当たり具合と、年ごとの当たり具合
- 04-血統で補う.md: 初めての条件（距離帯・競馬場・芝ダ・馬場の組）の適性を、血統で補う前と後の当たり具合
- 05-年ごとの当たり具合.md: 年ごとの相関を、馬どうしの差の広がりと外れ方に分けたものと、原因の候補ごとの比べ
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, render  # noqa: E402
from 共通.ability import (  # noqa: E402
    COURSE, DISTANCE, FIELD_LEVEL, FIGURE, FIRST_KINDS, FIRST_SURFACE, GOING, AbilityBuilder, AbilityIndex, AbilitySettings, FirstConditions,
    PedigreeAptitude,
)
from 共通.render import Table  # noqa: E402

from 展開の理論の検証.analysis.cache_store import CacheStore  # noqa: E402
from 能力指数の作り方.analysis import (  # noqa: E402
    REFORM_DAY, AccuracyBreakdown, EraRaceTable, FigureConsistency, IndexAccuracy,
)
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
#: 血統で補う候補（補う前の既定の設定から変える）。4つの条件を全部補う候補と、芝ダだけ補う候補。
_ALL_KINDS = {"pedigree_kinds": FIRST_KINDS}
_SURFACE_ONLY = {"pedigree_kinds": (FIRST_SURFACE,)}
PEDIGREE_VARIANTS: dict[str, dict] = {
    "補う前": {"pedigree": ()},
    **{f"4つの条件・父・寄せる強さ {p:g}": {"pedigree": ("sire",), "pedigree_prior": p, **_ALL_KINDS} for p in (5.0, 20.0, 80.0)},
    **{f"4つの条件・父と母の父・寄せる強さ {p:g}": {"pedigree": ("sire", "damsire"), "pedigree_prior": p, **_ALL_KINDS}
       for p in (20.0, 80.0)},
    **{f"芝ダだけ・父・寄せる強さ {p:g}": {"pedigree": ("sire",), "pedigree_prior": p, **_SURFACE_ONLY} for p in (20.0, 80.0)},
    **{f"芝ダだけ・父と母の父・寄せる強さ {p:g}": {"pedigree": ("sire", "damsire"), "pedigree_prior": p, **_SURFACE_ONLY}
       for p in (10.0, 20.0, 40.0, 80.0)},
}
#: 年ごとの期間。2019年は、降級制度の廃止（6月）の前と後に分ける。
YEAR_PERIODS: list[tuple[str, str, str]] = [
    *[(str(y), f"{y}-01-01", f"{y}-12-31") for y in range(2014, 2019)],
    ("2019（1〜5月）", "2019-01-01", "2019-05-31"), ("2019（6〜12月）", "2019-06-01", "2019-12-31"),
    *[(str(y), f"{y}-01-01", f"{y}-12-31") for y in range(2020, 2027)],
]
#: 原因の候補ごとに比べる期間。無観客の開催は 2020年2月29日〜10月9日。
CAUSE_PERIODS: list[tuple[str, str, str]] = [
    ("降級制度の廃止の前（2014年1月〜2019年5月）", "2014-01-01", "2019-05-31"),
    ("降級制度の廃止の後（2019年6月〜）", "2019-06-01", "2026-12-31"),
    ("無観客の開催（2020年2月29日〜10月9日）", "2020-02-29", "2020-10-09"),
    ("無観客の後（2020年10月10日〜2021年12月）", "2020-10-10", "2021-12-31"),
]
#: 年ごとに指数の平均を並べるレースの水準。
LEVELS: tuple[str, ...] = ("未勝利・3歳", "1勝クラス・古馬", "2勝クラス・古馬", "3勝クラス・古馬")


def main(args) -> None:
    runs = CacheStore(args.cache).read("runs")
    args.out.mkdir(parents=True, exist_ok=True)
    _write(args.out / "01-スピード指数の補正.md", [_figure_table(runs)])
    print("既定の設定でスピード指数を作っています …", file=sys.stderr, flush=True)
    result = AbilityBuilder(AbilitySettings(), UNTIL).build(runs)
    _write(args.out / "02-能力指数のまとめ方.md", [_index_table(result.runs)])
    _write(args.out / "03-確かめ.md", _holdout_tables(result))
    print("血統で補う前と後を比べています …", file=sys.stderr, flush=True)
    _write(args.out / "04-血統で補う.md", _pedigree_tables(result.runs))
    print("年ごとの当たり具合を分けています …", file=sys.stderr, flush=True)
    _write(args.out / "05-年ごとの当たり具合.md", _yearly_tables(runs, result))
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


def _pedigree_tables(runs: pd.DataFrame) -> list[Table]:
    plain = AbilityIndex(AbilitySettings()).build(runs)
    flagged = FirstConditions(replace(AbilitySettings(), **_ALL_KINDS)).build(plain)
    first = flagged[list(FIRST_KINDS)].any(axis=1)
    accuracy = IndexAccuracy()
    overall, by_kind = [], []
    for name, change in PEDIGREE_VARIANTS.items():
        print(f"  {name} …", file=sys.stderr, flush=True)
        settings = replace(AbilitySettings(), **change)
        filled = PedigreeAptitude(settings).fit(flagged).fill(flagged) if settings.pedigree else flagged
        for period_name, period in (("選んだ期間", SELECT), ("確かめる期間", HOLDOUT)):
            whole, firsts = accuracy.score(filled, *period), accuracy.score(filled[first], *period)
            overall.append([name, period_name, whole["相関"], whole["ばらつき"], firsts["走の数"], firsts["相関"],
                            firsts["ずれ"], firsts["ばらつき"]])
            by_kind += [[kind, name, period_name, *accuracy.score(filled[flagged[kind]], *period).values()]
                        for kind in FIRST_KINDS]
    by_kind.sort(key=lambda row: (FIRST_KINDS.index(row[0]), row[2]))
    return [
        Table(["補い方", "期間", "全部の走の相関", "全部の走のばらつき", "初めての条件の走の数", "その相関", "そのずれ", "そのばらつき"],
              _rounded(overall, 4), title="血統で補う前と後の当たり具合",
              note="初めての条件の走 = 近走に同じ距離帯・競馬場・芝ダ・馬場の組の走が無かった走（どれか1つでも）。"
                   f"既定は pedigree={AbilitySettings().pedigree}・pedigree_prior={AbilitySettings().pedigree_prior:g}・"
                   f"pedigree_kinds={AbilitySettings().pedigree_kinds}"),
        Table(["初めての条件", "補い方", "期間", "走の数", "付いた割合", "相関", "ずれ", "ばらつき"], _rounded(by_kind, 4),
              title="初めての条件の種類ごとの当たり具合"),
    ]


def _yearly_tables(runs: pd.DataFrame, result) -> list[Table]:
    levelled = _with_level(result)
    breakdown = AccuracyBreakdown()
    columns = ["期間", *breakdown.score(levelled, *SELECT)]
    years = [[name, *breakdown.score(levelled, first, last).values()] for name, first, last in YEAR_PERIODS]
    causes = [[name, *breakdown.score(levelled, first, last).values()] for name, first, last in CAUSE_PERIODS]
    means = [[name, *_level_means(levelled, first, last)] for name, first, last in YEAR_PERIODS]
    print("  水準の差を降級制度の廃止の前後で分けて、指数を作り直しています …", file=sys.stderr, flush=True)
    era = _with_level(AbilityBuilder(AbilitySettings(), UNTIL, EraRaceTable()).build(runs))
    eras = [*_era_rows("1つで求める（既定）", levelled), *_era_rows("廃止の前後で分ける", era)]
    return [
        Table(columns, _rounded(years), title="年ごとの当たり具合と、相関を決める量",
              note="相関は、外れ方（ばらつき）が同じでも、馬どうしの差（指数の広がり）が小さいと下がる"),
        Table(["期間", *LEVELS], _rounded(means, 2), title="レースの水準ごとの、スピード指数の平均"),
        Table(columns, _rounded(causes), title="原因の候補ごとの期間の比べ"),
        Table(["レースの水準の差", "降級制度の廃止の", "続けた走の相関", "相関", "ばらつき", "指数の広がり"], _rounded(eras),
              title="基準タイムの作り方: レースの水準の差を、降級制度の廃止の前後で分けて求めたとき"),
    ]


def _with_level(result) -> pd.DataFrame:
    """出走の表に、レースの水準の列を足す。"""
    return result.runs.merge(result.races[["race_id", FIELD_LEVEL]], on="race_id", how="left")


def _level_means(runs: pd.DataFrame, first: str, last: str) -> list[float]:
    chosen = runs[runs["race_date"].between(pd.Timestamp(first), pd.Timestamp(last))]
    return chosen.groupby(FIELD_LEVEL)[FIGURE].mean().reindex(list(LEVELS)).tolist()


def _era_rows(name: str, runs: pd.DataFrame) -> list[list]:
    """降級制度の廃止の前と後の、続けた走の相関・相関・ばらつき・指数の広がり。"""
    before = (REFORM_DAY - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    halves = (("前", "2014-01-01", before), ("後", REFORM_DAY.strftime("%Y-%m-%d"), HOLDOUT[1]))
    rows = []
    for half, first, last in halves:
        score = AccuracyBreakdown().score(runs, first, last)
        consistency = FigureConsistency().score(runs, first, last)["続けた走の相関"]
        rows.append([name, half, consistency, score["相関"], score["ばらつき"], score["指数の広がり"]])
    return rows


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
