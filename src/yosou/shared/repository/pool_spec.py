"""券種オッズから、馬ごとの確率を取り出すときの決まり（どの表の、どの列を、どう足すか）。"""

from dataclasses import dataclass

#: 1つのオッズ列を持つ券種の、払戻倍率の式（元DB のオッズは10倍の整数。'0540123' = 54012.3倍）。
SINGLE_PRICE = 'TRY_CAST(o."オッズ" AS DOUBLE) / 10.0'
#: 最低〜最高の幅で出る券種（複勝・ワイド）の、払戻倍率の式。幅の真ん中を使う。
RANGE_PRICE = '(TRY_CAST(o."最低オッズ" AS DOUBLE) + TRY_CAST(o."最高オッズ" AS DOUBLE)) / 20.0'


@dataclass(frozen=True)
class PoolSpec:
    """1つの券種から取り出す確率。

    - ``column``: 出走の行に付ける列の名前（英字）。
    - ``name``: 特徴量の名前。
    - ``header``・``table``: 元DB のオッズの親の表（データ区分がある）と子の表（買い目ごとのオッズ）。
    - ``combo``: 買い目を表す列（組番。複勝だけ馬番）。
    - ``price``: 払戻倍率の式。
    - ``horses``: 買い目に入る馬の数。
    - ``first_horse_only``: 1着の馬だけを見るか（馬単・3連単）。
    - ``market``: 比べる単勝オッズ側の確率（勝率・2着以内率・3着以内率）。
    - ``scale``: 買い目の確率の和を、その意味の確率にする倍率。複勝は1頭の買い目で3頭が当たるので3倍、
      ワイドは2頭の買い目で3組が当たり、1頭は2組に入るので 3 ÷ 2 = 1.5倍。ほかは1倍。
      これでレース内の合計が、勝率は1、2着以内率は2、3着以内率は3になる。
    """

    column: str
    name: str
    header: str
    table: str
    combo: str
    price: str
    horses: int
    first_horse_only: bool
    market: str
    scale: float = 1.0


#: 取り出す確率の一覧（研究「回収率100超」の PoolMarginal と同じ計算に、``scale`` を足した）。
POOLS: tuple[PoolSpec, ...] = (
    PoolSpec("pool_trifecta_win", "3連単から見た勝率", "o6", "o6__3連単オッズ", "組番", SINGLE_PRICE, 3, True, "勝率"),
    PoolSpec("pool_exacta_win", "馬単から見た勝率", "o4", "o4__馬単オッズ", "組番", SINGLE_PRICE, 2, True, "勝率"),
    PoolSpec("pool_trio_top3", "3連複から見た3着以内率", "o5", "o5__3連複オッズ", "組番", SINGLE_PRICE, 3, False, "3着以内率"),
    PoolSpec("pool_quinella_top2", "馬連から見た2着以内率", "o2", "o2__馬連オッズ", "組番", SINGLE_PRICE, 2, False, "2着以内率"),
    PoolSpec("pool_wide_top3", "ワイドから見た3着以内率", "o3", "o3__ワイドオッズ", "組番", RANGE_PRICE, 2, False, "3着以内率", 1.5),
    PoolSpec("pool_place_top3", "複勝から見た3着以内率", "o1", "o1__複勝オッズ", "馬番", RANGE_PRICE, 1, False, "3着以内率", 3.0),
)
