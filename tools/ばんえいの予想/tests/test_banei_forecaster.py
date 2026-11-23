"""BaneiForecaster の、競走条件名称からクラスを取り出す所のテスト。"""

from __future__ import annotations

from ばんえいの予想.banei_forecaster import BaneiForecaster


def test_クラスの部分だけを取り出し_後ろの賞金の条件は落とす() -> None:
    assert BaneiForecaster._condition("　　　Ｃ２－６　　　　      　　 220.0万未満") == "Ｃ２－６"
    assert BaneiForecaster._condition("２歳　Ｄ　－８") == "２歳Ｄ－８"
    assert BaneiForecaster._condition(None) == ""
