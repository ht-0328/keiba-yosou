"""対戦レーティング（まとまり O）の列の名前と、レーティングの決めごと。"""

from __future__ import annotations

#: 行を突き合わせる鍵（木曜は馬番が無いので、馬で突き合わせる）。
KEY: list[str] = ["race_id", "horse_id"]

#: そのレースの前日までのレーティングと、それまでに勝ち負けを数えたレースの数。
RATING = "対戦レーティング"
RUN_COUNT = "対戦レーティングの対戦数"
#: レーティングの動き（前走で動いた幅と、近5走で動いた幅）。
LAST_CHANGE = "対戦レーティングの前走での変化"
RECENT_CHANGE = "対戦レーティングの近5走の変化"
#: 同じレースの出走馬の中での位置。
FIELD_RANK = "対戦レーティングのレース内順位"
FIELD_Z = "対戦レーティングのレース内偏差"
FIELD_GAP = "対戦レーティングとレースの平均との差"

#: まとまり O の列の並び（7個。どれも小数）。
HEAD_TO_HEAD_NAMES: tuple[str, ...] = (RATING, FIELD_RANK, FIELD_Z, FIELD_GAP, LAST_CHANGE, RECENT_CHANGE, RUN_COUNT)

#: 初めて走る馬のレーティング。
INITIAL_RATING = 1500.0
#: レーティングの差を勝つ見込みに直す尺度（差が 400 なら、勝つ見込みが 10 倍）。チェスの Elo と同じ。
SCALE = 400.0
#: 1レースで動く幅の上限（K）。走った数が少ない馬は、早く本当の力に寄せるために大きくする。
K_FACTOR = 20.0
K_FACTOR_NEW = 40.0
#: この数より少ないレースしか走っていない馬に、大きい K を使う。
NEW_HORSE_RUNS = 5
#: 「近5走の変化」で見る走の数。
RECENT_RUNS = 5
