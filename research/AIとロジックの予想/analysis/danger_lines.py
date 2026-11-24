"""研究「AIとロジックの予想」: 消（危険な人気馬）の決まり（線と足す材料）を人気帯ごとに変えたときの、消の成績を期間ごとに出す。

    uv run python research/AIとロジックの予想/analysis/danger_lines.py            # 危険度の帯ごとの成績と、決まりの組ごとの消の成績
    uv run python research/AIとロジックの予想/analysis/danger_lines.py --flags    # 道具「印の成績」に渡す消の表も書く

読むのは研究「裏目を買うかの予想」の印の表（``reports/裏目を買うかの予想/marked.pkl``。1行 = 1頭。人気馬には危険度が付いている）。
元DB は開かない。危険度 = 予想の4着以下の確率 − 市場から見た4着以下の確率。

出すもの: (1) 人気帯 × 危険度の帯ごとの、頭数と「実際の3着以内率 − 市場から見た3着以内率」（ポイント）と複勝の回収率、
(2) 決まりの組（``RULE_SETS``）ごとの、消の頭数・勝率・3着以内率・単勝と複勝の回収率（人気帯ごと）。
``--flags`` は決まりの組ごとに ``reports/AIとロジックの予想/消/flags_<名前>.pkl`` を書く。道具「印の成績」の ``--danger-flags`` に渡すと、
その消で印を付け直した全券種の買い目の成績が出る（``danger_tickets.py --kinds`` で比べる）。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import danger_cancel  # noqa: E402

#: いちばん優先する人気帯（本番の ``DangerPicker`` と同じ。この人気帯の馬が線以上なら、その馬だけを消にする）。
FIRST_BAND = "1番人気"


@dataclass(frozen=True)
class BandRule:
    """1つの人気帯の消の決まり。点が ``line`` 以上の馬を危険とする。

    点は危険度。``with_form`` なら、全頭の予想が市場より低く見る度合い（市場から見た3着以内率 − 予想の3着以内の確率）を足す。
    ``win_below_market`` なら、1着の予想が市場の見立てより低い馬だけを危険とする。
    """

    line: float
    with_form: bool = False
    win_below_market: bool = False

    def margin(self, horses: pd.DataFrame) -> pd.Series:
        """点 − 線（0 以上なら危険）。``win_below_market`` に合わない馬は NaN。"""
        score = horses["danger_score"] + ((horses["market_top3"] - horses["probability"]) if self.with_form else 0.0)
        margin = score - self.line
        return margin.where(horses["win_probability"] < horses["market_win"]) if self.win_below_market else margin


#: 比べる決まりの組（名前 → 人気帯 → 決まり）。決まりの無い人気帯は消にしない。「本番の線」は今の当日の線。
RULE_SETS: dict[str, dict[str, BandRule]] = {
    "本番の線": {"1番人気": BandRule(0.12), "4〜5番人気": BandRule(0.01)},
    "1番人気だけ": {"1番人気": BandRule(0.12)},
    "4〜5番人気は4ポイント": {"1番人気": BandRule(0.12), "4〜5番人気": BandRule(0.04)},
    "全頭の予想も低い": {"1番人気": BandRule(0.12), "2〜3番人気": BandRule(0.16, with_form=True), "4〜5番人気": BandRule(0.08, with_form=True)},
    "全頭の予想も低い・1番人気は1着の予想も低い": {"1番人気": BandRule(0.12, win_below_market=True),
                               "2〜3番人気": BandRule(0.16, with_form=True), "4〜5番人気": BandRule(0.08, with_form=True)},
    "1番人気も全頭の予想を足す": {"1番人気": BandRule(0.24, with_form=True), "2〜3番人気": BandRule(0.16, with_form=True),
                      "4〜5番人気": BandRule(0.08, with_form=True)},
}
#: 危険度の帯の境目。
EDGES: tuple[float, ...] = (-1.0, 0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 1.0)
_FLAG_COLUMNS = ["race_id", "horse_id", "favorite_band", "is_danger"]


def picked(favorites: pd.DataFrame, rules: Mapping[str, BandRule]) -> pd.Series:
    """レースごとに消にする馬を1頭だけ選ぶ（本番と同じ決まり）。``favorites`` は人気馬の行（race_id・favorite_band と点の材料の列）。

    1番人気が線以上ならその馬。そうでなければ、線以上のほかの人気帯の馬のうち、線をいちばん大きく超えた馬。
    """
    margin = pd.Series(float("nan"), index=favorites.index)
    for band, rule in rules.items():
        inside = favorites["favorite_band"] == band
        margin[inside] = rule.margin(favorites[inside])
    over = favorites[margin >= 0].assign(margin=margin[margin >= 0])
    first = over[over["favorite_band"] == FIRST_BAND]
    rest = over[~over["race_id"].isin(first["race_id"])]
    best = rest.sort_values("margin", ascending=False).drop_duplicates("race_id")
    return favorites.index.isin(first.index.union(best.index))


def band_table(favorites: pd.DataFrame, band: str) -> pd.DataFrame:
    """1つの人気帯の、危険度の帯 × 期間の表（頭数・実際の3着以内率 − 市場から見た3着以内率・複勝の回収率）。"""
    inside = favorites[favorites["favorite_band"] == band]
    days = pd.to_datetime(inside["race_date"])
    columns = {}
    for name, start, end in danger_cancel.PERIODS:
        rows = inside[(days >= start) & (days < end)]
        columns[name] = rows.groupby(pd.cut(rows["danger_score"], list(EDGES)), observed=False).apply(_cell, include_groups=False)
    return pd.DataFrame(columns)


def _cell(horses: pd.DataFrame) -> str:
    if horses.empty:
        return "0頭"
    gap = (horses["finish"] <= 3).mean() - (1 - horses["market_out"]).mean()
    return f"{len(horses)}頭 {gap * 100:+.1f} 複 {horses['place_payout'].fillna(0).mean():.1f}%"


def rule_set_table(favorites: pd.DataFrame, rules: Mapping[str, BandRule]) -> pd.DataFrame:
    """1つの決まりの組の、期間 × 人気帯ごとの消の成績（頭数・勝率・3着以内率・単勝と複勝の回収率）。"""
    dangers = favorites[picked(favorites, rules)]
    days = pd.to_datetime(dangers["race_date"])
    rows = []
    for name, start, end in danger_cancel.PERIODS:
        inside = dangers[(days >= start) & (days < end)]
        for band, horses in inside.groupby("favorite_band", sort=True):
            rows.append({"期間": name, "人気帯": band, **danger_cancel.stats(horses),
                         "複勝の回収率": horses["place_payout"].fillna(0).mean() / 100})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--flags", action="store_true", help="道具「印の成績」に渡す消の表も書く")
    args = parser.parse_args()
    marked = pd.read_pickle(danger_cancel.MARKED)
    favorites = marked[marked["favorite_band"].notna() & marked["danger_score"].notna()]
    pd.set_option("display.width", 250)
    for band in sorted(favorites["favorite_band"].unique()):
        print(f"== {band}（危険度の帯ごと。頭数・実際の3着以内率 − 市場から見た3着以内率（ポイント）・複勝の回収率）")
        print(band_table(favorites, band).to_string())
    rates = dict.fromkeys(("勝率", "3着以内率", "単勝の回収率", "複勝の回収率"), "{:.1%}".format)
    for name, rules in RULE_SETS.items():
        print(f"== 消の成績: {name}")
        print(rule_set_table(favorites, rules).to_string(index=False, formatters=rates))
        if args.flags:
            danger_cancel.OUT.mkdir(parents=True, exist_ok=True)
            favorites[picked(favorites, rules)].assign(is_danger=True)[_FLAG_COLUMNS].to_pickle(danger_cancel.OUT / f"flags_{name}.pkl")
    if args.flags:
        print(f"消の表を {danger_cancel.OUT} に書いた")


if __name__ == "__main__":
    main()
