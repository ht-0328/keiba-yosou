"""検証データを、開催日で前半と後半に分ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE, TrainingData


class ValidationHalves:
    """検証データを、開催日の真ん中で前半と後半に分ける（設計書 16 の 1）。

    前半は早期終了（木の数を決める）、後半は温度（と、1着の予想では 2着・3着の割り当てのならしの指数）を決めるのに使う。
    同じデータで両方を決めると、確率が実際より当たって見えるためである（設計書 11 の 10・12）。
    """

    def split(self, valid: TrainingData) -> tuple[TrainingData, TrainingData]:
        """（前半, 後半）。真ん中の開催日は後半に入る。開催日が1日しかなければ ``ValueError``。"""
        days = sorted(pd.to_datetime(valid.ids[RACE_DATE]).unique())
        if len(days) < 2:
            raise ValueError("検証データの開催日が1日しかないので、前半と後半に分けられません。検証の期間を延ばしてください。")
        middle = pd.Timestamp(days[len(days) // 2]).date()
        return valid.between(None, middle), valid.between(middle, None)
