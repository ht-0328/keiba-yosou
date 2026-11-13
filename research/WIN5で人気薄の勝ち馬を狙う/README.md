# WIN5で人気薄の勝ち馬を狙う

**何をする研究か。** WIN5 の予想（設計書「近走と適性からWIN5の買い目を決める」）が、10番人気以下の勝ち馬（16番人気のような大穴も含む）を買い目に入れられるようにする。そのために、人気薄が勝ったレースを集めて1つずつ見て、人が言葉で説明できる「人気薄が勝つときの形」を作り、それをもとに人気薄を選べる予想の学び方と、WIN5 の買い目への入れ方を決める。

**なぜ始めたか。** WIN5 の予想は、1着の確率を今のモデル（今毎週の予想に使っているモデル。設計書「近走と適性から3着以内を予想」）から借りている。過去の WIN5 で数えると、買い目に入る馬の半分が1〜2番人気で、10番人気以下は 4〜7% しかない。2026-11-08 の WIN5 では、1レース目を締め切り前に 11番人気だった馬が、4レース目（18頭立て）を 16番人気が勝った。今のモデルは、この2頭にオッズから見た勝率とほぼ同じ確率しか付けていなかった。利用者からは「16番人気が1着だったけど、これも含めてちゃんと狙えるように予想しろ」と言われた。

**進め方。** 事例 → 理論 → 確かめ の順で進める。いきなり材料の総当たりから入らない。人気薄を狙う予想で、今のモデルが人気上位しか選べないことを、並べ替えや期待値による絞り込みのような後で手を加える方法では直さない。学び方（目的変数・学ぶ行・人気の与え方・重み）に手を入れる。

数値（JV-Data 由来の馬名・オッズ・払戻と、細かい成績の表）は Git 対象外の `reports/WIN5で人気薄の勝ち馬を狙う/` に出し、この README と docs には回数と割合だけを書く。

## 今どこまで進んだか

| 段 | 中身 | 文書 | 状態 |
|---|---|---|---|
| 1. 事例 | 2019年からの WIN5 の対象レースと平地の全レースで、10番人気以下が勝ったレースを集め、2026-11-08 の2レースを詳しく見た | [docs/01-事例.md](docs/01-事例.md) | 済み |
| 1. 理論 | 「荒れそうなレース」（レースの側）と「勝ちそうな人気薄」（馬の側）の型にまとめ、見分けられそうかを書いた | [docs/02-理論.md](docs/02-理論.md) | 済み |
| 2. 次の段の案 | 人気薄を選べる予想の学び方、WIN5 の買い目への入れ方、確かめ方 | [docs/03-次の段の案.md](docs/03-次の段の案.md) | 済み（おすすめで進めた） |
| 2. 人気薄の1着の予想と WIN5 の抑え | 人気薄の1着の予想（荒れる前提の予想）を区切りごとに学び直して比べ、WIN5 の本線（今の買い目）はそのままに、本線と重ならない「抑え」の買い目を足して確かめた | [docs/04-段2の結果.md](docs/04-段2の結果.md) | 済み。採用しない（段3 には進まない） |

## この文書で使う言葉の意味

