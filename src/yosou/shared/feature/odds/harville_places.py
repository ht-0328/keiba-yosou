"""勝率から、2着以内・3着以内に入る確率を出す（Harville の式）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .column_names import TOP2_RATE, TOP3_RATE, WIN_RATE

#: 割り算の分母が 0 に近くなるのを防ぐ下限（1頭がほぼ全部の勝率を持つレース）。
_FLOOR = 1e-9


class HarvillePlaces:
    """1レースの勝率から、1着・2着以内・3着以内に入る確率を出す。

    Harville の式は「1着が決まったら、残りの馬の中で、勝率の比で2着を決める。3着も同じ」と考える。
    例: 勝率 0.5・0.3・0.2 の3頭なら、2頭目の馬が2着になる確率は、1頭目が勝って（0.5）残りの中で勝つ
    （0.3 ÷ 0.5）場合と、3頭目が勝って（0.2）残りの中で勝つ（0.3 ÷ 0.8）場合の和になる。

    レースごとに馬を横に並べた表（レースの数 × いちばん多い頭数）にして、まとめて計算する。
    3着になる確率は、1着・2着の組ごとの値 ``T[j, k]`` を全部足してから、自分が1着か2着に入る組を引いて出す
    （頭数の2乗の計算で済む）。
    """

    def places(self, race_ids: pd.Series, win_probability: pd.Series) -> pd.DataFrame:
        """列は ``WIN_RATE``・``TOP2_RATE``・``TOP3_RATE``。index は ``win_probability`` と同じ。

        勝率が欠損値か 0 以下の馬は、どれも欠損値。
        """
        known = win_probability.notna() & (win_probability > 0)
        race_code, slot, board = self._board(race_ids[known], win_probability[known])
        top2 = board + self._second(board)
        top3 = top2 + self._third(board)
        result = pd.DataFrame(np.nan, index=win_probability.index, columns=[WIN_RATE, TOP2_RATE, TOP3_RATE])
        result.loc[known, WIN_RATE] = board[race_code, slot]
        result.loc[known, TOP2_RATE] = top2[race_code, slot]
        result.loc[known, TOP3_RATE] = top3[race_code, slot]
        return result

    def _board(self, race_ids: pd.Series, probability: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """（行ごとのレースの番号, 行ごとのレース内の位置, レース × 位置 の勝率の表）。空いた位置の勝率は 0。"""
        race_code, races = pd.factorize(race_ids, sort=False)
        slot = pd.Series(race_code).groupby(race_code).cumcount().to_numpy()
        width = int(slot.max()) + 1 if len(slot) else 1
        board = np.zeros((len(races), width))
        board[race_code, slot] = probability.to_numpy(dtype="float64")
        return race_code, slot, board

    def _second(self, board: np.ndarray) -> np.ndarray:
        """2着になる確率。i が2着 = ほかの j が勝ち、残りの中で i が勝つ（p_j × p_i ÷ (1 − p_j) の和）。"""
        others = board / np.clip(1.0 - board, _FLOOR, None)
        return board * (others.sum(axis=1, keepdims=True) - others)

    def _third(self, board: np.ndarray) -> np.ndarray:
        """3着になる確率。``T[j, k]`` = j が1着・k が2着で、そのあと残りの中で勝つための分母を含む値。

        i が3着 = i を含まない (j, k) の組の ``T[j, k]`` の和 × p_i。
        """
        first = board / np.clip(1.0 - board, _FLOOR, None)
        remaining = np.clip(1.0 - board[:, :, None] - board[:, None, :], _FLOOR, None)
        pair = first[:, :, None] * board[:, None, :] / remaining
        size = board.shape[1]
        pair[:, np.arange(size), np.arange(size)] = 0.0
        total = pair.sum(axis=(1, 2))[:, None]
        return board * (total - pair.sum(axis=2) - pair.sum(axis=1))
