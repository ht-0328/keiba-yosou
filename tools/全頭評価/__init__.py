"""特別登録の時点の全頭評価。登録馬の全員について、強み・弱み・有力馬の候補を 1レース 1枚の Markdown にする。

予想「特別登録馬の近走と適性から3着以内を予想」（``yosou.special_registration_top3``）の確率と寄与、事実表の数字、重賞の傾向から、
文章を定型で作る（設計書 15 の 13）。印・的中率と配当率・買い目・想定人気は出さない。

| クラス | 仕事 |
|---|---|
| ``FieldReview`` | 1レースの全頭評価を組み立てる（予測 → 事実 → 強み弱み → 重賞の傾向 → 文書） |
| ``HorseFactsRepository`` | 登録馬の行（一時表）から、評価に使う事実（近走・適性・人・血統）を読む（1 SQL） |
| ``PreviousRunRepository`` | 登録馬の前走（レース名・クラス・着順・人気・着差）を事実表から読む（1 SQL） |
| ``StakesEditionRepository`` | 重賞の過去の開催の出走馬（前走のレース名・人気、休み明け、所属、好走経験、着順、払戻）を読む（1 SQL） |
| ``RegistrationStakesMap`` | 重賞の対応表（stakes_map）に、登録の時点のレース（ra にまだ無い）を足す（1 SQL） |
| ``StakesTendencyPoints`` | 過去の開催から、登録馬ごとの「同じ条件の馬の成績」の文を作る |
| ``HorsePoints`` | 事実とモデルの寄与から、1頭の強み・弱みの文を作る |
| ``ReviewLabels`` | 特徴量の分類と名前（今週の予想の ``FeatureLabels`` に、能力スコアの分類を足す） |
| ``ReviewWriter`` | 全頭評価の文書を Markdown にする |
| ``HorseReview``・``FieldReviewDocument`` | 文書の中身（``review_document.py``） |
"""
