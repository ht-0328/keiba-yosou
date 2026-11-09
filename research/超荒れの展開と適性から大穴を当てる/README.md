# 超荒れの展開と適性から大穴を当てる

**何をする研究か。** 1レースずつの予想で、「超荒れ（大穴が来る）がある前提なら、大穴のどれが勝つか・3着以内に来るか」と「大穴が2頭以上来ることはあるか、どの組か」を、レースの展開・馬場・適性・ハンデ（斤量）から予想する方法を作る。そのために、大穴（10番人気以下）が来たレースを集めて1つずつ見て、「どんな展開・馬場になったから大穴が来たか」と「来る大穴の条件」を言葉にし、それをもとにモデルの案を書く。

**なぜ始めたか。** 利用者から「普通に1レース、1レースの予想で超荒れがある前提の場合に大穴馬でどれが勝つかを予想したモデルを考えてほしい。なんなら大穴が2頭以上入る予想とかあるのか調べてほしい」「ちゃんとレースの展開や適性とかそういうのを見て予想してほしい」「後はハンデ戦とか」と頼まれた。研究「WIN5で人気薄の勝ち馬を狙う」では、馬を1頭ずつ材料で見る作りで、人気薄の中の並べ方がオッズの順を超えられなかった。この研究では、1頭ずつの強さではなく、展開・馬場・ハンデから見る。

**進め方。** 事例 → 理論 → モデル の順で進める。モデル作り（段3 から）は、利用者の承認を得てから始める。

数値（JV-Data 由来の馬名・オッズ・払戻と、細かい成績の表）は Git 対象外の `reports/超荒れの展開と適性から大穴を当てる/` に出し、この README と docs には回数・割合・人気から見た差だけを書く。

## 今どこまで進んだか

