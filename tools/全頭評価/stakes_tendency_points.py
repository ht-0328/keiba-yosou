"""重賞の過去の開催から、登録馬ごとの「同じ条件の馬の成績」の文を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通 import stakes

#: 文にする最少の出走数（これより少ない条件は偶然の幅が大きいので出さない）。
MIN_RUNS = 8
#: 強み・弱みに入れる、3着以内率の全体との差（ポイント）。
GAP_POINTS = 0.05
#: 前走の人気の区切り（3番人気以内と 4番人気以下）。
_FAVORITE_LIMIT = 3


@dataclass(frozen=True)
class TendencyLine:
    """1つの条件の成績の文と、強み（True）・弱み（False）・どちらでもない（None）。"""

    text: str
    side: bool | None


class StakesTendencyPoints:
    """同じ重賞の過去の開催の出走馬（``StakesEditionRepository`` が読んだもの）から、登録馬の条件に当てはまる馬の成績を文にする。

    条件は、前走のレース名、前走の人気（3番人気以内か 4番人気以下か）、休み明け（中9週以上）、関西馬（栗東）、このレースで3着以内の経験。
    成績は 着別度数（1着-2着-3着-着外）と単勝・複勝の回収率。3着以内率が全体より ``GAP_POINTS`` 以上高ければ強み、低ければ弱み。
    出走数が ``MIN_RUNS`` に届かない条件は出さない。
    """

    def lines_of(self, editions: pd.DataFrame, horse: pd.Series, prev_race_name: str | None,
                 prev_stakes_no: str | None = None) -> list[TendencyLine]:
        """``horse`` は登録馬の事実の行（interval_days・affiliation・same_race_places_before・prev_popularity）。

        前走のレースは、重賞なら特別競走番号（``prev_stakes_no``。レース名はスポンサー名で年ごとに変わる）、それ以外はレース名で突き合わせる。
        """
        if editions.empty:
            return []
        overall = self._place_rate(editions)
        count = int(editions["race_id"].nunique())
        lines: list[TendencyLine] = []
        if prev_stakes_no and "prev_stakes_no" in editions.columns:
            rows = editions[editions["prev_stakes_no"].fillna("") == prev_stakes_no]
            lines.append(self._line(f"過去 {count} 開催で前走が{prev_race_name or '同じ重賞'}だった馬", rows, overall))
        elif prev_race_name:
            rows = editions[editions["prev_race_name"].fillna("") == prev_race_name]
            lines.append(self._line(f"過去 {count} 開催で前走が{prev_race_name}だった馬", rows, overall))
        prev_popularity = pd.to_numeric(horse.get("prev_popularity"), errors="coerce")
        if pd.notna(prev_popularity):
            is_favorite = prev_popularity <= _FAVORITE_LIMIT
            band = editions["prev_popularity"] <= _FAVORITE_LIMIT if is_favorite else editions["prev_popularity"] > _FAVORITE_LIMIT
            label = f"前走で{_FAVORITE_LIMIT}番人気以内" if is_favorite else f"前走で{_FAVORITE_LIMIT + 1}番人気以下"
            lines.append(self._line(f"過去 {count} 開催で{label}だった馬", editions[band.fillna(False)], overall))
        interval = pd.to_numeric(horse.get("interval_days"), errors="coerce")
        if pd.notna(interval) and interval >= stakes.REST_INTERVAL_DAYS:
            rows = editions[editions["interval_days"] >= stakes.REST_INTERVAL_DAYS]
            lines.append(self._line(f"過去 {count} 開催で休み明け（中9週以上）の馬", rows, overall))
        if horse.get("affiliation") == "栗東":
            lines.append(self._line(f"過去 {count} 開催で関西馬（栗東）", editions[editions["affiliation"] == "栗東"], overall))
        if pd.to_numeric(horse.get("same_race_places_before"), errors="coerce") >= 1:
            rows = editions[editions["same_race_places_before"] >= 1]
            lines.append(self._line(f"過去 {count} 開催でこのレースで3着以内の経験がある馬", rows, overall))
        return [line for line in lines if line is not None]

    def _line(self, label: str, rows: pd.DataFrame, overall: float) -> TendencyLine | None:
        if len(rows) < MIN_RUNS:
            return None
        finish = pd.to_numeric(rows["finish"], errors="coerce")
        first, second, third = int((finish == 1).sum()), int((finish == 2).sum()), int((finish == 3).sum())
        out = len(rows) - first - second - third
        rate = (first + second + third) / len(rows)
        win_back = pd.to_numeric(rows["win_payout"], errors="coerce").fillna(0).sum() / (100 * len(rows))
        place_back = pd.to_numeric(rows["place_payout"], errors="coerce").fillna(0).sum() / (100 * len(rows))
        text = (f"{label}は {first}-{second}-{third}-{out}（3着以内率 {rate:.0%}、全体 {overall:.0%}。"
                f"単勝回収率 {win_back:.0%}・複勝回収率 {place_back:.0%}）")
        side: bool | None = None
        if rate >= overall + GAP_POINTS:
            side = True
        elif rate <= overall - GAP_POINTS:
            side = False
        return TendencyLine(text, side)

    def _place_rate(self, rows: pd.DataFrame) -> float:
        finish = pd.to_numeric(rows["finish"], errors="coerce")
        return float(finish.between(1, 3).mean()) if len(rows) else 0.0
