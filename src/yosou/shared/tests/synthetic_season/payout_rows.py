"""終わった1レースの払戻の行を作る。"""

from __future__ import annotations

from collections.abc import Mapping

from 合成DB import synth

#: 払戻の架空の決め方。上位に来た馬の人気の和が大きい（人気薄が来た）ほど、指数的に高くする。
#: 荒れ具合の予想の4つのクラス（設計書 10 の線引き）が、どの券種にもひととおり出る大きさにしてある。
_WIN_BASE, _WIN_GROWTH = 150, 2.0            # 単勝: 1番人気なら 150円、人気が1つ下がるごとに2倍
_QUINELLA_BASE, _QUINELLA_GROWTH = 200, 2.0  # 馬連: 1・2番人気なら 200円、人気の和が1増えるごとに2倍
_TRIO_BASE, _TRIO_GROWTH = 300, 1.8          # 3連複: 1〜3番人気なら 300円、人気の和が1増えるごとに1.8倍
_TRIFECTA_MULTIPLIER = 6                     # 3連単: 3連複の6倍
#: 3連単・3連複には3頭の着順が要る。
_PLACED_COUNT = 3


class PayoutRows:
    """終わった1レースの、払戻の親（フラグ）と 単勝・馬連・3連複・3連単の払戻の行を、合成DB の行の束に足す。

    払戻は架空で、上位に来た馬の人気から決める（人気薄が来るほど高い）。同着は作らない。
    3着まで着順の付いた馬が3頭に満たないレース（頭数が少ない・競走中止）は、払戻を付けない。
    """

    def __init__(self, sample: synth.Sample) -> None:
        self._sample = sample

    def add(self, race_row: dict[str, str], results: Mapping[int, tuple[int, int]]) -> None:
        """``results`` は 馬番 → （確定着順, 単勝人気）。着順 0 は着順なし。"""
        placed = sorted((num for num, (finish, _) in results.items() if 1 <= finish <= _PLACED_COUNT),
                        key=lambda num: results[num][0])
        if len(placed) < _PLACED_COUNT:
            return
        first, second, third = placed
        pop1, pop2, pop3 = (results[num][1] for num in placed)
        win_yen = round(_WIN_BASE * _WIN_GROWTH ** (pop1 - 1))
        quinella_yen = round(_QUINELLA_BASE * _QUINELLA_GROWTH ** (pop1 + pop2 - 3))
        trio_yen = round(_TRIO_BASE * _TRIO_GROWTH ** (pop1 + pop2 + pop3 - 6))
        self._sample.headers.append(synth.payout_header(race_row))
        self._sample.win.append(synth.payout(race_row, first, win_yen, pop=pop1))
        self._sample.quinella.append(synth.combo_payout(
            race_row, self._combo(sorted([first, second])), quinella_yen, pop=pop1 * pop2, table="hr__馬連払戻"))
        self._sample.trio.append(synth.combo_payout(
            race_row, self._combo(sorted(placed)), trio_yen, pop=pop1 * pop2 * pop3, table="hr__3連複払戻"))
        self._sample.trifecta.append(synth.combo_payout(
            race_row, self._combo(placed), trio_yen * _TRIFECTA_MULTIPLIER,
            pop=pop1 * pop2 * pop3 * _TRIFECTA_MULTIPLIER, table="hr__3連単払戻"))

    def _combo(self, numbers: list[int]) -> str:
        """組番（馬番を2桁ずつ並べた文字列）。"""
        return "".join(f"{num:02d}" for num in numbers)
