"""6番人気以下の複勝を「予想 − 複勝オッズから見た3着以内率」が線以上の馬だけ買ったときの成績の表。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from 共通.render import Table

#: 予測の表の列（研究「既存モデルの改善」の walk_forward が書く名前）。
_KEYS = ["レースID", "馬ID"]
_PROBABILITY, _FOLD, _PART = "確率", "区切り", "期間"
_VALID, _TEST = "検証", "テスト"
#: 評価用の列と、比べる相手の列（複勝オッズから見た3着以内率）。
_DATE, _FINISH, _POPULARITY, _PLACE_PAYOUT, _MARKET = "開催日", "確定着順", "確定の単勝人気", "複勝の払戻", "複勝オッズの確率"
#: 買う馬の人気の下限（6番人気以下）。
MIN_POPULARITY = 6
#: 比べる線（予想が複勝オッズから見た3着以内率をどれだけ上回れば買うか）。
LINES: tuple[float, ...] = (0.0, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10)
#: 区切りごとに線を選ぶときの、検証期間で買った頭数の下限（少なすぎる線をたまたま選ばないため）。
MIN_VALID_BETS = 300


class PlaceBetReport:
    """作り方ごとに、6番人気以下の複勝を線以上の馬だけ買ったときの頭数・3着以内率・複勝の回収率を出す。

    1つめの表は線ごとの検証期間とテスト期間（と年ごと）の成績。2つめの表は、区切りごとに検証期間でいちばん回収率の高い線
    （検証で ``MIN_VALID_BETS`` 頭以上買った線の中から）を選び、その区切りのテスト期間に当てはめた成績（結果を見ずに線を決めた場合）。
    """

    def tables(self, evaluation: pd.DataFrame, predictions: Mapping[str, pd.DataFrame],
               lines: Sequence[float] = LINES) -> list[Table]:
        """``evaluation`` は ID・開催日・評価用の列と、比べる相手の列（``_MARKET``）を並べた表。予測の表に ``_MARKET`` があればそちらを使う。"""
        by_line, chosen = [], []
        for name, frame in predictions.items():
            scored = self._scored(evaluation, frame)
            for line in lines:
                bought = scored[scored["value"] >= line]
                valid, test = bought[bought[_PART] == _VALID], bought[bought[_PART] == _TEST]
                years = test.groupby(test[_DATE].dt.year)[_PLACE_PAYOUT].mean()
                by_line.append([name, f"{line:+.2f}", *self._stats(valid), *self._stats(test),
                                "・".join(f"{year}年 {value:.0f}%" for year, value in years.items())])
            chosen.append([name, *self._chosen(scored, lines)])
        return [
            Table(["作り方", "線", "検証の頭数", "検証の3着以内率", "検証の複勝回収率", "テストの頭数", "テストの3着以内率",
                   "テストの複勝回収率", "テストの年ごとの複勝回収率"], by_line, title="線ごとの6番人気以下の複勝の成績"),
            Table(["作り方", "区切りごとに選んだ線", "テストの頭数", "テストの3着以内率", "テストの複勝回収率"], chosen,
                  title="区切りごとに検証期間で線を選んだときのテスト期間の成績"),
        ]

    def _scored(self, evaluation: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
        right = evaluation.drop(columns=[_DATE] + ([_MARKET] if _MARKET in frame.columns else []))
        merged = frame.merge(right, on=_KEYS, how="inner")
        merged = merged[(merged[_POPULARITY] >= MIN_POPULARITY) & merged[_MARKET].notna()]
        return merged.assign(value=merged[_PROBABILITY] - merged[_MARKET], **{_DATE: pd.to_datetime(merged[_DATE])})

    def _stats(self, bought: pd.DataFrame) -> list[str]:
        if bought.empty:
            return ["0", "—", "—"]
        return [f"{len(bought):,}", f"{(bought[_FINISH] <= 3).mean():.1%}", f"{bought[_PLACE_PAYOUT].mean():.1f}%"]

    def _chosen(self, scored: pd.DataFrame, lines: Sequence[float]) -> list[str]:
        picked_lines, tests = [], []
        for fold, group in scored.groupby(_FOLD, sort=True):
            valid = group[group[_PART] == _VALID]
            rates = {line: valid.loc[valid["value"] >= line, _PLACE_PAYOUT].mean() for line in lines
                     if (valid["value"] >= line).sum() >= MIN_VALID_BETS}
            if not rates:
                continue
            line = max(rates, key=rates.get)
            picked_lines.append(f"{fold} {line:+.2f}")
            test = group[group[_PART] == _TEST]
            tests.append(test[test["value"] >= line])
        bought = pd.concat(tests) if tests else scored.iloc[0:0]
        return ["・".join(picked_lines), *self._stats(bought)]
