"""研究「AIとロジックの予想」: 騎手の暗黙の了解から作ったロジックの候補（見送り・買い足し）と、期間ごとの成績。

    uv run python research/AIとロジックの予想/analysis/convention_candidates.py            # 探す期間（参考1・参考2・作る）
    uv run python research/AIとロジックの予想/analysis/convention_candidates.py --verify   # 確かめる期間と追加の確かめの期間（選んだ候補だけ）

比べる相手は今の AI＋ロジック予想（展開のロジックとクラスのロジックで見送ったあとの、印の買い目）。``convention_materials.py`` の ``convention.pkl`` を読む。
- 見送り: 今の AI＋ロジックが買うレースのうち、条件に当たるレースを見送る。
- 買い足し: 今の AI＋ロジックが買わないレース（AI が見込み 100% 未満で買わない・ロジックで見送った）のうち、条件に当たるレースを買う。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import convention_materials  # noqa: E402
import logic_candidates  # noqa: E402
import logic_rules  # noqa: E402
import logic_scan  # noqa: E402

_BACK_STYLES = ("差し", "追込")
#: 後ろから位置を上げる割合がこの値以下の騎手を「途中で動かない騎手」と見る。
STAY_RATE = 0.08
#: 買い足しで要る、印の買い目の見込みの回収率。
ADD_EXPECTED = 0.9

Rule = Callable[[pd.DataFrame], pd.Series]


def top_is_back(t: pd.DataFrame) -> pd.Series:
    return t["top_style"].isin(_BACK_STYLES)


def top_leads_unchallenged(t: pd.DataFrame) -> pd.Series:
    """◎ が逃げの候補で、◎ より人気のある逃げの候補がいない（人気の逃げ馬に行かせる、の形）。"""
    return (t["top_style"] == "逃げ") & (t["top_popularity"] <= t["best_lead_pop"])


#: 見送りの候補（真が見送り）。
SKIPS: dict[str, Rule] = {
    "◎が差し・追込で、騎手が途中で動かない": lambda t: top_is_back(t) & (t["top_move_rate"] <= STAY_RATE),
    "◎が差し・追込で、人気の前の馬が2頭以上": lambda t: top_is_back(t) & (t["front_popular"] >= 2),
    "減量の騎手の逃げの候補がいる": lambda t: t["lead_apprentices"] > 0,
    "◎が先行で、騎手が61位以下": lambda t: (t["top_style"] == "先行") & (t["top_jockey_class"] == "61-"),
}
#: 買い足しの候補（真が買い足し）。「（比べる）」は、逃げの候補でない ◎ で同じ線を使ったとき。
ADDS: dict[str, Rule] = {
    "◎が逃げの候補で、より人気の逃げの候補がいない": top_leads_unchallenged,
    "同じで、◎が3番人気以内": lambda t: top_leads_unchallenged(t) & (t["top_popularity"] <= 3),
    f"同じで、見込み {ADD_EXPECTED} 以上": lambda t: top_leads_unchallenged(t) & (t["f_expected"] >= ADD_EXPECTED),
    f"（比べる）◎が逃げの候補でなく、見込み {ADD_EXPECTED} 以上": lambda t: (t["top_style"] != "逃げ") & (t["f_expected"] >= ADD_EXPECTED),
}
#: 確かめる期間で数える候補（探す期間で選んだもの）。
VERIFY_SKIPS: tuple[str, ...] = ("◎が差し・追込で、騎手が途中で動かない", "◎が先行で、騎手が61位以下")
VERIFY_ADDS: tuple[str, ...] = (f"同じで、見込み {ADD_EXPECTED} 以上", f"（比べる）◎が逃げの候補でなく、見込み {ADD_EXPECTED} 以上")


def bought_now(t: pd.DataFrame) -> pd.Series:
    """今の AI＋ロジック予想が買うレース。"""
    return t["bought"] & logic_rules.slow_pace(t) & ~t["class_name"].isin(logic_candidates.OPEN_CLASSES)


def metrics(stake: pd.Series, back: pd.Series, days: int) -> dict[str, float]:
    """買う数・回収率・的中率・1日の儲け。"""
    return {"買う": len(stake), "回収率": back.sum() / stake.sum() if stake.sum() else float("nan"),
            "的中率": (back > 0).mean() if len(back) else float("nan"), "1日の儲け": (back.sum() - stake.sum()) / days}


def skipped(t: pd.DataFrame, rule: Rule) -> tuple[dict[str, float], dict[str, float]]:
    """見送ったあとの成績と、見送ったレースの成績。"""
    now, days = t[bought_now(t)], t["day"].nunique()
    skip = rule(now).fillna(False).astype(bool)
    return metrics(now.loc[~skip, "stake"], now.loc[~skip, "back"], days), metrics(now.loc[skip, "stake"], now.loc[skip, "back"], days)


def added(t: pd.DataFrame, rule: Rule) -> tuple[dict[str, float], dict[str, float]]:
    """買い足したあとの成績と、買い足したレースの成績。"""
    keep, days = bought_now(t), t["day"].nunique()
    more = t[~keep & rule(t).fillna(False).astype(bool) & t["f_stake"].notna()]
    stake, back = pd.concat([t.loc[keep, "stake"], more["f_stake"]]), pd.concat([t.loc[keep, "back"], more["f_back"]])
    return metrics(stake, back, days), metrics(more["f_stake"], more["f_back"], days)


def _line(name: str, kind: str, after: dict[str, float], part: dict[str, float], base: dict[str, float]) -> str:
    return (f"  {name}: {kind} {part['買う']}（回収率 {part['回収率']:.0%}・的中率 {part['的中率']:.0%}） → 回収率 {after['回収率']:.1%}（{after['回収率'] - base['回収率']:+.1%}） "
            f"的中率 {after['的中率']:.1%}（{after['的中率'] - base['的中率']:+.1%}） 1日の儲け {after['1日の儲け']:,.0f}円（{after['1日の儲け'] - base['1日の儲け']:+,.0f}）")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true", help="確かめる期間を数える（選んだ候補だけを見る）")
    args = parser.parse_args()
    parts = pd.read_pickle(convention_materials.PATH)
    skips = {name: SKIPS[name] for name in VERIFY_SKIPS} if args.verify else SKIPS
    adds = {name: ADDS[name] for name in VERIFY_ADDS} if args.verify else ADDS
    for part in logic_candidates.VERIFY if args.verify else logic_scan.SEARCH:
        table = parts[part]
        now = table[bought_now(table)]
        base = metrics(now["stake"], now["back"], table["day"].nunique())
        print(f"{part} 今（AI＋ロジック） 買う {base['買う']} 回収率 {base['回収率']:.1%} 的中率 {base['的中率']:.1%} 1日の儲け {base['1日の儲け']:,.0f}円")
        for name, rule in skips.items():
            print(_line(name, "見送り", *skipped(table, rule), base))
        for name, rule in adds.items():
            print(_line(name, "買い足し", *added(table, rule), base))


if __name__ == "__main__":
    main()
