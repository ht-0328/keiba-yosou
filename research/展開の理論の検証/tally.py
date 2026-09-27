"""ペースの測り方・脚質の分け方・逃げたい馬の数え方を比べ、成績を数える（研究「展開の理論の検証」の入口③）。

    uv run python research/展開の理論の検証/tally.py

先に extract.py で中間データを作っておく。2014年からの全レースで数え、``reports/展開の理論の検証/集計/`` に次の3つを書く。

- 01-測り方と分け方の比べ.md: ペースの測り方3通り × 脚質の分け方4通りの「展開の効き目」と、それぞれの成績の表
- 02-内訳（<測り方>・<脚質の分け方>）.md: ``--measure`` と ``--style`` で選んだ組み合わせの、人気・芝ダ・距離・競馬場・頭数・年ごとの効き目
- 03-逃げたい馬の数え方の比べ.md: 数え方ごとに、実際のペースをどれだけ当てるか
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 展開の理論の検証.analysis.cache_store import CacheStore  # noqa: E402
from 展開の理論の検証.analysis.leaders import COUNTS, EarlyRunHistory, LeaderCountTable  # noqa: E402
from 展開の理論の検証.analysis.pace import (  # noqa: E402
    FIRST_HALF_BY_CONDITION,
    MEASURES,
    NO_BASELINE,
    PACE_ORDER,
    PaceMeasureTable,
)
from 展開の理論の検証.analysis.tally import (  # noqa: E402
    VARIANTS,
    LeaderPaceScore,
    MarketWinProbability,
    PaceEffectScore,
    PerformanceTally,
    StyleColumns,
)
from 展開の理論の検証.extract import DEFAULT_CACHE  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUT = _REPO_ROOT / "reports" / "展開の理論の検証" / "集計"
#: 数える最初の年（前半タイムの基準に前の3年がそろう年）。
_FIRST_YEAR = 2014
#: 内訳の切り口: 名前 → 出走の表から値を作る関数。
_SPLITS = {
    "人気": lambda r: pd.cut(r["popularity"], [0, 3, 6, 99], labels=["1〜3番人気", "4〜6番人気", "7番人気以下"]),
    "芝ダ": lambda r: r["surface"],
    "距離": lambda r: pd.cut(r["distance_m"], [0, 1400, 1800, 9999], labels=["1400m以下", "1500〜1800m", "1900m以上"]),
    "競馬場": lambda r: r["venue"],
    "頭数": lambda r: pd.cut(r["field_size"], [0, 10, 14, 18], labels=["10頭以下", "11〜14頭", "15頭以上"]),
    "クラス": lambda r: r["class_name"],
    "年": lambda r: r["year"],
}


def main(args) -> None:
    store = CacheStore(args.cache)
    print("中間データを読み、材料を作っています …", file=sys.stderr, flush=True)
    runners = _runners_with_history(store)
    races = PaceMeasureTable().build(store.read("races"))
    races = races.merge(LeaderCountTable().build(runners), on="race_id", how="left")
    races = races[races["year"] >= _FIRST_YEAR]
    runners = runners[runners["year"] >= _FIRST_YEAR].merge(
        races[["race_id", *MEASURES, *(f"{m}（z）" for m in MEASURES)]], on="race_id")
    args.out.mkdir(parents=True, exist_ok=True)
    variant = next(v for v in VARIANTS if v.name == args.style)
    _write(args.out / "01-測り方と分け方の比べ.md", _comparison(races, runners))
    _write(args.out / f"02-内訳（{args.measure}・{args.style}）.md", _breakdown(runners, args.measure, variant))
    _write(args.out / "03-逃げたい馬の数え方の比べ.md", _leaders(races))
    print(f"書きました: {args.out}", file=sys.stderr)


def _runners_with_history(store: CacheStore) -> pd.DataFrame:
    runners = EarlyRunHistory().build(store.read("runners"))
    return MarketWinProbability().build(StyleColumns().build(runners))


def _comparison(races: pd.DataFrame, runners: pd.DataFrame) -> list[Table]:
    shares = [[m, *[(races[m] == p).mean() * 100 for p in (*PACE_ORDER, NO_BASELINE)]] for m in MEASURES]
    tables = [Table(["測り方", *PACE_ORDER, NO_BASELINE], _rounded(shares), title=f"ペースの区分の割合（%、{len(races)}レース）")]
    score = PaceEffectScore()
    rows = [[m, v.name, "結果" if v.after_race else "レース前", *score.score(runners, m, v).values()]
            for m in MEASURES for v in VARIANTS]
    tables.append(Table(["測り方", "脚質の分け方", "分かる時点", *score.score(runners, MEASURES[0], VARIANTS[0])],
                        _rounded(rows), title="展開の効き目（前−後ろの差が、スローとハイでどれだけ違うか。ポイント）"))
    tables += [_detail(runners, m, v) for m in MEASURES for v in VARIANTS]
    return tables


def _detail(runners: pd.DataFrame, measure: str, variant) -> Table:
    table = PerformanceTally().tally(runners, [variant.name, measure])
    table = table.reindex(pd.MultiIndex.from_product([variant.groups, PACE_ORDER])).dropna(how="all")
    rows = [[style, pace, *values] for (style, pace), values in zip(table.index, table.to_numpy().tolist())]
    return Table(["脚質", "ペース", *table.columns], _rounded(rows), title=f"{measure} × {variant.name}")


def _breakdown(runners: pd.DataFrame, measure: str, variant) -> list[Table]:
    score = PaceEffectScore()
    tables = [_detail(runners, measure, variant)]
    for name, split in _SPLITS.items():
        values = split(runners)
        rows = [[value, int((values == value).sum()), *score.score(runners[values == value], measure, variant).values()]
                for value in pd.unique(values.dropna())]
        tables.append(Table([name, "頭数", *score.score(runners, measure, variant)], _rounded(rows),
                            title=f"{name}ごとの展開の効き目（{measure} × {variant.name}）"))
    popularity = _SPLITS["人気"](runners)
    detail = PerformanceTally().tally(runners.assign(人気帯=popularity), ["人気帯", variant.name, measure])
    rows = [[*index, *values] for index, values in zip(detail.index, detail.to_numpy().tolist())]
    tables.append(Table(["人気帯", "脚質", "ペース", *detail.columns], _rounded(rows), title="人気帯 × 脚質 × ペースの成績"))
    return tables


def _leaders(races: pd.DataFrame) -> list[Table]:
    score = LeaderPaceScore()
    tables = []
    for measure in MEASURES:
        decided = races[races[measure] != NO_BASELINE]
        rows = [[name, COUNTS[name], *_rounded([list(score.score(decided, name, f"{measure}（z）", measure).values())], 3)[0]]
                for name in COUNTS]
        tables.append(Table(["数え方", "中身", *score.score(decided, next(iter(COUNTS)), f"{measure}（z）", measure)],
                            rows, title=f"逃げたい馬の数え方と、実際のペース（{measure}）"))
    decided = races[races[FIRST_HALF_BY_CONDITION] != NO_BASELINE]
    for name in [n for n in COUNTS if "合計" not in n]:
        capped = decided[name].clip(upper=4)
        shares = pd.crosstab(capped, decided[FIRST_HALF_BY_CONDITION], normalize="index") * 100
        rows = [[f"{int(c)}頭" + ("以上" if c == 4 else ""), int((capped == c).sum()),
                 *[shares.loc[c].get(p, 0.0) for p in PACE_ORDER]] for c in shares.index]
        tables.append(Table(["頭数", "レース数", *PACE_ORDER], _rounded(rows),
                            title=f"{name}の頭数ごとのペースの割合（%、{FIRST_HALF_BY_CONDITION}）"))
    return tables


def _rounded(rows: list[list], digits: int = 1) -> list[list]:
    return [[round(v, digits) if isinstance(v, float) else v for v in row] for row in rows]


def _write(path: Path, tables: list[Table]) -> None:
    path.write_text(render.render(tables, "markdown"), encoding="utf-8")


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.set_defaults(out=_DEFAULT_OUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="中間データの置き場")
    parser.add_argument("--measure", default=FIRST_HALF_BY_CONDITION, choices=MEASURES, help="内訳で使うペースの測り方")
    parser.add_argument("--style", default=VARIANTS[0].name, choices=[v.name for v in VARIANTS], help="内訳で使う脚質の分け方")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
