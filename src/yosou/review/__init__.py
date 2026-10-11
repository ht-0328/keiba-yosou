"""回顧データ: レースのあとに Python が JV-Data から自動で作る3つの表（買い目の記録・レースの回顧・馬の回顧ノート）と、
馬の回顧ノートから作る次走の材料「前走の不利」（設計書「買うレースと買い目を決める」08 の 3）。

不利は JV-Data から自動で分かる3つだけ（出遅れ・展開が向かなかった・バイアスと逆）。進路の妨害など、人が映像を見ないと分からない不利は扱わない。
表は ``reports/回顧/review.duckdb``（Git の対象外）に置き、NotebookLM には上げない（利用者の決定）。

| 名前 | 仕事 |
|---|---|
| ``ReviewRunRepository`` | 回顧の元になる、中央・平地の全出走を読む |
| ``EarlyPositions`` | 出走ごとの実際の序盤の位置と、見込みの序盤の位置（近5走の平均） |
| ``ResultStyle`` | 出走ごとの結果の脚質（その走の最初のコーナーの位置から） |
| ``HandicapLines`` | 不利の線と程度（0 なし〜3 大）の分け方 |
| ``RunHandicaps`` | 終わった出走ごとに3つの不利と程度・次走の扱いを出す |
| ``HandicapHistory`` | 全出走に、年ごとに「その年より前のレースだけで作った表」で不利を付ける（リークを防ぐ） |
| ``RaceReviews`` | レースごとの回顧（表2。予想と結果のペース・終わった日のバイアスの傾き・馬場状態） |
| ``ReviewStore`` | 3つの表を ``reports/回顧/review.duckdb`` に書く・読む |
| ``BetSettler`` | 買い目の記録（表1）の未精算の行に払戻を書き足す |
| ``ReviewWorkflow`` | 終わったレースの表2・表3を作って保存し、表1を精算する |
| ``PreviousHandicapColumns`` | 不利の表から、出走ごとの前走の不利（まとまり X）を作る |
| ``PreviousRunRepository``・``StoredHandicapLookup`` | これから走る馬の前走を読み、保存した表3から X を引く（予測用） |
| ``RacePreviousHandicapAttacher`` | 1レースの予測用データに X を足す関数の形（全頭の予想の予測の流れに渡す） |
| ``PreviousHandicapAttachment``・``PreviousHandicapFreeData`` | 学習データ・予測用データに X を足す・外す |
| ``PREVIOUS_HANDICAP_FEATURES`` | 前走の不利を予想の特徴量にするときの一覧（まとまり X。5個） |
"""

from .bet_settler import BetSettler
from .early_positions import EarlyPositions
from .features import PREVIOUS_HANDICAP_FEATURES, PREVIOUS_HANDICAP_NAMES
from .handicap_history import HandicapHistory
from .handicap_lines import HandicapLines
from .previous_handicap_attachment import PreviousHandicapAttachment
from .previous_handicap_columns import PreviousHandicapColumns
from .previous_handicap_free_data import PreviousHandicapFreeData
from .previous_run_repository import PreviousRunRepository
from .race_previous_handicap_attacher import RacePreviousHandicapAttacher
from .race_reviews import RaceReviews
from .result_style import ResultStyle
from .review_run_repository import ReviewRunRepository
from .review_store import DEFAULT_REVIEW_DB, ReviewStore
from .review_workflow import ReviewWorkflow
from .run_handicaps import RunHandicaps
from .stored_handicap_lookup import StoredHandicapLookup

__all__ = [
    "ReviewRunRepository", "EarlyPositions", "ResultStyle", "HandicapLines", "RunHandicaps", "HandicapHistory", "RaceReviews",
    "ReviewStore", "DEFAULT_REVIEW_DB", "BetSettler", "ReviewWorkflow", "PreviousHandicapColumns", "PreviousRunRepository",
    "StoredHandicapLookup", "RacePreviousHandicapAttacher", "PreviousHandicapAttachment", "PreviousHandicapFreeData",
    "PREVIOUS_HANDICAP_FEATURES", "PREVIOUS_HANDICAP_NAMES",
]
