"""理論の一覧: 段1 の事例の表（崩れた人気馬・来た穴馬の事情の倍率）から立てた候補。段2 で全レースの数で確かめる。"""

from __future__ import annotations

import pandas as pd

from .popularity_band import FAVORITE, LONGSHOT, MIDDLE
from .runner_circumstances import SUPPORT_RATIO
from .theory import FAVORITE_FAILS, FAVORITE_HOLDS, LONGSHOT_COMES, LONGSHOT_FAILS, Theory

_FAV = (FAVORITE,)
_HOLES = (MIDDLE, LONGSHOT)
#: 単勝支持が厚い（支持率が同じ人気の中央値の 1.2倍以上）。
_THICK_SUPPORT_RATIO = 1.2
_POPULARITY_DROP_FROM, _POPULARITY_DROP_TO = 3, 8


def _flag(name: str):
    return lambda t: t[name]


def _both(first: str, second: str):
    return lambda t: t[first] & t[second]


#: 人気馬が崩れる（1〜3番人気の複勝率が、同じ人気の馬全体より低いはず）。
FAVORITE_THEORIES: tuple[Theory, ...] = (
    Theory("単勝支持が薄い人気", FAVORITE_FAILS, _FAV, "人気の順位のわりにオッズが高い（市場の支持が割れている）", _flag("単勝支持が薄い人気")),
    Theory("前走は後ろにいた", FAVORITE_FAILS, _FAV, "小回りの地方では後ろからの馬は取りこぼす", _flag("前走は後ろにいた")),
    Theory("前走6着以下", FAVORITE_FAILS, _FAV, "前走で負けているのに人気", _flag("前走6着以下")),
    Theory("前走大敗", FAVORITE_FAILS, _FAV, "前走の着差 1.0秒以上", _flag("前走大敗")),
    Theory("前走6番人気以下", FAVORITE_FAILS, _FAV, "前走は人気薄だったのに今回は人気（急に評価が上がった）", _flag("前走6番人気以下")),
    Theory("斤量が軽い", FAVORITE_FAILS, _FAV, "減量や別定で軽い斤量の人気馬（力より条件で人気）", _flag("斤量が軽い")),
    Theory("減量騎手", FAVORITE_FAILS, _FAV, "減量騎手が乗る人気馬", _flag("減量騎手")),
    Theory("騎手が場の圏外", FAVORITE_FAILS, _FAV, "その場で前の年に 11位以下か勝っていない騎手", _flag("騎手が場の圏外")),
    Theory("乗り替わりで場の圏外の騎手", FAVORITE_FAILS, _FAV, "乗り替わり、かつ場の圏外の騎手", _both("乗り替わり", "騎手が場の圏外")),
    Theory("休み明け", FAVORITE_FAILS, _FAV, "90日以上の休み明け", _flag("休み明け")),
    Theory("牝馬（牡牝混合）", FAVORITE_FAILS, _FAV, "牡馬相手の牝馬の人気馬", _flag("牝馬（牡牝混合）")),
    Theory("高齢", FAVORITE_FAILS, _FAV, "8歳以上の人気馬", _flag("高齢")),
    Theory("前走6着以下で支持が薄い", FAVORITE_FAILS, _FAV, "前走で負けていて、市場の支持も割れている", _both("前走6着以下", "単勝支持が薄い人気")),
    Theory("前走後ろで距離延長", FAVORITE_FAILS, _FAV, "後ろからの馬が距離を延ばす", _both("前走は後ろにいた", "距離延長")),
    Theory("別の場から", FAVORITE_FAILS, _FAV, "前走と違う競馬場（遠征・転入を含む）", _flag("別の場から")),
    Theory("地方で2走以下", FAVORITE_HOLDS, _FAV, "転入して間もない人気馬（中央や他地区からの馬は格上のことが多い）", _flag("地方で2走以下")),
    Theory("騎手が場の上位3", FAVORITE_HOLDS, _FAV, "その場のリーディング上位の騎手", _flag("騎手が場の上位3")),
    Theory("持ち時計1位", FAVORITE_HOLDS, _FAV, "このコースの持ち時計がレースで1位", _flag("持ち時計1位")),
    Theory("前走3着以内で前にいた", FAVORITE_HOLDS, _FAV, "前走で先行して好走", _both("前走3着以内", "前走は前にいた")),
    Theory("単勝支持が厚い人気", FAVORITE_HOLDS, _FAV, "人気の順位のわりにオッズが低い（市場が強く支持）", lambda t: t[SUPPORT_RATIO] >= _THICK_SUPPORT_RATIO),
)

