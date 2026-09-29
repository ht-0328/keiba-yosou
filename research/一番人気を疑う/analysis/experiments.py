"""試した作り方の一覧。番号の若い順に試した。"""

from __future__ import annotations

from datetime import date

from .experiment import Experiment
from .source.ability_table_source import GROUPS

_SMALL_TREES_FORM = {"num_leaves": 15, "min_child_samples": 1000}
_SMALL_TREES_ABILITY = {"num_leaves": 7, "min_child_samples": 2000}

EXPERIMENTS: tuple[Experiment, ...] = (
    # 今の予想の材料（研究「既存モデルの改善」の表。学習は 2017年から）
    Experiment("00_今の予想_木曜", "今の予想の木曜版（オッズなし）", "form", ("thursday",)),
    Experiment("01_今の予想_当日からオッズを外す", "今の予想の当日版からオッズを外した71個", "form", ("base",)),
    Experiment("02_小さい木", "01 の木を小さくする", "form", ("base",), params=_SMALL_TREES_FORM),
    Experiment("03_レース内の比較", "01 ＋ レース内で比べた値", "form", ("base",), relative=True),
    Experiment("04_追加の材料", "01 ＋ 能力指数・市場に対する成績・当日の馬場傾向", "form", ("base", "extra")),
    Experiment("05_追加とレース内", "04 ＋ レース内で比べた値", "form", ("base", "extra"), relative=True),
    # オッズを使わない197個の材料（研究「馬の力と展開でオッズに勝つ」の表。学習は 2012年から）
    Experiment("11_研究の材料", "197個の材料", "ability", ("race_day",)),
    Experiment("12_研究の材料_小さい木", "11 の木を小さくする", "ability", ("race_day",), params=_SMALL_TREES_ABILITY),
    Experiment("13_研究の材料＋セリ", "11 ＋ セリの価格", "ability", ("race_day",), sales=True),
    Experiment("14_＋セリ＋マイニング", "13 ＋ JRA-VAN のマイニング予想", "ability", ("race_day", "mining"), sales=True),
    Experiment("15_＋前走の人気", "14 ＋ 前走の人気", "ability", ("race_day", "mining", "past_popularity"), sales=True),
    Experiment("16_CatBoost", "14 を CatBoost で", "ability", ("race_day", "mining"), sales=True, models=("catboost",)),
    Experiment("17_平均", "14 の LightGBM と CatBoost の平均", "ability", ("race_day", "mining"), sales=True,
               models=("lightgbm", "catboost")),
    # 木曜の時点（馬体重・枠・当日の馬場が分からない）
    Experiment("21_木曜_研究の材料", "197個から木曜に分からないものを外す", "ability", ("thursday",)),
    Experiment("22_木曜_研究の材料_2017年から", "21 を 2017年からの学習で", "ability", ("thursday",),
               first_day=date(2017, 1, 1)),
    *(Experiment(f"23_木曜_{group}を外す", f"21 から{group}を外す", "ability", ("thursday",), without=(group,))
      for group in GROUPS),
)


def experiment_named(key: str) -> Experiment:
    """名前から引く。知らなければ ``ValueError``。"""
    for experiment in EXPERIMENTS:
        if experiment.key == key:
            return experiment
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(e.key for e in EXPERIMENTS)}）")
