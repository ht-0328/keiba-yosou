"""勝ち切る材料を足した1着のモデルの、時点ごとの作り方と、比べる相手。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.dataset import TOP3, WIN
from yosou.shared.feature import PredictionTiming

from 既存モデルの改善.analysis.variants import ModelVariant

from .finish_columns import FINISH_NAMES
from .finish_tables import FINISH_TABLES, FinishTable

_DAY_BEFORE, _RACE_DAY = PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY


@dataclass(frozen=True)
class FinishVariantSpec:
    """1つの時点の作り方。``table`` は読む表、``variant`` は学ぶ列と時点、``current_table``・``current_key`` は比べる相手
    （研究「既存モデルの改善」の今の1着のモデルの予測。``predictions/<表>/win-<時点>.pkl``）。

    列は今の1着のモデルと同じ（前日は M・O・J、当日は A〜L・N・M・O の元の表の列）に、勝ち切る材料の 10個を足したもの。
    オッズの分かる前日・当日なので、オッズから見た勝率の基準（``WinTargetData`` が付ける）を出発点にして学ぶ。
    ``pool_baseline`` なら、出発点を3連単から見た勝率に替える（施策 1-B と重ねた作り方。当日だけ）。
    ``label`` は当てる目的変数。1着のモデルの確かめが本筋だが、材料を当日の一覧に足すと3着以内のモデルにも入るので、
    3着以内のモデル（``TOP3``。基準はオッズから見た3着以内率のまま）に足しても悪くならないかも同じ区切りで確かめる。
    木曜は単勝の期待値が出ず ◎ の単勝回収率を比べられないので、確かめない。
    """

    timing: PredictionTiming
    table: FinishTable
    variant: ModelVariant
    current_table: str
    current_key: str
    pool_baseline: bool = False
    label: str = WIN

    @property
    def key(self) -> str:
        return self.variant.key


def _spec(table: FinishTable, columns: tuple[str, ...], pool_baseline: bool = False) -> FinishVariantSpec:
    timing = table.timing
    key = f"finish-pool-win-{timing.value}" if pool_baseline else f"finish-win-{timing.value}"
    name = (f"1着のモデル ＋ 勝ち切る材料・出発点を3連単から見た勝率に（{timing.label}）" if pool_baseline
            else f"1着のモデル ＋ 勝ち切る材料（{timing.label}）")
    variant = ModelVariant(table.name, key, name, columns + FINISH_NAMES, uses_baseline=True, timing=timing)
    return FinishVariantSpec(timing, table, variant, table.base, f"win-{timing.value}", pool_baseline)


def _top3_spec(table: FinishTable, columns: tuple[str, ...]) -> FinishVariantSpec:
    """3着以内のモデルに勝ち切る材料を足した作り方（比べる相手は今の3着以内のモデル ``h2h-<時点>``）。"""
    timing = table.timing
    variant = ModelVariant(table.name, f"finish-top3-{timing.value}", f"3着以内のモデル ＋ 勝ち切る材料（{timing.label}）", columns + FINISH_NAMES,
                           uses_baseline=True, timing=timing)
    return FinishVariantSpec(timing, table, variant, table.base, f"h2h-{timing.value}", label=TOP3)


#: 時点ごとの作り方（回す順。前日が道具「印の成績」の既定なので先）。3つ目は当日に施策 1-B（3連単の出発点）を重ねたもの、
#: 最後は当日の3着以内のモデルに足したもの（材料を当日の一覧に足してよいかの確かめ）。
FINISH_VARIANTS: tuple[FinishVariantSpec, ...] = (
    _spec(FINISH_TABLES[0], ABILITY_CATALOG.columns_for(_DAY_BEFORE)),
    _spec(FINISH_TABLES[1], RACE_DAY_CATALOG.columns_for(_RACE_DAY)),
    _spec(FINISH_TABLES[1], RACE_DAY_CATALOG.columns_for(_RACE_DAY), pool_baseline=True),
    _top3_spec(FINISH_TABLES[1], RACE_DAY_CATALOG.columns_for(_RACE_DAY)),
)


def spec_keyed(key: str) -> FinishVariantSpec:
    """保存する名前（``finish-win-<時点>``・``finish-pool-win-race_day``・``finish-top3-race_day``）から引く。知らなければ ``ValueError``。"""
    for spec in FINISH_VARIANTS:
        if spec.key == key:
            return spec
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(spec.key for spec in FINISH_VARIANTS)}）")
