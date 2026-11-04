"""比べる買い方の一覧。L（3連単・全レース・型を問わず・人気馬2頭＋中穴3頭＋大穴3頭・期待値 1.0 以上・30点まで）を軸に、1つずつ変えて比べる。3連複も同じ形で比べる。"""

from __future__ import annotations

from ..payout_band import BIG, HUGE, MEDIUM, SOLID
from .strategy import (
    ALL_PATTERNS, ANY_EVERYWHERE, ANY_PATTERN, DEFAULT_PATTERNS, EDGE_DANGER, EDGE_LONGSHOT, STRENGTH_MIX, STRENGTH_TOP3,
    STRENGTH_TOP3_FIT, STRENGTH_WIN_THEN_TOP3_FIT, TRIO, TRIO_DEFAULT_PATTERNS, UPSET_STAGE, Strategy,
)

TRIFECTA_STRATEGIES: tuple[Strategy, ...] = (
    Strategy("L 全レース・型を問わず・人2中3大3・期待値 1.0・30点", ANY_EVERYWHERE, breakdown=True),
    Strategy("L1 L で消をしない（人3）", ANY_EVERYWHERE, eliminate=False),
    Strategy("L3 L で期待値 1.2 以上", ANY_EVERYWHERE, ev_min=1.2),
    Strategy("L5 L で 10点まで", ANY_EVERYWHERE, max_points=10),
    Strategy("L6 L で 50点まで", ANY_EVERYWHERE, max_points=50),
    Strategy("L7 L で万馬券の組だけ", ANY_EVERYWHERE, odds_min=100.0),
    Strategy("L8 L で 10万馬券の組だけ", ANY_EVERYWHERE, odds_min=1000.0),
    Strategy("L14 L で 30〜300倍の組だけ", ANY_EVERYWHERE, odds_min=30.0, odds_max=300.0),
    Strategy("L15 L で 100〜1000倍の組だけ", ANY_EVERYWHERE, odds_min=100.0, odds_max=1000.0),
    Strategy("L16 L で 300倍以下の組だけ", ANY_EVERYWHERE, odds_max=300.0),
    Strategy("L9 L で頭数を問わない", ANY_EVERYWHERE, min_heads=1),
    Strategy("L17 L で 12頭以上", ANY_EVERYWHERE, min_heads=12),
    Strategy("L13 L で勝つ力を 1着と3着以内の相乗平均に", ANY_EVERYWHERE, strength=STRENGTH_MIX),
    Strategy("L18 L15（100〜1000倍）で期待値 1.2 以上", ANY_EVERYWHERE, odds_min=100.0, odds_max=1000.0, ev_min=1.2),
    Strategy("L19 L15（100〜1000倍）で 10点まで", ANY_EVERYWHERE, odds_min=100.0, odds_max=1000.0, max_points=10),
    Strategy("L20 L で 100〜3000倍の組だけ", ANY_EVERYWHERE, odds_min=100.0, odds_max=3000.0),
    Strategy("L21 L15（100〜1000倍）で当たる見込み 5% 以上のレースだけ", ANY_EVERYWHERE, odds_min=100.0, odds_max=1000.0, race_hit_min=0.05),
    Strategy("L22 L15（100〜1000倍）で当たる見込み 10% 以上のレースだけ", ANY_EVERYWHERE, odds_min=100.0, odds_max=1000.0, race_hit_min=0.10),
    Strategy("L23 L で当たる見込み 10% 以上のレースだけ", ANY_EVERYWHERE, race_hit_min=0.10),
    Strategy("L24 L で当たる見込み 15% 以上のレースだけ", ANY_EVERYWHERE, race_hit_min=0.15),
    Strategy("L25 L で平均の期待値 1.3 以上のレースだけ", ANY_EVERYWHERE, race_ev_min=1.3),
    Strategy("A 荒れ具合で型・消あり・期待値 1.0・30点", DEFAULT_PATTERNS),
    Strategy("C A で消をしない", DEFAULT_PATTERNS, eliminate=False),
)

