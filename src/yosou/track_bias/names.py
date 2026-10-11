"""トラックバイアスの、表の列の名前と決めた値。"""

from __future__ import annotations

#: レースの鍵と条件（傾きの表と、過去の傾きのマスの列）。
RACE_ID, RACE_DATE, RACE_NO = "race_id", "race_date", "race_no"
VENUE_CODE, SURFACE, TRACK_CODE = "venue_code", "surface", "track_code"
MEETING_DAY, CONDITION_CODE = "meeting_day", "condition_code"
#: 同じ馬場（競馬場 × 芝ダ × 内外回り）を表す鍵。
COURSE_KEY: tuple[str, ...] = (VENUE_CODE, SURFACE, TRACK_CODE)
#: 過去の傾きのマスの鍵（同じ馬場 × 開催の何日目 × 馬場状態）。
PRIOR_KEY: tuple[str, ...] = (*COURSE_KEY, MEETING_DAY, CONDITION_CODE)

#: レースごとの傾き（正なら内（前）が有利）。
INNER_SLOPE, FRONT_SLOPE = "内の傾き", "前の傾き"
SLOPES: tuple[str, ...] = (INNER_SLOPE, FRONT_SLOPE)
#: 当日の傾きに数えたレースの数（前日のレースは 0.5）。
RACES = "レース数"
#: 過去の傾き（マスの平均を、同じ馬場の全体の平均に寄せたもの）の列。
PRIOR_INNER, PRIOR_FRONT = "過去の内の傾き", "過去の前の傾き"
#: 使う傾き（当日の傾きと過去の傾きを、レース数で混ぜたもの）の列。
USED_INNER, USED_FRONT = "使う内の傾き", "使う前の傾き"
#: いつもの傾き（同じ馬場の全期間の平均。前に行った馬はどのレースでも市場の見立てより来る、のような恒常的な分）の列。
#: バイアスは「いつもとの差」なので、補正は 使う傾き − いつもの傾き で数える。
COURSE_INNER, COURSE_FRONT = "いつもの内の傾き", "いつもの前の傾き"

#: 馬ごとの補正の列（特徴量にもなる）。
INNER_PART, FRONT_PART, CORRECTION = "バイアス_内の分", "バイアス_前の分", "バイアス補正"
INNER_SLOPE_FEATURE, FRONT_SLOPE_FEATURE = "バイアス_内の傾き", "バイアス_前の傾き"
#: 馬ごとの内らしさ・前らしさ（最内・先頭が +0.5、大外・最後方が −0.5）。
INNERNESS, FRONTNESS = "内らしさ", "予想の前らしさ"

#: 判定の列と値（出馬表の表示用。線は ±0.02。設計書「買うレースと買い目を決める」06 の 1）。
VERDICT = "判定"
WITH_BIAS, AGAINST_BIAS, NEUTRAL = "バイアス向き", "バイアス逆", "－"
