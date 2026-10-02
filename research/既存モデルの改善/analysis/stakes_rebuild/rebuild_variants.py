"""重賞の予想の作り直しの確かめで比べる作り方と、時点ごとの比べ方。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG as FORM_ABILITY_CATALOG
from yosou.form_aptitude_top3.feature import RACE_DAY_CATALOG as FORM_RACE_DAY_CATALOG
from yosou.shared.feature import PredictionTiming
from yosou.stakes_tendency_top3.feature import ABILITY_CATALOG as STAKES_ABILITY_CATALOG
from yosou.stakes_tendency_top3.feature import RACE_DAY_CATALOG as STAKES_RACE_DAY_CATALOG

from ..variants import ModelVariant
from .rebuild_tables import FORM_ABILITY, FORM_RACE_DAY, STAKES_ABILITY, STAKES_RACE_DAY

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY
#: オッズだけの基準に使う列（研究「既存モデルの改善」の全頭・重賞と同じ。オッズから出した値と頭数だけ）。
_ODDS_ONLY = ("単勝オッズ", "人気順位", "オッズから見た勝率", "オッズから見た3着以内率", "出走頭数")


def _variant(table: str, key: str, name: str, columns: tuple[str, ...], timing: PredictionTiming) -> ModelVariant:
    """オッズの分かる前日・当日は、予想と同じく、オッズから作った基準を出発点にして学ぶ。"""
    return ModelVariant(table, key, name, columns, uses_baseline=timing is not _THURSDAY, timing=timing)


def _timed(table: str, key: str, name: str, columns: tuple[str, ...], timing: PredictionTiming) -> ModelVariant:
    """保存する名前と表に出す名前に時点を付けた作り方（研究の ``--timing`` と同じ付け方）。"""
    return _variant(table, f"{key}-{timing.value}", f"{name}（{timing.label}）", columns, timing)


#: 作り方の一覧。「作り直し」は予想のパッケージの材料そのもの（その時点で分かる列）。「重賞の傾向を外す」は K だけを外したもの
#: （手本の材料を重賞だけで学ぶ）。「手本」は全レースの表で学び、重賞の行だけで測る。
REBUILD_VARIANTS: tuple[ModelVariant, ...] = (
    # 木曜（オッズが無いので基準なし。オッズだけのモデルは作れず、当日のオッズだけと比べる）
    _timed(STAKES_ABILITY, "default", "作り直し", STAKES_ABILITY_CATALOG.columns_for(_THURSDAY), _THURSDAY),
    _timed(STAKES_ABILITY, "without_tendency", "作り直しから重賞の傾向を外す", FORM_ABILITY_CATALOG.columns_for(_THURSDAY), _THURSDAY),
    _timed(FORM_ABILITY, "general", "手本を重賞だけに使う", FORM_ABILITY_CATALOG.columns_for(_THURSDAY), _THURSDAY),
    # 前日
    _timed(STAKES_RACE_DAY, "odds_only", "オッズだけ", _ODDS_ONLY, _DAY_BEFORE),
    _timed(STAKES_ABILITY, "default", "作り直し", STAKES_ABILITY_CATALOG.columns_for(_DAY_BEFORE), _DAY_BEFORE),
    _timed(STAKES_ABILITY, "without_tendency", "作り直しから重賞の傾向を外す", FORM_ABILITY_CATALOG.columns_for(_DAY_BEFORE), _DAY_BEFORE),
    _timed(FORM_ABILITY, "general", "手本を重賞だけに使う", FORM_ABILITY_CATALOG.columns_for(_DAY_BEFORE), _DAY_BEFORE),
    # 当日
    _timed(STAKES_RACE_DAY, "odds_only", "オッズだけ", _ODDS_ONLY, _RACE_DAY),
    _timed(STAKES_RACE_DAY, "default", "作り直し", STAKES_RACE_DAY_CATALOG.columns_for(_RACE_DAY), _RACE_DAY),
    _timed(STAKES_RACE_DAY, "without_tendency", "作り直しから重賞の傾向を外す", FORM_RACE_DAY_CATALOG.columns_for(_RACE_DAY), _RACE_DAY),
    _timed(FORM_RACE_DAY, "general", "手本を重賞だけに使う", FORM_RACE_DAY_CATALOG.columns_for(_RACE_DAY), _RACE_DAY),
)


def rebuild_variant_keyed(key: str) -> ModelVariant:
    """保存する名前から引く。知らなければ ``ValueError``。"""
    for variant in REBUILD_VARIANTS:
        if variant.key == key:
            return variant
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(variant.key for variant in REBUILD_VARIANTS)}）")


@dataclass(frozen=True)
class RebuildComparisonSpec:
    """1つの時点の比べ方。

    - ``candidate``: 作り直した専用モデル。
    - ``odds_reference``: 採用の基準 (a) の比べ先（オッズだけ。木曜は当日のオッズだけ）。
    - ``general``: 採用の基準 (b) の比べ先（手本を重賞だけに使ったとき）。
    - ``without_tendency``: 理由の説明に使う、K を外した作り方。
    """

    timing: PredictionTiming
    candidate: ModelVariant
    odds_reference: ModelVariant
    general: ModelVariant
    without_tendency: ModelVariant

    @property
    def variants(self) -> tuple[ModelVariant, ...]:
        """表に出す順（作り直し・傾向を外す・手本・オッズだけ）。"""
        return (self.candidate, self.without_tendency, self.general, self.odds_reference)


#: 時点ごとの比べ方（設計書 15 の 9）。
REBUILD_COMPARISONS: tuple[RebuildComparisonSpec, ...] = (
    RebuildComparisonSpec(_THURSDAY, rebuild_variant_keyed("default-thursday"), rebuild_variant_keyed("odds_only-race_day"),
                          rebuild_variant_keyed("general-thursday"), rebuild_variant_keyed("without_tendency-thursday")),
    RebuildComparisonSpec(_DAY_BEFORE, rebuild_variant_keyed("default-day_before"), rebuild_variant_keyed("odds_only-day_before"),
                          rebuild_variant_keyed("general-day_before"), rebuild_variant_keyed("without_tendency-day_before")),
    RebuildComparisonSpec(_RACE_DAY, rebuild_variant_keyed("default-race_day"), rebuild_variant_keyed("odds_only-race_day"),
                          rebuild_variant_keyed("general-race_day"), rebuild_variant_keyed("without_tendency-race_day")),
)
