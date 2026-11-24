"""市場の表（1行 = 1券種の1組）と馬ごとの表の、列の名前。

市場の表は共有の部品（``yosou.shared.combo_value.ComboBlendFeatures``）が作るので、列の名前はその部品のものに合わせる。
"""

#: レースID（16桁の文字列）と馬番。
RACE_ID = "race_id"
HORSE_NO = "horse_no"
#: 組番（馬番を2桁ずつ並べた文字列）と、その券種のオッズ（倍。ワイドは最低オッズ）。
COMBO = "combo"
ODDS = "odds"
#: その券種のオッズから見た組の確率 q の対数（オッズの逆数をレースで合計 1、ワイドは 3 にそろえた値）。
LOG_Q = "log_own"
#: 3連単の市場の確率をその券種の組に足し合わせた値 t の対数。
LOG_T = "log_trifecta"
