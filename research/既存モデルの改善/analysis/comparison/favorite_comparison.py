"""人気馬の4着以下の予想の、比べ方の表（人気帯ごと・危険の判定）。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.favorites_out_of_top3.danger import DangerThreshold
from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND, FavoriteBand
from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import POPULARITY

from ..scores import BinaryScores
from ..walk_forward import PART, PART_TEST, PART_VALID, PREDICTION_COLUMN, WINDOW
from ..windows import TestWindow
from .prediction_join import BASE_PROBABILITY, LABEL, PredictionJoin
from .table_formatter import TableFormatter

#: 作り方の鍵（variant_catalog と同じ）。
CURRENT, ODDS_ONLY, ODDS_BASELINE, IMPROVED = "current", "odds_only", "odds_baseline", "improved"
#: 現行の報告で使っていた「危険」の線（4着以下の確率 60% 以上）。
_OLD_DANGER = 0.6
#: 危険度（予想 − 基準）の列の名前。
DANGER = "危険度"


class FavoriteComparison:
    """人気馬の4着以下の予想を、人気帯ごとに比べ、危険の判定が「同じ人気の馬全体」より当たるかを見る表を作る
    （既存モデルの修正計画の 3「人気馬」）。

    採用の基準（計画の 3）: 1番人気にも有効な判定ができ、件数と複数期間の結果で裏付けられること。
    危険の判定の数を増やすだけでは改善としない。
    変更版の危険の判定は「危険度 = 4着以下の確率 − オッズから見た4着以下の確率」が線以上。線は人気帯ごとに、
    区切りごとの検証期間で決める（``DangerThreshold``）。現行は「4着以下の確率 60% 以上」（現行の報告の線）。
    """

    def __init__(self, data: TrainingData, predictions: Mapping[str, pd.DataFrame], names: Mapping[str, str],
                 windows: tuple[TestWindow, ...]) -> None:
        join = PredictionJoin(data)
        self._joined = {key: self._with_danger(join.of(frame)) for key, frame in predictions.items()}
        self._names = dict(names)
        self._windows = windows
        self._format = TableFormatter()

    def tables(self) -> list[Table]:
        bands = [band.label for band in FavoriteBand]
        return [self._by_window(band) for band in bands] + [self._pooled()] + [
            self._danger_table(CURRENT), self._danger_table(ODDS_BASELINE), self._danger_table(IMPROVED),
            self._first_favorite_by_window(),
        ]

    def _with_danger(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame.assign(**{DANGER: frame[PREDICTION_COLUMN] - frame[BASE_PROBABILITY]})

    def _rows(self, key: str, part: str = PART_TEST) -> pd.DataFrame:
        frame = self._joined[key]
        return frame[frame[PART] == part]

    def _by_window(self, band: str) -> Table:
        frame = pd.DataFrame([self._window_row(band, window) for window in self._windows])
        improved, odds_only = self._names[IMPROVED], self._names[ODDS_ONLY]
        count = int((frame[improved] < frame[odds_only]).sum())
        return self._format.table(frame, f"人気馬（{band}）: 区切りごとのログ損失（テスト期間。小さいほど良い）",
                                  note=f"変更版がオッズだけより小さい区切り {count} / {len(frame)}。")

    def _window_row(self, band: str, window: TestWindow) -> dict[str, object]:
        row: dict[str, object] = {"区切り": window.name}
        for key, name in self._names.items():
            rows = self._rows(key)
            chosen = rows[(rows[WINDOW] == window.name) & (rows[FAVORITE_BAND] == band)]
            row[name] = BinaryScores().of(chosen[LABEL], chosen[PREDICTION_COLUMN], chosen[POPULARITY])["ログ損失"]
        return row

    def _pooled(self) -> Table:
        scores = BinaryScores()
        rows = [{"作り方": name, **scores.of(self._rows(key)[LABEL], self._rows(key)[PREDICTION_COLUMN],
                                                 self._rows(key)[POPULARITY])}
                for key, name in self._names.items()]
        base = self._rows(IMPROVED)
        rows.append({"作り方": "オッズから見た4着以下の確率（補正なし）",
                     **scores.of(base[LABEL], base[BASE_PROBABILITY], base[POPULARITY])})
        return self._format.table(pd.DataFrame(rows), "人気馬: テスト期間を合わせた当たり具合（1〜5番人気）")

    def _flagged(self, key: str) -> pd.DataFrame:
        """テスト期間の行に「危険」の真偽を付ける。現行は確率 60% 以上、ほかは危険度が線以上（線は検証期間で決める）。"""
        test = self._rows(key)
        if key == CURRENT:
            return test.assign(危険=test[PREDICTION_COLUMN] >= _OLD_DANGER, 線=_OLD_DANGER)
        thresholds = self._thresholds(key)
        line = thresholds.reindex(pd.MultiIndex.from_frame(test[[WINDOW, FAVORITE_BAND]])).to_numpy()
        return test.assign(危険=test[DANGER].to_numpy() >= line, 線=line)

    def _thresholds(self, key: str) -> pd.Series:
        """（区切り, 人気帯）→ 危険度の線。検証期間の行だけで決める。"""
        valid = self._rows(key, part=PART_VALID)
        chooser = DangerThreshold()
        return valid.groupby([WINDOW, FAVORITE_BAND]).apply(lambda group: chooser.choose(group[DANGER], group[LABEL]))

    def _danger_table(self, key: str) -> Table:
        flagged = self._flagged(key)
        rows = [self._danger_row(popularity, flagged[flagged[POPULARITY] == popularity]) for popularity in range(1, 6)]
        name = self._names[key]
        rule = "4着以下の確率 60% 以上" if key == CURRENT else "危険度（予想 − オッズから見た4着以下の確率）が線以上。線は検証期間で決めた"
        return self._format.table(pd.DataFrame(rows), f"人気馬（{name}）: 危険の判定は、同じ人気の馬全体より当たるか（テスト期間の合計）",
                                  note=f"危険の判定: {rule}。差 = 危険とした馬の4着以下率 − その人気の全体の4着以下率。")

    def _danger_row(self, popularity: int, rows: pd.DataFrame) -> dict[str, object]:
        flagged = rows[rows["危険"]]
        overall = float(rows[LABEL].mean()) if len(rows) else float("nan")
        hit = float(flagged[LABEL].mean()) if len(flagged) else float("nan")
        return {
            "人気": f"{popularity}番人気", "頭数": len(rows), "全体の4着以下率": overall,
            "危険とした頭数": len(flagged), "危険とした馬の4着以下率": hit, "差": hit - overall,
        }

    def _first_favorite_by_window(self) -> Table:
        flagged = self._flagged(IMPROVED)
        first = flagged[flagged[POPULARITY] == 1]
        rows = [{"区切り": window.name, **self._danger_row(1, first[first[WINDOW] == window.name]),
                 "線": float(np.nanmean(first.loc[first[WINDOW] == window.name, "線"]))}
                for window in self._windows]
        return self._format.table(pd.DataFrame(rows).drop(columns=["人気"]),
                                  f"人気馬（{self._names[IMPROVED]}）: 1番人気の危険の判定の、区切りごとの結果",
                                  note="区切りごとに、危険とした1番人気が、1番人気全体より実際に負けやすかったか。")
