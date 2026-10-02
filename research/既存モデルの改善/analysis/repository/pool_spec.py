"""1つの券種から、馬ごとの支持を取り出すための決まり。"""

from __future__ import annotations

from dataclasses import dataclass

#: 1つのオッズ列を持つ券種の値段の式（元DB のオッズは 10倍の整数）。
_SINGLE = 'TRY_CAST(o."オッズ" AS DOUBLE) / 10.0'
#: 最低〜最高の幅で出る券種（複勝・ワイド）の値段の式。中間を使う。
_RANGE = '(TRY_CAST(o."最低オッズ" AS DOUBLE) + TRY_CAST(o."最高オッズ" AS DOUBLE)) / 20.0'


@dataclass(frozen=True)
class PoolSpec:
    """1つの券種の、馬ごとの支持の取り出し方（既存モデルの修正計画の 2「券種ごとのオッズ」）。

    - ``column``: 作る列の名前（例: 3連複から見た3着以内率）。
    - ``parent``・``child``: オッズの親と子の表。``combo``: 組の列（馬番か組番）。
    - ``price``: 払戻倍率にする式。``horses``: 組に入る馬の数。
    - ``first_only``: 1着の馬だけを見るか（馬単・3連単）。見ないなら、組の全部の馬に同じ値を配る。
    """

    column: str
    parent: str
    child: str
    combo: str
    price: str
    horses: int
    first_only: bool


#: 取り出す券種。3連単・3連複は売上がいちばん大きく、情報が多い（研究「回収率100超」）。
POOL_SPECS: tuple[PoolSpec, ...] = (
    PoolSpec("3連単から見た勝率", "o6", "o6__3連単オッズ", "組番", _SINGLE, 3, True),
    PoolSpec("馬単から見た勝率", "o4", "o4__馬単オッズ", "組番", _SINGLE, 2, True),
    PoolSpec("3連複から見た3着以内率", "o5", "o5__3連複オッズ", "組番", _SINGLE, 3, False),
    PoolSpec("馬連から見た2着以内率", "o2", "o2__馬連オッズ", "組番", _SINGLE, 2, False),
    PoolSpec("ワイドから見た3着以内率", "o3", "o3__ワイドオッズ", "組番", _RANGE, 2, False),
    PoolSpec("複勝から見た3着以内率", "o1", "o1__複勝オッズ", "馬番", _RANGE, 1, False),
)
