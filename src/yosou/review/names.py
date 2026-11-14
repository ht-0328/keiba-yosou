"""回顧データの、表と列の名前と、不利の種類・程度の値。"""

from __future__ import annotations

#: 回顧の DuckDB の表（設計書「買うレースと買い目を決める」08 の 3 の表1〜3と、回顧を書いた範囲）。
BETS_TABLE, RACES_TABLE, HORSES_TABLE, COVERAGE_TABLE = "買い目の記録", "レースの回顧", "馬の回顧ノート", "回顧の範囲"

#: 共通の列。
RACE_ID, RACE_DATE, HORSE_ID = "race_id", "race_date", "horse_id"

#: 表1「買い目の記録」の列。
PARTICIPATION, TICKET_TYPE, COMBO, RECORD_ONLY, STAKE_YEN = "参加の種類", "券種", "買い目", "記録だけか", "金額"
BOUGHT_PROBABILITY, BOUGHT_VALUE, BOUGHT_ODDS, ODDS_AT, PAYOUT_YEN, SETTLED = "確率", "期待値", "オッズ", "オッズの時刻", "払戻", "精算済み"
#: 参加の種類の値。勝負（単勝・馬単）は、当日の予想で買う単勝（期待値）と、◎ の単勝の期待値が 1.00 以上のレースの ◎ の馬単（複勝の勝負レースとは別に選ぶ）。
#: 勝負（組の期待値）は、当日の予想で組の期待値が線以上の馬連・馬単（全レースから選ぶ）。
#: 勝負（穴馬の複勝）は、当日の予想で6番人気以下の馬のうち、3着以内の確率が複勝オッズから見た3着以内率より線以上高い馬の複勝（全レースから選ぶ）。
MATCH, POLICY_STAKES, POLICY_DAY, MATCH_WIN = "勝負", "ノルマ（重賞）", "ノルマ（日）", "勝負（単勝・馬単）"
MATCH_COMBO = "勝負（組の期待値）"
MATCH_LONGSHOT = "勝負（穴馬の複勝）"
#: 勝負（重賞）は、当日の予想で、平地の重賞なら必ず買う ◎ の単勝（勝負レースの予算で1点。勝負用の財布から）。
#: ノルマ（重賞）は前の版の記録のためだけに残す（重賞はノルマにしない。利用者の決定 2026-11-14）。
MATCH_STAKES = "勝負（重賞）"
#: ポリシー（WIN5）は、予想「近走と適性からWIN5の買い目を決める」で日の期待値が線以上の日に買う WIN5（楽しむための参加費。ポリシー用の財布から）。
#: 1日1行で、レース ID は1レース目、買い目はフォーメーション（``3,5/6/...`` の形。レースごとの馬番を「/」で区切る）。
POLICY_WIN5 = "ポリシー（WIN5）"
#: WIN5 の券種の名前（表1の券種の列）。払戻は事実表ではなく元DB の WIN5 の表から入れる（道具「今週の予想」の ``Win5BetSettler``）。
WIN5_TICKET = "WIN5"

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
