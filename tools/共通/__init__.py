"""ツール同士で使い回す部品。入口（main）は持たない。

- ``db``       元DB を読み取り専用で開く（ロック付き）
- ``keys``     レースと馬の鍵、中央だけ・確定成績の条件、最新行の選び方
- ``codes``    JV-Data のコード値と名前
- ``facts``    事実表（1行=1頭の出走）
- ``filters``  絞り込み（CLI のフラグ = 画面の URL パラメータ）
- ``perf``     成績7つの集計と切り口
- ``events``   人気馬が負けた・穴馬が勝った
- ``race`` / ``horse`` / ``runners`` / ``browse``  レース・馬・出走・表の読み出し
- ``card``     出馬表（これから走るレースの一覧、出走馬、各馬の近走）
- ``trend`` / ``trend_items`` / ``trend_backtest`` / ``trend_html``  傾向スコア（採点・項目の登録簿・検証・グラフ付きの HTML）
- ``static``   画面の部品（``trend.js``）。検索画面のサーバーと ``trend_html`` が使う
- ``raw``      生の値（仕様書の桁のままの文字列）を表に出す数や文字にする
- ``render``   Markdown / CSV / JSON の整形
- ``cli``      共通の引数と実行の型
"""
