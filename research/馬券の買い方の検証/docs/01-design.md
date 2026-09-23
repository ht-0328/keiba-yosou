# 01 設計（データの流れ・クラス・列名）

**この文書の目的:** 研究コードが何をどの順で計算するかと、部品（クラス）の一覧、表の列名をまとめる。決めごと（期間・基準）は [03-protocol.md](03-protocol.md)、買い方の一覧は [02-ticket-plans.md](02-ticket-plans.md)。

## データの流れ

```
predict_all.py（入口①）
  元DB を開く → 4モデルの学習データを作る部品で 2025-07-01〜2026-09-30 の特徴量を作る → 閉じる
  → 保存済みの当日モデルで予測 → reports/馬券の買い方の検証/predictions/<モデル名>.csv（4つ）と manifest.json

backtest.py（入口②）
  --check-data : 予測・事実表・確定オッズ・払戻を読み、数だけ出す
  --settle-only: 買い方（ticket_plans.py の全部）× 全レースの買い目を作り、払戻と照合して精算表 settlement.csv を作る
  （既定）     : 精算表を読み、探索期間のレースで 参加パターン × しきい値 × 買い方 の戦略を全部評価し、採否の基準で絞って chosen.json に書く
  --confirm    : chosen.json の戦略だけを確認期間で評価する（1回だけ）
```

要点は、**買い目の生成と払戻の照合を「買い方 × レース」で1回だけ計算し（精算表）、戦略の探索は精算表の行を選んで足すだけ**にすること。
しきい値を変えても買い目は変わらないので、数千の戦略を数分で回せる。

## 部品の一覧

`analysis/` の各フォルダの `__init__.py` に「クラス → 仕事」の表がある。フォルダの役割:

| フォルダ | 仕事 |
|---|---|
| `prediction/` | 4モデルの当日予測を期間ぶん一括で出して CSV に残す（`RunnerBatchPredictor`・`RaceBatchPredictor`） |
| `repository/` | 元DB から期間ぶんを読む。1 SQL = 1クラス（レースの属性・確定オッズ・払戻の明細・払戻のフラグ） |
| `loading/` | 予測の CSV と元DB から、材料表（`RaceMaterials`）と帳簿（`OddsBook`・`PayoutBook`）を組み立てる |
| `race_material/` | 予測と事実を、1行 = 1レースの `races` と 1行 = 1頭の `runners` にまとめる |
| `ticket/` | 買い方（券種・列の指定・候補の選び方）から 1レースの買い目を作る。目録は `ticket_plans.py` |
| `participation/` | 参加パターン①〜⑥。買うレースと広め/少点数の別を決める |
| `settlement/` | 買い目を払戻と照合し、レース × 買い方 の精算表を作る。低配当目のカットもここ |
| `summary/` | 回収率のまとめと、人が読む表 |
| `search/` | しきい値の格子で戦略を作り、評価し、採否の基準で絞り、確認期間で確かめる |

## 材料表の列

`runners`（1行 = 1頭。列名は `analysis/column_names.py`）:

| 列 | 意味 | 出どころ |
|---|---|---|
| race_id / race_date / horse_no | レースID（16桁）・開催日・馬番 | 近走と適性モデルの予測 |
| finish / win_odds / popularity | 確定着順・確定の単勝オッズ・確定の単勝人気 | 同上（評価用の列） |
| win_payout / place_payout | その馬の単勝・複勝の払戻（円。外れは 0） | 同上 |
| form_prob | 近走と適性モデルの「3着以内に入る確率」 | 同上 |
| danger_prob | 危険な人気馬モデルの「4着以下になる確率」。人気馬でなければ欠損 | 人気馬モデルの予測 |
| longshot_prob / longshot_zone | 穴馬モデルの「3着以内に入る確率」と区分（中穴・大穴）。穴馬でなければ欠損 | 穴馬モデルの予測 |

`races`（1行 = 1レース）:

| 列 | 意味 | 出どころ |
|---|---|---|
| race_id / race_date / venue_code / race_no / surface / distance_m / class_order / grade_code / field_size | レースの属性 | 事実表（`tools/共通/facts.py`） |
| is_graded | 重賞か（グレードコード A〜D） | 事実表 |
| week | 開催週の鍵（その週の土曜日。土日と月曜の振替が同じ週） | `RaceWeek` |
| upset_win / upset_quinella / upset_trio / upset_trifecta | 券種ごとの「中荒れ以上の確率」 | 荒れ具合モデルの予測 |
| favorite_no / favorite_prob / favorite_danger | 本命（近走と適性の確率が最大の馬。同点は人気上位）の馬番・確率・危険確率 | runners から |

## 精算表の列（settlement.csv）

| 列 | 意味 |
|---|---|
| race_id / plan | レースID・買い方の名前 |
| points / stake_yen / payout_yen / hit_count | 点数・賭け金（1点 100円）・払戻の合計（円）・当たった買い目の数 |
| skipped | 見送りの理由（買ったときは空）。候補が足りない・本命が1番人気でない・本命のオッズが低い・払戻データなし・不成立・オッズなし・カット後に買い目なし |

## 戦略の評価

1. 参加パターンが、しきい値（荒れ度・本命の確率・危険確率・週の上位 k）で、買うレースと広め/少点数の別を決める（`Participation`）。
2. 広めの買い方の精算表の行（広めで買うレース）と、少点数の買い方の行（少点数で買うレース）を取り、レース単位に足す。
3. `ReturnSummary`（レース数・買ったレース・点数・賭け金・払戻・的中レース率・最大の1レースを除く回収率）と月別のまとめにする。

荒れ度の線は「上位 x%」で指定し、探索期間の分布から確率に直す（券種ごとに分布が違うため）。直した確率は `chosen.json` に持たせ、確認期間でもそのまま使う。

## 荒れ判定に使う券種

広めの買い方の券種に対応する荒れ具合の券種で判定する: 単勝・複勝 → 単勝、馬連・ワイド・馬単 → 馬連、3連複 → 3連複、3連単 → 3連単（`TicketTypeSpec.upset_bet`）。

## 対象外

- 障害レース（予測に無い）、WIN5・枠連（券種の目録に無い）。
- 締め切り前のオッズ（元DB にほぼ無い。確定オッズで代用。[03-protocol.md](03-protocol.md)）。
