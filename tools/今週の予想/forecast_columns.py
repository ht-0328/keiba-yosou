"""今週の予想で使う、1レースの表の列の名前。"""

from __future__ import annotations

HORSE_ID = "horse_id"
HORSE_NO = "horse_no"
HORSE_NAME = "horse_name"
#: 3着以内に入る確率（予想。2つのモデルの平均）。
PROBABILITY = "probability"
#: 1着になる確率（1着のモデル。2つのモデルの平均。1着のモデルが無ければ欠損値）。
WIN_PROBABILITY = "win_probability"
#: 単勝オッズ（前日・当日だけ。木曜は欠損値）。
WIN_ODDS = "win_odds"
#: 単勝の期待値（1着になる確率 × 単勝オッズ。前日・当日だけ。◎ を決めるのに使う）。
WIN_VALUE = "win_value"
#: 単勝人気（単勝オッズの低い順。オッズが無ければ欠損値）。
POPULARITY = "popularity"
#: オッズから見た3着以内率（市場の見立て。前日・当日だけ）。
MARKET_TOP3 = "market_top3"
#: オッズから見た勝率（市場の見立て。前日・当日だけ。組の期待値の「1着の比」に使う）。
MARKET_WIN = "market_win"
#: 複勝の期待値（3着以内の確率 × 見込みの払戻倍率。前日・当日だけ）。
PLACE_VALUE = "place_value"
#: 上げ下げ（logit(予想) − logit(市場の見立て)。市場より来ると見る度合い。前日・当日だけ）。
UPDOWN = "updown"
#: 3着以内に入る確率のレース内順位（1 が最上位）。
RANK = "rank"
#: 印（◎○▲△☆注消と無印 －）と、その印になった理由（1文）。
MARK = "mark"
MARK_REASON = "mark_reason"
#: 軸（◎○▲のうち3着以内の確率がいちばん高い馬なら真。◎ と同じ馬のことも ○ のこともある。設計書「買うレースと買い目を決める」07 の 5）。
#: 3連複・3連単の「軸馬」のパターンで軸にする。
AXIS = "axis"
#: レースの期待度（高・低。◎ の単勝の期待値が 1.00 以上なら高。期待値の無い木曜は欠損値。
#: 設計書「近走と適性から3着以内を予想」の 16 の 6）。レースの全頭に同じ値が入る。
EXPECTATION = "expectation"
#: 危険な人気馬の判定（人気馬だけ。前日・当日だけ。設計書「買うレースと買い目を決める」07 の 3）。
#: 人気帯・4着以下になる確率（人気馬の予想）・市場から見た4着以下の確率・危険度（その差）・人気帯の線・危険か。
FAVORITE_BAND = "favorite_band"
OUT_PROBABILITY = "out_probability"
MARKET_OUT = "market_out"
DANGER_SCORE = "danger_score"
DANGER_LINE = "danger_line"
IS_DANGER = "is_danger"
DANGER_COLUMNS: tuple[str, ...] = (FAVORITE_BAND, OUT_PROBABILITY, MARKET_OUT, DANGER_SCORE, DANGER_LINE, IS_DANGER)
