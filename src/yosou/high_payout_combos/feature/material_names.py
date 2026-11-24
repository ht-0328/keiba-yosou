"""馬ごとの材料の名前（組の位置ごとに付ける 20個と、Harville の式に使う2個）。

| 名前 | 意味 |
|---|---|
| ``pw``・``p3`` | 予想の1着の確率・3着以内の確率 |
| ``mw``・``m3`` | 単勝オッズから見た勝率・3着以内率 |
| ``pm`` | 複勝オッズから見た3着以内率 |
| ``e3`` | p3 − pm（予想が複勝の市場より高く見ている分） |
| ``r3``・``rw``・``rpm`` | log(p3 ÷ m3)・log(pw ÷ mw)・log(p3 ÷ pm) |
| ``lwo``・``lpo`` | log(単勝オッズ)・log(複勝オッズの真ん中)。1倍未満は 1倍として扱う |
| ``pop``・``rk`` | 単勝人気・予想の順位 |
| ``dg``・``ds`` | 危険な人気馬か（1 か 0）・その点数 |
| ``psup`` | 3連単の板から見た勝率 ÷ mw |
| ``mk`` | 印の番号（◎0 ○1 ▲2 △3 ☆4 注5 －6 消7） |
| ``updown``・``wv``・``pv`` | 予想の上げ下げ・単勝の期待値・複勝の期待値 |
| ``pwn``・``mwn`` | pw・mw をレースで合計 1 にそろえた値（Harville の式のもと。組の位置ごとの材料にはしない） |
"""

PW, P3, MW, M3, PM = "pw", "p3", "mw", "m3", "pm"
E3, R3, RW, RPM = "e3", "r3", "rw", "rpm"
LWO, LPO, POP, RK = "lwo", "lpo", "pop", "rk"
DG, DS, PSUP, MK = "dg", "ds", "psup", "mk"
UPDOWN, WV, PV = "updown", "wv", "pv"
WIN_SHARE, MARKET_WIN_SHARE = "pwn", "mwn"

#: 組の位置ごとに付ける馬の材料（20個。この並びで列を作る）。
POSITION_MATERIALS: tuple[str, ...] = (
    PW, P3, MW, M3, PM, E3, R3, RW, RPM, LWO, LPO, POP, RK, DG, DS, PSUP, MK, UPDOWN, WV, PV,
)
#: 馬ごとの材料の全部（位置ごとの 20個と、Harville の式のもと2個）。
HORSE_MATERIALS: tuple[str, ...] = (*POSITION_MATERIALS, WIN_SHARE, MARKET_WIN_SHARE)
#: 対数や割り算の前に当てる下限（確率 0 で −∞ や 0 割りにならないように）。
FLOOR = 1e-9
