"""馬体重の表の、帯の名前と表の列の名前。"""

from __future__ import annotations

#: 帯の列。
CHANGE_BAND, INTERVAL_BAND, AGE_BAND = "増減の帯", "間隔の帯", "馬齢の組"
BANDS: tuple[str, ...] = (CHANGE_BAND, INTERVAL_BAND, AGE_BAND)

#: 増減の帯（kg。設計書「買うレースと買い目を決める」06 の 2）。
CHANGE_BIG_LOSS, CHANGE_LOSS, CHANGE_FLAT, CHANGE_GAIN, CHANGE_BIG_GAIN = "−10kg以下", "−9〜−4kg", "−3〜+3kg", "+4〜+9kg", "+10kg以上"
CHANGE_BANDS: tuple[str, ...] = (CHANGE_BIG_LOSS, CHANGE_LOSS, CHANGE_FLAT, CHANGE_GAIN, CHANGE_BIG_GAIN)
#: 前走からの間隔の帯（中3週以内 = 前走から 28日以内、4〜9週 = 29〜70日、10週以上 = 71日以上の休み明け）。
INTERVAL_SHORT, INTERVAL_MIDDLE, INTERVAL_LONG = "中3週以内", "4〜9週", "10週以上"
INTERVAL_BANDS: tuple[str, ...] = (INTERVAL_SHORT, INTERVAL_MIDDLE, INTERVAL_LONG)
#: 馬齢の組。
AGE_YOUNG, AGE_OLD = "2〜3歳", "4歳以上"
AGE_BANDS: tuple[str, ...] = (AGE_YOUNG, AGE_OLD)

#: 表の列。
TOP3 = "3着以内"
MARKET_TOP3 = "市場から見た3着以内率"
COUNT, RAW_GAP, BAND_GAP, GAP = "件数", "差", "増減の帯の差", "縮めた差"
#: 馬ごとの割引の列（特徴量にもなる）。
DISCOUNT = "体重の割引"

#: 判定の列と値（出馬表の表示用。線は −0.02。設計書「買うレースと買い目を決める」07 の 3）。
VERDICT = "判定"
DISCOUNTED, NEUTRAL = "体重の割引", "－"