| 言葉 | 意味 | 例（架空） |
|---|---|---|
| 人気薄 | 確定の単勝人気が 10番人気以下の馬 | 18頭立ての 16番人気 |
| オッズから見た勝率 | 単勝オッズの逆数を、レースの中で合計 1 にそろえたもの。市場が見たその馬の勝つ確率 | 4倍・4倍・2倍の3頭なら 0.25・0.25・0.5 |
| 人気薄の市場合計 | そのレースの人気薄全部の、オッズから見た勝率の合計。市場が「人気薄のどれかが勝つ」と見た確率 | 0.12 なら、8回に1回くらい人気薄が勝つと市場が見ている |
| 市場が見た数 | 人気薄の市場合計を、レース（または馬）について足したもの。市場の見立てどおりなら、この数だけ人気薄が勝つ | |
| 実際 ÷ 市場 | 人気薄が実際に勝った数 ÷ 市場が見た数。1 より大きければ、市場が見落としている | |
| 集まり方 | ある手がかりに当てはまる人気薄の勝率 ÷ 人気薄全体の勝率。大きいほど、その手がかりが勝ち馬に集まっている | |
| 上乗せ | 今のモデルの1着の確率 ÷ オッズから見た勝率 | 0.02 ÷ 0.01 = 2.0 |
| レースの側の型 | 人気薄が勝ちやすいレースの形（R1〜R4）。[docs/02 の 2.](docs/02-理論.md#2-レースの側の型荒れそうなレース) | 人気薄に票が残るハンデ戦 |
| 馬の側の型 | 勝った人気薄に多い形（A〜G）。[docs/02 の 3.](docs/02-理論.md#3-馬の側の型勝ちそうな人気薄) | 前で運べば走る馬が、前の走は後ろで負けた |

## フォルダの中身

| 場所 | 何があるか |
|---|---|
| `cases.py` | 入口（段1）。事例の表と一覧を書く |
| `forecast.py` | 入口（段2 の①）。型の材料の表を作り（`features`）、人気薄の1着の予想を作り方ごと・時点ごとに区切りごとに学び直して予測を残す（`train`） |
| `evaluate.py` | 入口（段2 の②）。作り方を人気薄の中の並べ方で選び、WIN5 の本線（今の買い目）に足す抑えの候補を過去の WIN5 で精算して選び・確かめ、2026-11-08 を予想し直す |
| `analysis/case_study.py` | 段1 の流れ（読む → 列を足す → 型を付ける → 表 → 書く） |
| `analysis/repository/` | 元DB を読むリポジトリ（1 SQL につき 1 クラス）。事実表の出走の行 `runner_facts_repository.py`・WIN5 の対象レース `win5_leg_repository.py` |
| `analysis/enrichment/` | 出走の表に列を足す部品。過去走 `runner_history.py`・騎手と調教師の前の年の勝率 `people_rates.py`・父の産駒の馬場ごとの勝率 `sire_going_rates.py`・オッズから見た勝率と人気の割れ方 `race_market_shape.py`・結果側の様子 `race_outcome_side.py`・今のモデルの1着の確率（区切りごとの予測 `fold_win_predictions.py`、最近の WIN5 の日は予想の記録 `win5_record_probabilities.py`）と上乗せ `model_uplift.py`・流れ `runner_enrichment.py` |
| `analysis/theory/` | 手がかりと型の決めごと。名前の付いた真偽の決まり `flag_rule.py`・手がかりの一覧 `clue_catalog.py`・馬の側の型 `runner_type_catalog.py` と付け方 `runner_type_flags.py`・レースの側の型 `race_type_catalog.py`・1行 = 1レースの表 `race_table.py` |
| `analysis/tables/` | 表（事例の数・勝ち馬の人気・分布・レースの型・手がかりと型の割合・前半と後半の年・人気薄の中の並べ方・今のモデルの見方・結果側の様子・詳しく見る日・事例の一覧） |
| `analysis/case_report.py` | 表を Markdown にまとめて書く |
| `analysis/longshot_forecast/` | 段2 の人気薄の1着の予想。型の材料 `type_features.py`（元DB から作って保存 `type_feature_source.py`）・学習データ `longshot_data.py` `longshot_dataset.py`（今のモデルの学習の表＋型の材料。出発点を今のモデルにする `current_baseline.py`）・作り方 `longshot_variant.py` `longshot_variants.py`・重み `race_weights.py`・学び方（重みつき二値分類 `weighted_lightgbm.py` `weighted_catboost.py`、並べ替え `rank_lightgbm.py` `rank_catboost.py`、点数を確率に `rank_probability.py`）・区切り `longshot_windows.py`・区切りごとの学び直し `longshot_window_trainer.py` `longshot_walk_forward.py`・置き場所 `longshot_prediction_store.py`・今のモデルの確率と合わせる `combined_win_share.py`・確かめの表 `evaluation_frame.py` `ordering_capture_table.py` `probability_fit_table.py` `longshot_evaluation.py`・詳しく見る日の材料 `focus_day_data.py` |
| `analysis/win5_longshot/` | 段2 の WIN5 の本線と抑え。荒れそうなレース `upset_legs.py`・抑えの候補 `hedge_candidate.py` `hedge_candidates.py`・抑えの組み方 `hedge_formation.py`・1日の精算 `hedge_day_bets.py`・人気薄の勝ち馬を含めたか `longshot_coverage.py`・成績と表 `hedge_summary.py` `hedge_table.py` `hedge_year_table.py`・採用の決まり `hedge_adoption_judge.py`・流れ `win5_hedge_study.py`・詳しく見る日 `focus_day_runner.py` `focus_day_study.py` |
| `docs/` | 01 事例・02 理論・03 次の段の案・04 段2 の結果 |
| `tests/` | 合成DB と架空の値で部品を確かめるテスト（実DB は要らない） |
| `reports/WIN5で人気薄の勝ち馬を狙う/`（Git 対象外） | `事例.md`（全部の表）・`WIN5の事例.csv`（WIN5 の対象レースで人気薄が勝った全部の事例）・`平地の事例.csv`（平地の全部の事例）・`型の材料.pkl`・`predictions/`（作り方ごとの区切りごとの予測と、人気薄を置き換えた予測 `combined-*`）・`段2の結果.md`（段2 の全部の表）・`WIN5の精算.csv`（本線と抑えの日ごとの精算） |

## 動かし方

リポジトリ直下（`keiba-yosou/`）から実行する。元DB は jvdata-store の `jvdata.duckdb`（読むだけ）。今のモデルの1着の確率は、研究「複勝以外の回収率100超」の区切りごとの予測（`reports/複勝以外の回収率100超/predictions-2019から/dscore_finish_race_day/win-race_day.pkl`）を使う。

```bash
uv run python research/WIN5で人気薄の勝ち馬を狙う/cases.py                    # 段1: 事例の表（1〜2分）
uv run python research/WIN5で人気薄の勝ち馬を狙う/cases.py --focus 2026-11-01   # 詳しく見る WIN5 の日を変える
uv run python research/WIN5で人気薄の勝ち馬を狙う/forecast.py features           # 段2: 型の材料（2分）
uv run python research/WIN5で人気薄の勝ち馬を狙う/forecast.py train --timings 当日 前日   # 段2: 作り方ごとに区切りごとに学び直す（数時間）
uv run python research/WIN5で人気薄の勝ち馬を狙う/evaluate.py                  # 段2: 作り方を選び、WIN5 の本線と抑えで確かめる（30分ほど）
uv run python -m pytest research/WIN5で人気薄の勝ち馬を狙う -q                 # 部品のテスト
```

開催日のレースの時間（発走前の通知が動いている間）には、元DB を使うこの入口を動かさない。
