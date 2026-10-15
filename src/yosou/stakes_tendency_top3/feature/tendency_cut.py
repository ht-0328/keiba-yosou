"""K の切り口（「自分と同じ条件だった馬」の条件）と、切り口ごとに数える成績の名前。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.feature import PredictionTiming

#: 切り口ごとに数える成績（設計書 09 の K）。複勝率は 3着以内の割合、回収率は 100円ずつ買ったときの払戻 ÷ 賭け金。
RUNS, PLACE_RATE, WIN_PAYBACK, PLACE_PAYBACK = "出走数", "複勝率", "単勝回収率", "複勝回収率"
STATS: tuple[str, ...] = (RUNS, PLACE_RATE, WIN_PAYBACK, PLACE_PAYBACK)
#: レース単位の3個（同じレースの馬でみな同じ値）。過去の開催の数と、過去の開催の1番人気・1〜3番人気の複勝率。
EDITIONS = "重賞の過去開催の数"
FAV1_PLACE_RATE = "過去開催の1番人気の複勝率"
FAV123_PLACE_RATE = "過去開催の1〜3番人気の複勝率"
RACE_LEVEL_NAMES: tuple[str, ...] = (EDITIONS, FAV1_PLACE_RATE, FAV123_PLACE_RATE)


@dataclass(frozen=True)
class TendencyCut:
    """切り口1つ。``key`` はコードで使う名前、``label`` は特徴量の名前に使う言葉（「前走のレースが同じ馬」など）。

    ``known_from`` は、自分がどの帯かが分かる最初の時点（枠・オッズ・人気は前日から。ほかは木曜から）。
    """

    key: str
    label: str
    known_from: PredictionTiming = PredictionTiming.THURSDAY

    def feature_name(self, stat: str) -> str:
        """特徴量の名前（例: 過去開催の前走のレースが同じ馬の複勝率）。"""
        return f"過去開催の{self.label}の{stat}"


_DAY_BEFORE = PredictionTiming.DAY_BEFORE

#: 12個の切り口。帯の分け方は ``ConditionBands``。
CUTS: tuple[TendencyCut, ...] = (
    TendencyCut("prev_race", "前走のレースが同じ馬"),
    TendencyCut("prev_finish", "前走の着順が同じ帯の馬"),
    TendencyCut("prev_popularity", "前走の人気が同じ帯の馬"),
    TendencyCut("frame", "枠が同じ帯の馬", _DAY_BEFORE),
    TendencyCut("odds", "単勝オッズが同じ帯の馬", _DAY_BEFORE),
    TendencyCut("popularity", "人気が同じ帯の馬", _DAY_BEFORE),
    TendencyCut("style", "脚質が同じ馬"),
    TendencyCut("interval", "間隔が同じ帯の馬"),
    TendencyCut("affiliation", "所属が同じ馬"),
    TendencyCut("experience", "好走経験の有無が同じ馬"),
    TendencyCut("age", "年齢が同じ馬"),
    TendencyCut("sex", "性別が同じ馬"),
)


def cut_keyed(key: str) -> TendencyCut:
    """名前から引く。知らなければ ``ValueError``。"""
    for cut in CUTS:
        if cut.key == key:
            return cut
    known = " / ".join(cut.key for cut in CUTS)
    raise ValueError(f"知らない切り口です: {key}（{known}）")
