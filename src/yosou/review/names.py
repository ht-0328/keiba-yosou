"""回顧データの、表と列の名前と、不利の種類・程度の値。"""

from __future__ import annotations

#: 回顧の DuckDB の表（設計書「買うレースと買い目を決める」08 の 3 の表1〜3と、回顧を書いた範囲）。
BETS_TABLE, RACES_TABLE, HORSES_TABLE, COVERAGE_TABLE = "買い目の記録", "レースの回顧", "馬の回顧ノート", "回顧の範囲"

#: 共通の列。
RACE_ID, RACE_DATE, HORSE_ID = "race_id", "race_date", "horse_id"

#: 表1「買い目の記録」の列。
PARTICIPATION, TICKET_TYPE, COMBO, RECORD_ONLY, STAKE_YEN = "参加の種類", "券種", "買い目", "記録だけか", "金額"
BOUGHT_PROBABILITY, BOUGHT_VALUE, BOUGHT_ODDS, ODDS_AT, PAYOUT_YEN, SETTLED = "確率", "期待値", "オッズ", "オッズの時刻", "払戻", "精算済み"
#: 参加の種類の値。勝負（単勝・馬単）は、当日の期待度「高」のレースで買う ◎ の単勝と馬単（複勝の勝負レースとは別に選ぶ）。
MATCH, POLICY_STAKES, POLICY_DAY, MATCH_WIN = "勝負", "ノルマ（重賞）", "ノルマ（日）", "勝負（単勝・馬単）"

#: 表2「レースの回顧」の列。
FORECAST_PACE, FORECAST_HIGH, FORECAST_SLOW = "予想のペース", "予想のハイの確率", "予想のスローの確率"
RESULT_PACE, DAY_INNER_SLOPE, DAY_FRONT_SLOPE, CONDITION = "結果のペース", "当日の内の傾き", "当日の前の傾き", "馬場状態"

#: 表3「馬の回顧ノート」の列。
HANDICAPS, DEGREE, NEXT_RUN = "不利の種類", "程度", "次走の扱い"
LATE_START_GAP, RESULT_SCORE, RESULT_BIAS = "出遅れの量", "結果の展開スコア", "結果のバイアス"
LATE_START_DEGREE, PACE_DEGREE, BIAS_DEGREE = "出遅れ_程度", "展開_程度", "バイアス_程度"
DEGREES: tuple[str, ...] = (LATE_START_DEGREE, PACE_DEGREE, BIAS_DEGREE)
#: 不利の種類の値。
LATE_START, PACE_AGAINST, BIAS_AGAINST = "出遅れ", "展開が向かなかった", "バイアスと逆"
HANDICAP_KINDS: tuple[str, ...] = (LATE_START, PACE_AGAINST, BIAS_AGAINST)
#: 程度の値（数字は 0 なし・1 小・2 中・3 大）。
DEGREE_NAMES: dict[int, str] = {0: "なし", 1: "小", 2: "中", 3: "大"}
#: 次走の扱いの値。
REVIEW, NONE = "見直す", "なし"

#: 回顧の範囲の列（馬の回顧ノートを書いた最後の開催日）。
AS_OF = "as_of"
