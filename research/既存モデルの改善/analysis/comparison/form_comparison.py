"""全頭の3着以内の予想の、比べ方の表。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData
from yosou.shared.dataset.column_names import PLACE_PAYOUT, POPULARITY, WIN_PAYOUT

from ..scores import BinaryScores, BootstrapInterval, PopularityBand
from ..scores.popularity_band import BANDS
from ..walk_forward import PART_TEST, PREDICTION_COLUMN, WINDOW
from ..windows import TestWindow
from .place_value_strategy import EXPECTED_VALUE, PlaceValueStrategy
from .prediction_join import BASE_PROBABILITY, LABEL, PredictionJoin
from .table_formatter import TableFormatter

#: 作り方の鍵（variant_catalog と同じ）。
CURRENT, ODDS_ONLY, IMPROVED = "current", "odds_only", "improved"


class FormComparison:
    """全頭の3着以内の予想を、現行・オッズだけ・変更版で比べる表を作る（既存モデルの修正計画の 3「全頭」）。

    採用の基準（計画の 3）: 変更版の確率の誤差（ログ損失）が、オッズだけより小さい区切りが7つのうち5つ以上あり、
    全期間を通じた誤差とばらつきも確かめられること。

    ``predictions`` は作り方の鍵 → 予測の表、``names`` は作り方の鍵 → 表に出す名前。
    """

    def __init__(self, data: TrainingData, predictions: Mapping[str, pd.DataFrame], names: Mapping[str, str],
                 windows: tuple[TestWindow, ...]) -> None:
        join = PredictionJoin(data)
        self._joined = {key: join.of(frame) for key, frame in predictions.items()}
        self._names = dict(names)
        self._windows = windows
        self._history = pd.concat([data.ids, data.evaluation], axis=1)
        self._format = TableFormatter()

    def tables(self) -> list[Table]:
        return [
            self._by_window(), self._pooled(), self._calibration(), self._top_pick(),
            *self._place_value(IMPROVED), *self._place_value(CURRENT),
        ]

    def _test(self, key: str) -> pd.DataFrame:
        frame = self._joined[key]
        return frame[frame["期間"] == PART_TEST]

    def _by_window(self) -> Table:
        frame = pd.DataFrame([self._window_row(window) for window in self._windows])
        improved, odds_only = f"{self._names[IMPROVED]}: ログ損失", f"{self._names[ODDS_ONLY]}: ログ損失"
        frame["変更版がオッズだけより小さい"] = np.where(frame[improved] < frame[odds_only], "はい", "いいえ")
        count = int((frame[improved] < frame[odds_only]).sum())
        return self._format.table(
            frame, "全頭: 区切りごとの確率の誤差（テスト期間）",
            note=f"ログ損失は小さいほど良い。変更版がオッズだけより小さい区切り: {count} / {len(frame)}"
                 "（計画の採用の基準は 5 / 7 以上）。人気別AUC は同じ単勝人気の馬どうしで比べた AUC（0.5 は見分けられていない）。",
        )

    def _window_row(self, window: TestWindow) -> dict[str, object]:
        """1つの区切りの、作り方ごとのログ損失と人気別 AUC。"""
        row: dict[str, object] = {"区切り": window.name}
        for key, name in self._names.items():
            row.update(self._window_scores(key, name, window))
        return row

    def _window_scores(self, key: str, name: str, window: TestWindow) -> dict[str, float]:
        test = self._test(key)
        chosen = test[test[WINDOW] == window.name]
        result = BinaryScores().of(chosen[LABEL], chosen[PREDICTION_COLUMN], chosen[POPULARITY])
        return {f"{name}: ログ損失": result["ログ損失"], f"{name}: 人気別AUC": result["人気別AUC"]}

    def _pooled(self) -> Table:
        scores = BinaryScores()
        rows = [{"作り方": name, **scores.of(self._test(key)[LABEL], self._test(key)[PREDICTION_COLUMN],
                                                 self._test(key)[POPULARITY])}
                for key, name in self._names.items()]
        base = self._test(IMPROVED)
        rows.append({"作り方": "オッズから見た3着以内率（Harville の式・補正なし）",
                     **scores.of(base[LABEL], base[BASE_PROBABILITY], base[POPULARITY])})
        return self._format.table(pd.DataFrame(rows), "全頭: 7つの区切りのテスト期間を合わせた当たり具合")

    def _calibration(self) -> Table:
        band = PopularityBand()
        frames = []
        for key, name in self._names.items():
            test = self._test(key).assign(帯=lambda frame: band.of(frame[POPULARITY]))
            summary = test.groupby("帯").agg(頭数=(LABEL, "size"), 実際=(LABEL, "mean"), 予想=(PREDICTION_COLUMN, "mean"))
            frames.append(summary.rename(columns={"予想": f"{name}: 確率の平均"}))
        joined = pd.concat([frames[0][["頭数", "実際"]], *[frame.iloc[:, 2:] for frame in frames]], axis=1)
        joined = joined.reindex([band_name for band_name in BANDS if band_name in joined.index]).reset_index()
        return self._format.table(joined, "全頭: 人気帯ごとの、3着以内の実際の割合と予想の確率の平均（テスト期間）",
                                  note="予想の確率の平均が実際の割合に近いほど、確率がずれていない。")

    def _top_pick(self) -> Table:
        rows = [self._top_row(name, self._test(key), PREDICTION_COLUMN) for key, name in self._names.items()]
        favorite = self._test(IMPROVED).assign(人気の逆=lambda frame: -frame[POPULARITY].fillna(99))
        rows.append(self._top_row("1番人気（比べる目安）", favorite, "人気の逆"))
        return self._format.table(pd.DataFrame(rows), "全頭: 各レースで確率がいちばん高い馬（テスト期間）",
                                  note="回収率は 100円ずつ買ったときの払戻の合計 ÷ 賭け金。")

    def _top_row(self, name: str, test: pd.DataFrame, column: str) -> dict[str, object]:
        picked = test.loc[test.groupby(RACE_ID)[column].idxmax()]
        return {
            "選び方": name, "レース数": len(picked), "3着以内率": float(picked[LABEL].mean()),
            "単勝回収率": float(picked[WIN_PAYOUT].fillna(0).sum() / (100 * len(picked))),
            "複勝回収率": float(picked[PLACE_PAYOUT].fillna(0).sum() / (100 * len(picked))),
        }

    def _place_value(self, key: str) -> list[Table]:
        strategy = PlaceValueStrategy(self._history)
        results = [(window, *strategy.run(self._joined[key][self._joined[key][WINDOW] == window.name], window))
                   for window in self._windows]
        rows = [self._value_row(window.name, bought, threshold) for window, bought, threshold in results]
        everything = pd.concat([bought for _, bought, _ in results], ignore_index=True)
        rows.append(self._value_row("合計", everything, float("nan")))
        name = self._names[key]
        by_band = self._value_by_band(everything)
        return [
            self._format.table(pd.DataFrame(rows), f"全頭（{name}）: 複勝を期待値で買ったとき（テスト期間）",
                               note="期待値 = 複勝的中の確率 × 見込みの払戻の倍率。線は区切りごとに検証期間で決めた。"
                                    "90%の幅は開催日を単位にしたブートストラップ。確定オッズを使うので、実際に買う時点より楽観側。"),
            self._format.table(by_band, f"全頭（{name}）: 複勝を期待値で買ったときの人気帯ごと（テスト期間の合計）"),
        ]

    def _value_row(self, name: str, bought: pd.DataFrame, threshold: float) -> dict[str, object]:
        points = len(bought)
        payout = bought[PLACE_PAYOUT].fillna(0.0)
        low, high = BootstrapInterval().of(bought[RACE_DATE], pd.Series(100.0, index=bought.index), payout)
        return {
            "区切り": name, "線": threshold, "点数": points,
            "的中率": float((payout > 0).mean()) if points else float("nan"),
            "回収率": float(payout.sum() / (100 * points)) if points else float("nan"),
            "90%の下限": low, "90%の上限": high,
            "期待値の平均": float(bought[EXPECTED_VALUE].mean()) if points else float("nan"),
        }

    def _value_by_band(self, bought: pd.DataFrame) -> pd.DataFrame:
        band = PopularityBand().of(bought[POPULARITY])
        payout = bought[PLACE_PAYOUT].fillna(0.0)
        summary = pd.DataFrame({"帯": band, "払戻": payout, "当たり": payout > 0}).groupby("帯").agg(
            点数=("払戻", "size"), 的中率=("当たり", "mean"), 払戻=("払戻", "sum"))
        summary["回収率"] = summary["払戻"] / (100 * summary["点数"])
        ordered = summary.reindex([name for name in BANDS if name in summary.index]).reset_index()
        return ordered[["帯", "点数", "的中率", "回収率"]]
