"""穴馬の3着以内の予想の、比べ方の表（中穴・大穴ごと）。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from 共通.render import Table

from yosou.longshots_in_top3.dataset import LONGSHOT_ZONE, LongshotZone
from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData
from yosou.shared.dataset.column_names import PLACE_PAYOUT, POPULARITY

from ..scores import BinaryScores, BootstrapInterval, PopularityBand
from ..scores.popularity_band import BANDS
from ..walk_forward import PART, PART_TEST, PREDICTION_COLUMN, WINDOW
from ..windows import TestWindow
from .place_value_strategy import PlaceValueStrategy
from .prediction_join import BASE_PROBABILITY, LABEL, PredictionJoin
from .table_formatter import TableFormatter

#: 作り方の鍵（variant_catalog と同じ）。
CURRENT, ODDS_ONLY, IMPROVED = "current", "odds_only", "improved"


class LongshotComparison:
    """穴馬の3着以内の予想を、中穴・大穴ごとに比べる表を作る（既存モデルの修正計画の 3「穴馬」）。

    採用の基準（計画の 3）: 大穴でも、現行の大穴予想・大穴を全部買う方法・人気最上位の大穴を選ぶ方法より良いかを比べる。
    回収率の推定幅も示す。複勝を買う候補は、変更版では期待値で選ぶ（計画の 1）。
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
        zones = [zone.label for zone in LongshotZone]
        return [self._by_window(zone) for zone in zones] + [self._pooled(zone) for zone in zones] + \
            [self._strategies(zone) for zone in zones] + [self._pick_bands(zone) for zone in zones] + \
            [self._value_by_window(zone) for zone in zones]

    def _rows(self, key: str, zone: str, part: str | None = PART_TEST) -> pd.DataFrame:
        frame = self._joined[key]
        chosen = frame[frame[LONGSHOT_ZONE] == zone]
        return chosen if part is None else chosen[chosen[PART] == part]

    def _by_window(self, zone: str) -> Table:
        frame = pd.DataFrame([self._window_row(zone, window) for window in self._windows])
        improved, odds_only, current = (f"{self._names[key]}" for key in (IMPROVED, ODDS_ONLY, CURRENT))
        better_than_odds = int((frame[improved] < frame[odds_only]).sum())
        better_than_current = int((frame[improved] < frame[current]).sum())
        return self._format.table(
            frame, f"穴馬（{zone}）: 区切りごとのログ損失（テスト期間。小さいほど良い）",
            note=f"変更版がオッズだけより小さい区切り {better_than_odds} / {len(frame)}、"
                 f"現行より小さい区切り {better_than_current} / {len(frame)}。",
        )

    def _window_row(self, zone: str, window: TestWindow) -> dict[str, object]:
        row: dict[str, object] = {"区切り": window.name}
        for key, name in self._names.items():
            rows = self._rows(key, zone)
            chosen = rows[rows[WINDOW] == window.name]
            row[name] = BinaryScores().of(chosen[LABEL], chosen[PREDICTION_COLUMN], chosen[POPULARITY])["ログ損失"]
        return row

    def _pooled(self, zone: str) -> Table:
        scores = BinaryScores()
        rows = [{"作り方": name, **scores.of(self._rows(key, zone)[LABEL], self._rows(key, zone)[PREDICTION_COLUMN],
                                                 self._rows(key, zone)[POPULARITY])}
                for key, name in self._names.items()]
        base = self._rows(IMPROVED, zone)
        rows.append({"作り方": "オッズから見た3着以内率（補正なし）",
                     **scores.of(base[LABEL], base[BASE_PROBABILITY], base[POPULARITY])})
        return self._format.table(pd.DataFrame(rows), f"穴馬（{zone}）: テスト期間を合わせた当たり具合")

    def _strategies(self, zone: str) -> Table:
        base = self._rows(IMPROVED, zone)
        rows = [
            self._strategy_row(f"{zone}を全部買う", base),
            self._strategy_row(f"人気がいちばん上の{zone}を1頭", self._top(base, -base[POPULARITY].fillna(99))),
            self._strategy_row(f"現行の確率1位の{zone}を1頭", self._top_by_probability(CURRENT, zone)),
            self._strategy_row(f"変更版の確率1位の{zone}を1頭", self._top_by_probability(IMPROVED, zone)),
            self._strategy_row(f"現行で、期待値が線以上の{zone}", self._valued(CURRENT, zone)),
            self._strategy_row(f"変更版で、期待値が線以上の{zone}", self._valued(IMPROVED, zone)),
        ]
        return self._format.table(
            pd.DataFrame(rows), f"穴馬（{zone}）: 複勝の買い方ごとの成績（7つの区切りのテスト期間の合計）",
            note="期待値の線は、区切りごとに検証期間の回収率で決めた。90%の幅は開催日を単位にしたブートストラップ。"
                 "確定オッズで見積もるので、実際に買う時点より楽観側。",
        )

    def _top(self, frame: pd.DataFrame, score: pd.Series) -> pd.DataFrame:
        return frame.loc[score.groupby(frame[RACE_ID]).idxmax()]

    def _top_by_probability(self, key: str, zone: str) -> pd.DataFrame:
        rows = self._rows(key, zone)
        return self._top(rows, rows[PREDICTION_COLUMN])

    def _valued(self, key: str, zone: str) -> pd.DataFrame:
        strategy = PlaceValueStrategy(self._history)
        rows = self._rows(key, zone, part=None)
        bought = [strategy.run(rows[rows[WINDOW] == window.name], window)[0] for window in self._windows]
        return pd.concat(bought, ignore_index=True)

    def _strategy_row(self, name: str, bought: pd.DataFrame) -> dict[str, object]:
        payout = bought[PLACE_PAYOUT].fillna(0.0)
        points = len(bought)
        low, high = BootstrapInterval().of(bought[RACE_DATE], pd.Series(100.0, index=bought.index), payout)
        return {
            "買い方": name, "点数": points, "的中率": float((payout > 0).mean()) if points else float("nan"),
            "回収率": float(payout.sum() / (100 * points)) if points else float("nan"),
            "90%の下限": low, "90%の上限": high,
        }

    def _pick_bands(self, zone: str) -> Table:
        picks = {
            "変更版の確率1位": self._top_by_probability(IMPROVED, zone),
            "変更版の期待値": self._valued(IMPROVED, zone),
            "現行の確率1位": self._top_by_probability(CURRENT, zone),
        }
        frame = pd.DataFrame({name: PopularityBand().of(rows[POPULARITY]).value_counts() for name, rows in picks.items()})
        frame = frame.reindex([band for band in BANDS if band in frame.index]).fillna(0).astype(int).reset_index()
        return self._format.table(frame.rename(columns={"index": "人気帯"}),
                                  f"穴馬（{zone}）: 選んだ馬の人気帯ごとの頭数（テスト期間の合計）",
                                  note="人気上位ばかりを選んでいないか（10番人気以下も選べているか）を見る。")

    def _value_by_window(self, zone: str) -> Table:
        strategy = PlaceValueStrategy(self._history)
        rows = self._rows(IMPROVED, zone, part=None)
        results = [(window, *strategy.run(rows[rows[WINDOW] == window.name], window)) for window in self._windows]
        base = self._rows(IMPROVED, zone)
        top_popular = self._top(base, -base[POPULARITY].fillna(99))
        table = [{**self._strategy_row(window.name, bought), "線": threshold,
                  "人気最上位の回収率": self._rate(top_popular[top_popular[WINDOW] == window.name])}
                 for window, bought, threshold in results]
        return self._format.table(pd.DataFrame(table).rename(columns={"買い方": "区切り"}),
                                  f"穴馬（{zone}）: 変更版で期待値が線以上の馬を買ったときの区切りごとの成績")

    def _rate(self, bought: pd.DataFrame) -> float:
        return float(bought[PLACE_PAYOUT].fillna(0.0).sum() / (100 * len(bought))) if len(bought) else float("nan")
