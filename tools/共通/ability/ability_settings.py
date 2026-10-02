"""能力指数の作り方の設定。"""

from __future__ import annotations

from dataclasses import dataclass

#: 適性の種類。
DISTANCE, COURSE, GOING = "距離", "コース", "馬場"
#: 初めての条件の種類（``FirstConditions``）。血統で補う単位。
FIRST_DISTANCE, FIRST_VENUE, FIRST_SURFACE, FIRST_GOING = "初めての距離帯", "初めての競馬場", "初めての芝ダ", "初めての馬場の組"
FIRST_KINDS: tuple[str, ...] = (FIRST_DISTANCE, FIRST_VENUE, FIRST_SURFACE, FIRST_GOING)


@dataclass(frozen=True)
class AbilitySettings:
    """能力指数の作り方。既定値は、研究「能力指数の作り方」で比べて決めた値
    （``research/能力指数の作り方/docs/02-結果の読み方.md``）。

    スピード指数（1回の走）:

    - track_variant: その日の馬場差で補正するか。
    - weight_per_kg: 斤量 1kg あたりの補正（%）。55kg より重く背負った走ほど、指数を上げる。
    - pace: ペース補正（展開で得をした分・損をした分を差し引く）をするか。
    - floor_gap: 大きく負けた走の切り上げ。そのレースでいちばん高い指数より ``floor_gap`` 点以上低い指数は、
      いちばん高い指数 − ``floor_gap`` にする（大きく負けた走は、力を出し切っていないことが多いため）。None なら切り上げない。

    能力指数（近走のまとめ）:

    - runs: 使う近走の数。
    - window_days: 何日前までの走を使うか。
    - recency: 1つ古い走の重みの倍率。例: 0.7 なら、前走 1、2走前 0.7、3走前 0.49 …。1 なら同じ重み（平均）。
    - distance_scale: 距離の近さの重み。今回との距離の差が d m の走の重みを exp(−d ÷ distance_scale) 倍にする。
      例: 800 なら、400m 違う走は 0.61倍、800m 違う走は 0.37倍。
    - other_venue: 今回と違う競馬場の走の重みの倍率。
    - other_going: 今回と馬場の組（良・稍重 か、重・不良）が違う走の重みの倍率。
    - other_surface: 今回と芝ダが違う走の重みの倍率。
    - aptitudes: 能力指数に入れる適性（``DISTANCE`` ``COURSE`` ``GOING``）。入れない適性は、重みの倍率を 1 にする。

    血統で補う（初めての条件の適性。``PedigreeAptitude``）:

    - pedigree: 使う親の列（``"sire"`` 父・``"damsire"`` 母の父）。空なら補わない。
    - pedigree_prior: 産駒の走が少ない親の値を 0 に寄せる強さ（走の数に足す数）。
    - pedigree_kinds: 血統で補う初めての条件（``FIRST_KINDS`` のどれか）。既定は、比べて効いた芝ダだけ。
    """

    track_variant: bool = True
    weight_per_kg: float = 0.05
    pace: bool = True
    floor_gap: float | None = 30.0
    runs: int = 8
    window_days: int = 730
    recency: float = 0.7
    distance_scale: float = 800.0
    other_venue: float = 0.9
    other_going: float = 0.8
    other_surface: float = 0.4
    aptitudes: tuple[str, ...] = (DISTANCE, COURSE, GOING)
    pedigree: tuple[str, ...] = ("sire", "damsire")
    pedigree_prior: float = 20.0
    pedigree_kinds: tuple[str, ...] = (FIRST_SURFACE,)