| 段 | 中身 | 文書 | 状態 |
|---|---|---|---|
| 1. 事例 | 2015年からの平地で、大穴が1着・3着以内に2頭以上・3頭とも大穴のレースを数え、75レースを1レースずつ見た。展開の予想が当たっていたかを見た | [docs/01-事例.md](docs/01-事例.md) | 済み |
| 2. 理論 | 大穴が来る展開の型、来る大穴の条件、ハンデ戦の型、大穴2頭以上の型を、件数・割合・人気から見た差で裏付けた | [docs/02-理論.md](docs/02-理論.md) | 済み |
| 2. 次の段の案 | 展開の型で混ぜる着順の予想（おすすめ）と、ほかの案、今のモデルに足す材料の候補。利用者の確認で全頭に広げた（03 の 6） | [docs/03-次の段の案.md](docs/03-次の段の案.md) | 済み。承認ずみ |
| 1・2 の追加 | 人気馬・中穴・大穴を同じ見方で数え、負けた人気馬の型を確かめ直した | [docs/01 の 10・11](docs/01-事例.md#10-人気馬中穴大穴を同じ見方で数えたとき)、[docs/02 の 8](docs/02-理論.md#8-全頭に広げた理論人気馬中穴大穴を同じ見方で) | 済み |
| 3. モデルと確かめ | 全頭の「展開の型で混ぜる着順の予想」を15の区切りで学び直し、中穴・大穴の並べ方、組、抑えの買い目、危険な人気馬を確かめた | [docs/04-段3の結果.md](docs/04-段3の結果.md) | 済み。利用者の判断待ち |

## この文書で使う言葉の意味

| 言葉 | 意味 | 例（架空） |
|---|---|---|
| 大穴 | 確定の単勝人気が 10番人気以下の馬 | 16頭立ての 13番人気 |
| 大穴2頭以上 | 1〜3着に大穴が2頭以上入ったレース | 1着 11番人気・3着 14番人気 |
| 人気から見た差 | 実際の3着以内率（1着率） − 同じ重量種別・同じ頭数の帯・同じ単勝人気の馬がふつう出す率（ポイント）。プラスなら市場が低く見ている | 期待 4.0% に対して実際 4.6% なら +0.6 |
| 集まり方 | 大穴が来たレースの中で、ある切り口の大穴が来た数 ÷ 市場の見立て（大穴のオッズから見た勝率を大穴の中でそろえたもの）から見た数 | 1.10 なら、市場の見立てより1割多く来た |
| 結果のペース | 前3ハロンを同じ競馬場・コース・距離・クラスの基準と比べた ハイ・平均・スロー（回顧の表2。展開の予想と同じ区分）。結果側 | |
| 予想のペース | 予想「展開から着順を予想」③ の前日の時点のペースの確率（その年より前だけで学んだ年ごとの予測）。ハイが 0.45 以上なら「ハイ予想」 | |
| 位置の見込み | 予想「展開から着順を予想」①② の、前3分の1・後ろ3分の1を取る確率。0.5 以上で「前の見込み」「後ろの見込み」 | |
| いつもより前 | その走の最初のコーナーの位置（頭数で 0〜1）が、近5走の平均より 0.25 以上前。結果側 | |
| トップハンデ | そのレースでいちばん重い斤量。トップとの差 = 斤量 − トップハンデ | |
| 今のモデル | 予想「近走と適性から3着以内を予想」（今毎週の予想に使っているモデル） | |

## フォルダの中身

| 場所 | 何があるか |
|---|---|
| `cases.py` | 入口（段1・段2）。出走の表を作り、事例の表と1レースずつの事例を書く |
| `analysis/case_study.py` | 流れ（読む → 列を足す → レースの表 → 表 → 事例を選ぶ → 書く） |
| `analysis/case_sections.py` | 報告の節と表の組み立て |
| `analysis/repository/` | 読む部品（1 SQL・1つの置き場所につき 1 クラス）。事実表の出走 `runner_facts_repository.py`・締め切り前の人気 `pre_close_popularity_repository.py`・回顧の表2（結果のペース・その日の傾き）`race_review_repository.py`・回顧の表3（不利）`disadvantage_note_repository.py`・展開の予想の年ごとの予測 `pace_forecast_store.py` |
| `analysis/enrichment/` | 出走の表に列を足す部品。斤量の過去走との比べ `carried_weight_history.py`・レースの中の斤量 `carried_weight_in_race.py`・位置取り `running_position.py`・近走 `recent_form.py`・展開の予想と回顧を結ぶ `pace_attachment.py`・期待の率 `expected_rates.py`・流れ `runner_enrichment.py` |
| `analysis/theory/` | 1行 = 1レースの表 `race_table.py`（決着の分け方）・表の切り口の列 `runner_cuts.py` |
| `analysis/tables/` | 表（事例の数・締め切り前の人気・ペースの割合・予想の当たり方・勝ち方の形・人気から見た差・集まり方・大穴の組の形と組み合わせ・並べ方・事例の選び方・事例の一覧と数え） |
| `forecast.py` | 入口（段3 の①）。足す材料の表を作り（`features`）、展開の型で混ぜる着順の予想を区切りごとに学び直し（`train`）、詳しく見る日を予想する（`focus`） |
| `evaluate.py` | 入口（段3 の②）。確かめの表を書き（`report`）、道具「印の成績」に渡す 4着以下の確率の表を書く（`danger`。今のモデルの 1 − 3着以内の確率は `danger-current`） |
| `danger_search.py` | 入口（段3 の③。消の決め方の探索）。消の元（今の消・今のモデルの消）と人気帯ごとの固定の線を替えて、道具「印の成績」と同じ部品で全券種の成績を数え直し、探索の期間だけで線を選ぶ |
| `analysis/scenario_forecast/` | 段3 の予想。その日の先のレースの傾き `prior_race_bias.py`・足す材料 `scenario_materials.py`（置き場所 `scenario_material_source.py`）・学習データ `scenario_dataset.py`・作り方 `scenario_variant.py`・混ぜる重み `scenario_weights.py`・展開の型ごとの予測と混ぜ方 `scenario_predictor.py`・区切りごとの学び `scenario_window_trainer.py` |
| `analysis/scenario_evaluation/` | 段3 の確かめ。比べる相手 `comparison_files.py`・確かめの表の元 `evaluation_frame.py`・人気帯 `popularity_band.py`・並べ方 `band_ranking_table.py`・確率の当たり具合 `band_logloss_table.py`・人気馬の4着以下 `favorite_out_table.py`・印の成績に渡す表 `danger_file_writer.py`・組の確率 `pair_probability.py`（混ぜる重み `race_weights_attacher.py`、表 `pair_calibration_table.py`）・抑えの買い目（印の成績の買い目 `mark_ticket_file.py`・組み方 `hedge_tickets.py`・精算 `hedge_settlement.py`・候補と選び方 `hedge_study.py`・表 `hedge_table.py`）・流れ `scenario_evaluation.py` |
| `analysis/danger_search/` | 消の決め方の探索。入力 `search_inputs.py`・消の元 `danger_sources.py`・払戻 `payout_table.py`・オッズ `odds_cache.py`・レースごとの消の組の印と買い目 `race_variant_cache.py`（印付けは複数のプロセス `race_variant_workers.py`）・組の期待値と枠連の候補 `combo_candidates.py`・成績 `ticket_metrics.py`・1つの決め方の評価 `danger_evaluator.py`・線の探索 `line_search.py`・表 `search_report.py` |
| `analysis/focus_day/` | 段3 の詳しく見る日。予測用データ `focus_day_data.py`・寄与 `contribution_lightgbm.py`・まとまり `material_groups.py`・理由の文 `reason_writer.py`・予想と順位 `focus_day_runner.py`・表 `focus_day_report.py`・流れ `focus_day_study.py` |
| `docs/` | 01 事例・02 理論・03 次の段の案・04 段3 の結果 |
| `tests/` | 合成DB と架空の値で部品を確かめるテスト（実DB は要らない） |
| `reports/超荒れの展開と適性から大穴を当てる/`（Git 対象外） | `事例.md`（全部の表）・`事例の一覧.csv`（1レースずつ見た 75レースの来た大穴と1番人気）・`コースの単位ごとの数.csv`（競馬場×コース×距離×馬場状態ごとの数）・`出走の表.pkl.gz`（列を足した出走の表）・`材料-<時点>.pkl`（段3 の足す材料）・`predictions/`（段3 の区切りごとの予測と、印の成績に渡す `danger-<時点>.pkl`）・`段3の結果-<時点>.md`・`段3の詳しく見る日-<日>.md` と `.csv`・`印の成績/`（今の消と新しい予想の消での印の成績） |

## 動かし方

リポジトリ直下（`keiba-yosou/`）から実行する。元DB は jvdata-store の `jvdata.duckdb`（読むだけ）。ほかに、回顧の DB（`reports/回顧/review.duckdb`。道具「回顧」が書く）と、予想「展開から着順を予想」の年ごとの予測（`reports/展開から着順を予想/out_of_sample/early/day_before/`）を読む。

```bash
uv run python research/超荒れの展開と適性から大穴を当てる/cases.py              # 段1・段2: 元DB から出走の表を作り、表と事例を書く（5分ほど）
uv run python research/超荒れの展開と適性から大穴を当てる/cases.py --cached     # 前に作った出走の表から書き直す（1分ほど）
uv run python research/超荒れの展開と適性から大穴を当てる/forecast.py features   # 段3: 足す材料の表（1分）
uv run python research/超荒れの展開と適性から大穴を当てる/forecast.py train      # 段3: 区切りごとに学び直す（3つの作り方 × 前日・当日。3時間ほど）
uv run python research/超荒れの展開と適性から大穴を当てる/forecast.py focus --date 2026-11-08   # 段3: 詳しく見る日（10分ほど）
uv run python research/超荒れの展開と適性から大穴を当てる/evaluate.py danger --timing 当日   # 段3: 印の成績に渡す表
uv run python research/超荒れの展開と適性から大穴を当てる/evaluate.py report --timing 当日 --marks <印の成績の買い目の csv>   # 段3: 確かめの表
uv run python research/超荒れの展開と適性から大穴を当てる/evaluate.py danger-current --timing 前日   # 段3: 今のモデルの 1 − 3着以内の確率を同じ形で
uv run python research/超荒れの展開と適性から大穴を当てる/danger_search.py --timing 当日 --db <元DB の写し>   # 段3: 消の決め方の探索（20分 ＋ 線1つにつき 1〜3分）
uv run python -m pytest research/超荒れの展開と適性から大穴を当てる -q          # 部品のテスト
```

開催日のレースの時間（発走前の通知が動いている間）には、元DB を使う入口（`cases.py`・`forecast.py features`・`forecast.py focus`・`evaluate.py report --marks`・`danger_search.py`）を動かさない（`--cached` と `train` は元DB を使わない）。