#: 穴馬が来る（中穴・大穴の複勝率が、同じ人気の馬全体より高いはず）。
LONGSHOT_THEORIES: tuple[Theory, ...] = (
    Theory("前走3着以内", LONGSHOT_COMES, _HOLES, "前走で好走したのに人気薄", _flag("前走3着以内")),
    Theory("前走1〜3番人気", LONGSHOT_COMES, _HOLES, "前走は人気だったのに今回は人気薄", _flag("前走1〜3番人気")),
    Theory("人気落ち（前走1〜3番人気で今回8番人気以下）", LONGSHOT_COMES, (LONGSHOT,), "人気を大きく落とした馬",
           lambda t: (t["prev_popularity"] <= _POPULARITY_DROP_FROM) & (t["popularity"] >= _POPULARITY_DROP_TO)),
    Theory("前走は前にいた", LONGSHOT_COMES, _HOLES, "先行できる人気薄（小回りで残る）", _flag("前走は前にいた")),
    Theory("騎手が場の上位3", LONGSHOT_COMES, _HOLES, "場の上位騎手が乗る人気薄", _flag("騎手が場の上位3")),
    Theory("騎手が場の10位以内", LONGSHOT_COMES, _HOLES, "場の 10位以内の騎手が乗る人気薄", _flag("騎手が場の10位以内")),
    Theory("持ち時計1位", LONGSHOT_COMES, _HOLES, "このコースの持ち時計がレースで1位の人気薄", _flag("持ち時計1位")),
    Theory("斤量が重い", LONGSHOT_COMES, _HOLES, "斤量が平均より重い（実績がある）人気薄", _flag("斤量が重い")),
    Theory("転入初戦", LONGSHOT_COMES, _HOLES, "地方の出走が無い 3歳以上の馬", _flag("転入初戦")),
    Theory("地方で2走以下", LONGSHOT_COMES, _HOLES, "転入して間もない人気薄", _flag("地方で2走以下")),
    Theory("中央所属", LONGSHOT_COMES, _HOLES, "交流競走の中央馬で人気薄", _flag("中央所属")),
    Theory("降級", LONGSHOT_COMES, _HOLES, "クラスが下がった人気薄", _flag("降級")),
    Theory("前走3着以内で前にいた", LONGSHOT_COMES, _HOLES, "前走で先行して好走した人気薄", _both("前走3着以内", "前走は前にいた")),
    Theory("前走3着以内で場の10位以内の騎手", LONGSHOT_COMES, _HOLES, "前走好走 × 場の上位騎手", _both("前走3着以内", "騎手が場の10位以内")),
    Theory("前走前にいて場の10位以内の騎手", LONGSHOT_COMES, _HOLES, "先行 × 場の上位騎手", _both("前走は前にいた", "騎手が場の10位以内")),
    Theory("前走前にいて距離短縮", LONGSHOT_COMES, _HOLES, "先行馬の距離短縮", _both("前走は前にいた", "距離短縮")),
    Theory("内枠で前走前にいた", LONGSHOT_COMES, _HOLES, "内枠の先行馬", _both("内枠", "前走は前にいた")),
    Theory("単勝支持が厚い人気薄", LONGSHOT_COMES, _HOLES, "人気の順位のわりにオッズが低い人気薄", lambda t: t[SUPPORT_RATIO] >= _THICK_SUPPORT_RATIO),
    Theory("連闘", LONGSHOT_COMES, _HOLES, "8日以内の出走", _flag("連闘")),
    Theory("休み明け", LONGSHOT_COMES, _HOLES, "90日以上の休み明けの人気薄", _flag("休み明け")),
    Theory("前走は後ろにいた", LONGSHOT_FAILS, _HOLES, "後ろからの人気薄（来ないはず）", _flag("前走は後ろにいた")),
    Theory("前走6着以下", LONGSHOT_FAILS, _HOLES, "前走で負けた人気薄（来ないはず）", _flag("前走6着以下")),
    Theory("単勝支持が薄い人気薄", LONGSHOT_FAILS, _HOLES, "人気の順位のわりにオッズが高い人気薄（来ないはず）", _flag("単勝支持が薄い人気")),
)

THEORIES: tuple[Theory, ...] = FAVORITE_THEORIES + LONGSHOT_THEORIES
