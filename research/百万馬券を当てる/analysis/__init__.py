"""研究「百万馬券を当てる」の部品。

帯・荒れたレースの線、1レースの予算、買い方（一律・甲・乙・丙）と組の確率は、本番の予想 ``yosou.upset_premise`` のものを使う。
ここには、事例を見る・区切りごとに学ぶ・確かめる部品だけを置く。

| ファイル | 仕事 |
|---|---|
| ``obi_rules.py`` | 払戻の段（帯・大荒れ・それ以外）、理論を作る年と確かめる年、人気薄（関数と定数だけ） |
| ``race_table_loader.py`` | ``RaceTableLoader``: レース単位の表を読み、帯・大荒れの目的変数を足す |
| ``race_frame.py`` | ``race_frame``: レース単位の表を、事例を見るための1つの表にする |
| ``horse_frame.py`` | ``horse_frame``: 馬ごとの表に、そのレースの払戻の段を付ける |
| ``lift_table.py`` | ``LiftTable``: 切り口の値ごとに、事象がどれだけ集まったかを数える |
| ``race_case_report.py`` | ``RaceCaseReport``: 帯のレースの事例と、切り口ごとの帯の集まり方（手順1） |
| ``horse_case_report.py`` | ``HorseCaseReport``: 荒れたレースで来た人気薄と来なかった人気薄（手順5） |
| ``race_obi_window_trainer.py`` | ``RaceObiWindowTrainer``: 1つの区切りで、帯になる確率（か 1,000倍以上になる確率）のモデルを学ぶ（第1段） |
| ``wild_only_window_trainer.py`` | ``WildOnlyWindowTrainer``: 1つの区切りで、荒れたレースだけで馬ごとのモデルを学ぶ（第2段） |
| ``crowded_split_rule.py`` | ``crowded_split_score``: 条件のルール「多頭数で人気が割れている」の点数（第1段） |
| ``race_selection_scores.py`` | ``RaceSelectionScores``: レースごとに、選び方ごとの点数を並べる |
| ``selection_precision.py`` | ``SelectionPrecision``: 点数ごとに、同じレース数を選んだときに実際に 1,000倍以上だった割合を並べる（docs/06 の 2） |
| ``day_race_picker.py`` | ``DayRacePicker``: 開催日ごとに、点数がいちばん高いレースを1つ選ぶ |
| ``day_bootstrap.py`` | ``DayBootstrap``: 開催日を単位にしたブートストラップで、比の 90% の幅を出す |
| ``selection_summary.py`` | ``SelectionSummary``: 選んだレースに帯がどれだけ集まったか（手順4） |
| ``finish_loader.py`` | ``FinishLoader``: 馬ごとの表から、確定着順と確定の人気を読む |
| ``race_horses_builder.py`` | ``RaceHorsesBuilder``: 保存した予測から、レースごとの出走馬の予想を作る |
| ``prediction_coverage.py`` | ``PredictionCoverage``: 予想の上位の馬が1〜3着に来たか、人気薄を選べているか（手順7の前半） |
| ``selected_combo_odds.py`` | ``SelectedComboOdds``: 選んだレースの3連単・3連複の確定オッズを読む |
| ``big_combo_odds.py`` | ``BigComboOdds``: 選んだレースの 1,000倍以上の3連単の組の確定オッズを、小さい表で持つ（docs/06 の 3） |
| ``plain_flat_plan.py`` | ``PlainFlatPlan``: 一律の買い方の比べる相手（組の確率を元の Harville の式にしたもの） |
| ``flat_hit_summary.py`` | ``FlatHitSummary``: 一律の買い方の、1,000倍以上で決まったレースのうち当てた割合（docs/06 の 3） |
| ``winning_combos.py`` | ``trifecta_winners``・``trio_winners``: 確定着順から当たりの組を作る |
| ``ticket_maker.py`` | ``TicketMaker``: 選んだレースごとに、買い方に従って買い目を作る |
| ``ticket_settler.py`` | ``TicketSettler``: 買い目を確定着順と確定オッズで精算する |
| ``betting_summary.py`` | ``BettingSummary``: 精算した買い目から、買い方ごとの成績を1行にまとめる（手順7） |
"""
