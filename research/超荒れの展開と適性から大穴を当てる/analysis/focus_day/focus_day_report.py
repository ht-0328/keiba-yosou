"""詳しく見る日の表: 注目の馬（WIN5 の対象レースの勝ち馬）の順位と理由、レースごとの荒れる前提の予想・中穴と大穴の組・危険な人気馬。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import HORSE_NO, RACE_ID

#: 危険な人気馬として挙げる、4着以下の確率の市場との差の下限。
DANGER_EDGE = 0.05


@dataclass(frozen=True)
class FocusDayReport:
    """``horses`` は ``FocusDayRunner.ranks`` の表に、馬名・確定着順・確定の人気（列 horse_name・finish・final_popularity）を足したもの。
    ``pairs`` は ``PairProbability.races`` のレースの表。"""

    horses: pd.DataFrame
    pairs: pd.DataFrame

    def focus(self, picks: list[tuple[str, str, int]], title: str) -> Table:
        """``picks`` は（見出し, レースID, 馬番）の並び。"""
        rows = []
        for label, race_id, horse_no in picks:
            found = self.horses.loc[(self.horses[RACE_ID] == race_id) & (self.horses[HORSE_NO] == horse_no)]
            if found.empty:
                rows.append([label, race_id, horse_no, *[""] * 9])
                continue
            row = found.iloc[0]
            heads = int((self.horses[RACE_ID] == race_id).sum())
            rows.append([label, race_id, horse_no, row["horse_name"], f"{int(row['popularity'])}（確定 {int(row['final_popularity'])}）",
                         self._int(row["finish"]), f"{int(row['順位（新しい予想の1着）'])} / {heads}", f"{int(row['順位（今のモデルの1着）'])} / {heads}",
                         f"{row['人気帯']}の中で {int(row['人気帯の中の順位'])}位（{row['荒れる前提の確率']:.3f}）",
                         f"{row['p_win']:.3f}（市場 {row['m_win']:.3f}）", row["理由"]])
        columns = ["注目の馬", "レースID", "馬番", "馬名", "人気（締め切り前）", "着順", "新しい予想の順位（1着の確率）", "今のモデルの順位",
                   "荒れる前提の順位（確率）", "1着の確率", "理由"]
        return Table(columns, rows, title=title, note="順位は、そのレースの全頭の中で1着の確率の高い順。荒れる前提の確率は、その人気帯の中で合計 1 にそろえた1着の確率。")

    def races(self, title: str) -> Table:
        rows = []
        for race_id, race in self.horses.groupby(RACE_ID, sort=True):
            pair = self.pairs.loc[self.pairs["race_id"] == race_id]
            pair_text = f"{pair['pair'].iloc[0]}（{pair['pair_probability'].iloc[0]:.3f}）" if not pair.empty else ""
            two = f"{pair['two_or_more'].iloc[0] * 100:.1f}%" if not pair.empty else ""
            danger = race.loc[(race["popularity"] <= 3) & (race["4着以下の市場との差"] >= DANGER_EDGE)]
            podium = race.loc[race["finish"].between(1, 3)].sort_values("finish")
            rows.append([race_id, race["race_name"].iloc[0] if "race_name" in race else "", self._top(race, "中穴"), self._top(race, "大穴"), two,
                         pair_text, "、".join(f"{int(r[HORSE_NO])}（{int(r['popularity'])}人・{r['4着以下の市場との差']:+.2f}）" for _, r in danger.iterrows()),
                         "−".join(f"{int(r[HORSE_NO])}（{int(r['popularity'])}人）" for _, r in podium.iterrows())])
        columns = ["レースID", "競走名", "中穴の上位3頭（荒れる前提の確率）", "大穴の上位3頭（荒れる前提の確率）", "中穴・大穴2頭以上の確率",
                   "いちばん確率の高い中穴・大穴の組", "4着以下になりやすい人気馬（市場との差）", "実際の1〜3着"]
        return Table(columns, rows, title=title,
                     note=f"4着以下になりやすい人気馬 = 1〜3番人気で、4着以下の確率が市場の見立てより {DANGER_EDGE:.2f} 以上高い馬。人気は締め切り前の単勝オッズの順。")

    @staticmethod
    def _top(race: pd.DataFrame, band: str) -> str:
        members = race.loc[race["人気帯"] == band].sort_values("荒れる前提の確率", ascending=False).head(3)
        return "、".join(f"{int(r[HORSE_NO])}（{int(r['popularity'])}人・{r['荒れる前提の確率']:.2f}）" for _, r in members.iterrows())

    @staticmethod
    def _int(value: object) -> str:
        return "" if pd.isna(value) else str(int(value))