TRIO_STRATEGIES: tuple[Strategy, ...] = (
    Strategy("T 3連複・全レース・型を問わず・人2中3大3・期待値 1.0・20点", ANY_EVERYWHERE, ticket=TRIO, max_points=20, breakdown=True),
    Strategy("T1 T で消をしない（人3）", ANY_EVERYWHERE, ticket=TRIO, max_points=20, eliminate=False),
    Strategy("T2 T で期待値 1.2 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2),
    Strategy("T3 T で 10点まで", ANY_EVERYWHERE, ticket=TRIO, max_points=10),
    Strategy("T4 T で 10〜100倍の組だけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, odds_min=10.0, odds_max=100.0),
    Strategy("T5 T で 100倍以上の組だけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, odds_min=100.0),
    Strategy("T6 T で頭数を問わない", ANY_EVERYWHERE, ticket=TRIO, max_points=20, min_heads=1),
    Strategy("T7 T で勝つ力を 3着以内の確率に", ANY_EVERYWHERE, ticket=TRIO, max_points=20, strength=STRENGTH_TOP3),
    Strategy("T8 3連複・荒れ具合で型・消あり・期待値 1.0・20点", TRIO_DEFAULT_PATTERNS, ticket=TRIO, max_points=20),
    Strategy("T9 T8 で固いレースも買う（人人中・人中中・人人大・人中大）", {SOLID: ("人人中", "人中中", "人人大", "人中大"), **TRIO_DEFAULT_PATTERNS}, ticket=TRIO, max_points=20),
    Strategy("T10 T2（期待値 1.2）で消をしない（人3）", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, eliminate=False),
    Strategy("T11 T2 で期待値 1.5 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.5),
    Strategy("T12 T2 で 3点まで", ANY_EVERYWHERE, ticket=TRIO, max_points=3, ev_min=1.2),
    Strategy("T13 T2 で頭数を問わない", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, min_heads=1),
    Strategy("T14 T2 で 10〜100倍の組だけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, odds_min=10.0, odds_max=100.0),
    Strategy("T15 T2 で中穴4頭・大穴4頭", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, middles=4, longshots=4),
    Strategy("T16 T2 で 12頭以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, min_heads=12),
    Strategy("T17 T2 で当たる見込み 10% 以上のレースだけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, race_hit_min=0.10),
    Strategy("T18 T2 で当たる見込み 20% 以上のレースだけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, race_hit_min=0.20),
    Strategy("T19 T2 で当たる見込み 30% 以上のレースだけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, race_hit_min=0.30),
    Strategy("T20 T で当たる見込み 20% 以上のレースだけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, race_hit_min=0.20),
    Strategy("T21 T で当たる見込み 30% 以上のレースだけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, race_hit_min=0.30),
    Strategy("T22 T で平均の期待値 1.3 以上のレースだけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, race_ev_min=1.3),
    Strategy("T23 T2 で平均の期待値 1.5 以上のレースだけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, race_ev_min=1.5),
)

#: 選んだ組の確率が高く出すぎる（当たりが見込みの 0.6〜0.7 倍）のを抑える: 組の確率を市場の組の確率に寄せる（縮め）。
SHRINK_STRATEGIES: tuple[Strategy, ...] = (
    Strategy("S1 L で縮め 0.9", ANY_EVERYWHERE, shrink=0.9),
    Strategy("S2 L で縮め 0.8", ANY_EVERYWHERE, shrink=0.8),
    Strategy("S3 L で縮め 0.7", ANY_EVERYWHERE, shrink=0.7, breakdown=True),
    Strategy("S4 L で縮め 0.5", ANY_EVERYWHERE, shrink=0.5),
    Strategy("S5 T で縮め 0.9", ANY_EVERYWHERE, ticket=TRIO, max_points=20, shrink=0.9),
    Strategy("S6 T で縮め 0.8", ANY_EVERYWHERE, ticket=TRIO, max_points=20, shrink=0.8),
    Strategy("S7 T で縮め 0.7", ANY_EVERYWHERE, ticket=TRIO, max_points=20, shrink=0.7, breakdown=True),
    Strategy("S8 T で縮め 0.5", ANY_EVERYWHERE, ticket=TRIO, max_points=20, shrink=0.5),
    Strategy("S9 L15（100〜1000倍）で縮め 0.7", ANY_EVERYWHERE, odds_min=100.0, odds_max=1000.0, shrink=0.7),
    Strategy("S10 L で縮め 0.7・期待値 1.1 以上", ANY_EVERYWHERE, shrink=0.7, ev_min=1.1),
    Strategy("S11 T で縮め 0.7・期待値 1.1 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, shrink=0.7, ev_min=1.1),
)

#: 組の確率を、市場より当たる 3着以内の確率に合わせる: Harville の 3着以内率が 3着以内の確率に一致する勝つ力で組の確率を出す。
FITTED_STRATEGIES: tuple[Strategy, ...] = (
    Strategy("F1 L で勝つ力を 3着以内の確率に合わせて解く", ANY_EVERYWHERE, strength=STRENGTH_TOP3_FIT, breakdown=True),
    Strategy("F2 L で 1着は 1着の確率・2着3着は 3着以内に合わせた勝つ力", ANY_EVERYWHERE, strength=STRENGTH_WIN_THEN_TOP3_FIT),
    Strategy("F3 T で勝つ力を 3着以内の確率に合わせて解く", ANY_EVERYWHERE, ticket=TRIO, max_points=20, strength=STRENGTH_TOP3_FIT, breakdown=True),
    Strategy("F4 F1 で縮め 0.7", ANY_EVERYWHERE, strength=STRENGTH_TOP3_FIT, shrink=0.7),
    Strategy("F5 F3 で縮め 0.7", ANY_EVERYWHERE, ticket=TRIO, max_points=20, strength=STRENGTH_TOP3_FIT, shrink=0.7),
    Strategy("F6 F2 で縮め 0.7", ANY_EVERYWHERE, strength=STRENGTH_WIN_THEN_TOP3_FIT, shrink=0.7),
    Strategy("F7 F1 で 100〜1000倍の組だけ", ANY_EVERYWHERE, strength=STRENGTH_TOP3_FIT, odds_min=100.0, odds_max=1000.0),
    Strategy("F8 F3 で期待値 1.2 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, strength=STRENGTH_TOP3_FIT, ev_min=1.2),
    Strategy("F9 F3 で縮め 0.5", ANY_EVERYWHERE, ticket=TRIO, max_points=20, strength=STRENGTH_TOP3_FIT, shrink=0.5),
    Strategy("F10 F1 で縮め 0.5", ANY_EVERYWHERE, strength=STRENGTH_TOP3_FIT, shrink=0.5),
)

#: 予想方法の段（②危険な人気馬・③穴馬・④荒れ具合。``stages.py`` の予測）で消・穴・レース・型を決める買い方（計画の 6. の段3）。
#: ④の型は、④のいちばん高いクラスを鍵にする（固いは買わない。``DEFAULT_PATTERNS`` と同じ型）。
_STAGE = dict(danger=EDGE_DANGER, longshot=EDGE_LONGSHOT)
STAGE_STRATEGIES: tuple[Strategy, ...] = (
    Strategy("M1 L で消を②（危険な人気馬の予想）で決める", ANY_EVERYWHERE, danger=EDGE_DANGER, breakdown=True),
    Strategy("M2 L で穴を③（穴馬の予想）で決める", ANY_EVERYWHERE, longshot=EDGE_LONGSHOT),
    Strategy("M3 L で消②・穴③", ANY_EVERYWHERE, breakdown=True, **_STAGE),
    Strategy("M4 L で④の大荒れ以上の確率 0.15 以上のレースだけ", ANY_EVERYWHERE, big_min=0.15),
    Strategy("M5 M3 で④の大荒れ以上の確率 0.15 以上のレースだけ", ANY_EVERYWHERE, big_min=0.15, breakdown=True, **_STAGE),
    Strategy("M6 M3 で④ 0.25 以上", ANY_EVERYWHERE, big_min=0.25, **_STAGE),
    Strategy("M7 M3 で④の荒れ具合で型（固いは買わない）", DEFAULT_PATTERNS, upset_source=UPSET_STAGE, breakdown=True, **_STAGE),
    Strategy("M8 M7 で固いレースも型を問わず買う", {**ANY_EVERYWHERE, **DEFAULT_PATTERNS}, upset_source=UPSET_STAGE, **_STAGE),
    Strategy("M9 M5 で 100〜1000倍の組だけ", ANY_EVERYWHERE, big_min=0.15, odds_min=100.0, odds_max=1000.0, **_STAGE),
    Strategy("M10 M5 で期待値 1.2 以上", ANY_EVERYWHERE, big_min=0.15, ev_min=1.2, **_STAGE),
    Strategy("M11 M5 で当たる見込み 5% 以上のレースだけ", ANY_EVERYWHERE, big_min=0.15, race_hit_min=0.05, **_STAGE),
    Strategy("M12 M3 で④の中荒れ以上の確率 0.6 以上のレースだけ", ANY_EVERYWHERE, mid_min=0.6, **_STAGE),
    Strategy("M13 M5 で縮め 0.7", ANY_EVERYWHERE, big_min=0.15, shrink=0.7, **_STAGE),
    Strategy("M14 M3 で②の差 0.10 以上のときだけ消す", ANY_EVERYWHERE, danger_min=0.10, **_STAGE),
    Strategy("M15 M3 で③の差 0.03 以上の穴だけ", ANY_EVERYWHERE, longshot_min=0.03, **_STAGE),
    Strategy("M16 M3 で③の差 0.05 以上の穴だけ", ANY_EVERYWHERE, longshot_min=0.05, **_STAGE),
    Strategy("M17 M5 で③の差 0.03 以上の穴だけ", ANY_EVERYWHERE, big_min=0.15, longshot_min=0.03, **_STAGE),
    Strategy("TM1 T で消②・穴③", ANY_EVERYWHERE, ticket=TRIO, max_points=20, breakdown=True, **_STAGE),
    Strategy("TM2 TM1 で④ 0.15 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, big_min=0.15, **_STAGE),
    Strategy("TM3 TM1 で④の荒れ具合で型", TRIO_DEFAULT_PATTERNS, ticket=TRIO, max_points=20, upset_source=UPSET_STAGE, **_STAGE),
    Strategy("TM4 TM2 で勝つ力を 3着以内の確率に合わせて解く", ANY_EVERYWHERE, ticket=TRIO, max_points=20, big_min=0.15, strength=STRENGTH_TOP3_FIT, **_STAGE),
    Strategy("TM5 TM1 で期待値 1.2 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, ev_min=1.2, **_STAGE),
    Strategy("TM6 TM1 で④の中荒れ以上の確率 0.6 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, mid_min=0.6, **_STAGE),
    Strategy("TM7 TM1 で③の差 0.03 以上の穴だけ", ANY_EVERYWHERE, ticket=TRIO, max_points=20, longshot_min=0.03, **_STAGE),
    Strategy("TM8 TM7 で④ 0.15 以上", ANY_EVERYWHERE, ticket=TRIO, max_points=20, big_min=0.15, longshot_min=0.03, **_STAGE),
)

STRATEGIES: tuple[Strategy, ...] = TRIFECTA_STRATEGIES + TRIO_STRATEGIES + SHRINK_STRATEGIES + FITTED_STRATEGIES + STAGE_STRATEGIES
