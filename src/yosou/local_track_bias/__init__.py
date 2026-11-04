"""地方の当日の馬場傾向: 中央のトラックバイアスの部品（``yosou.track_bias``）を地方の元DB と地方の前らしさで動かし、
全頭の予想「地方競馬の近走と適性から3着以内を予想」の当日の材料（まとまり U。5個）にする（地方の設計書 09 の U・15 の 11）。

同じ開催日に先に終わった同じ競馬場のレースで「市場の見立てより来た馬が内か外か・前か後ろか」を傾きで数え、
過去の傾き（同じ馬場 × 開催の何日目 × 馬場状態）と混ぜ、いつもの傾きを引いた分を馬番の位置と前らしさの見込みに掛けて、馬ごとの補正にする。

中央と同じ部品: 残差の傾き（``RaceSlopes``）・当日の傾き（``DaySlopes``）・過去の傾きの表（``PriorSlopeTableBuilder``）・
使う傾き（``UsedSlopes``）・馬ごとの補正（``BiasCorrection``）・年ごとのリーク防止（``YearlyBias``）・学習データに足す（``BiasAttachment``）・
出走の読み込み（``BiasRunRepository``。事実表の元を見分けるので、地方の元DB ではそのまま地方の出走を読む）。
地方で違うのは、前らしさの見込みである。中央は展開の予想④（4コーナーの位置の予想）を使うが、地方には展開の予想が無いので、
その馬の直近3走の4コーナーの位置の平均（0 が先頭、1 が最後方）を使う。

| 名前 | 仕事 |
|---|---|
| ``FrontPosition`` | 過去の全出走（傾きの元の表）から、馬ごとに「そのレースより前の直近3走の4コーナーの位置の平均」を出す |
| ``PastPositionRepository`` | これから走る1レースの出走馬の、直近3走の4コーナーの位置の平均を事実表から読む（``repository/``） |
| ``LocalBiasHistory`` | 過去の全出走に、年ごとの過去の傾きと先に終わったレースの傾きで U を付ける（学習と確かめ用） |
| ``LocalFrontForecast`` | これから走る1レースの出走馬の前らしさの見込みを返す関数の形（``RaceBiasSource`` の ``forecast`` に渡す） |
| ``LOCAL_TRACK_BIAS_FEATURES`` | U の一覧（名前は中央と同じ5個。当日から分かる） |
| ``local_bias_cache_folder_beside`` | レースごとの傾きと過去の傾きの表をとっておく場所（モデルの置き場所の2つ上の ``地方の当日の馬場傾向/cache/``） |
| ``TrackBiasMarker`` | モデルの置き場所に「当日のモデルを U で学んだ」印を書く・読む（``train --track-bias`` が書き、``backtest``・``predict`` が読んで U を足すか決める。本番のモデルは印なし＝U なし） |

決まり: 1ファイルに1クラス。SQL は ``repository/`` だけ。``yosou.track_bias``・``yosou.shared`` は参照してよいが、そこからここを参照しない。
"""

from .cache_folder import LOCAL_BIAS_CACHE_FOLDER, local_bias_cache_folder_beside
from .features import LOCAL_TRACK_BIAS_FEATURES
from .front_position import FRONT_POSITION, RECENT_RUNS, FrontPosition
from .local_bias_history import LocalBiasHistory
from .local_front_forecast import LocalFrontForecast
from .repository import PastPositionRepository
from .track_bias_marker import MARKER_FILE, TrackBiasMarker

__all__ = [
    "FrontPosition", "FRONT_POSITION", "RECENT_RUNS", "PastPositionRepository", "LocalBiasHistory", "LocalFrontForecast",
    "LOCAL_TRACK_BIAS_FEATURES", "LOCAL_BIAS_CACHE_FOLDER", "local_bias_cache_folder_beside", "TrackBiasMarker", "MARKER_FILE",
]
