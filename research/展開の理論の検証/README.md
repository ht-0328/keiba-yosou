# 展開の理論の検証

「スローなら逃げ・先行が有利、ハイなら差し・追込が有利」「逃げたい馬が複数いるとハイになりやすい」という展開の理論が、
過去のレースで本当に成り立つかを、事例を1レースずつ見るところから確かめる研究。進め方は [docs/01-進め方.md](docs/01-進め方.md)、分かったことと決めたことは [docs/02-結果の読み方.md](docs/02-結果の読み方.md)。

- 結果は、あとで作る「馬の能力指数」で、過去の走のタイムからペースで得をした分・損をした分を差し引くのに使う。
- 数値（JV-Data 由来の成績・回収率・馬名）は Git 対象外の `reports/展開の理論の検証/` に出す。この README と `docs/` には数値を書かない。
- 言葉の意味は [docs/01-進め方.md の「この文書で使う言葉の意味」](docs/01-進め方.md#この文書で使う言葉の意味) にある。

## フォルダ構成

| 場所 | 中身 |
|---|---|
| `extract.py` | 入口①: 元DB から出走の表（1行 = 1頭）とレースの表（1行 = 1レース、ペースの区分つき）を作って、`reports/展開の理論の検証/cache/` に保存する |
| `collect_cases.py` | 入口②: 事例の型ごとのレース数と、型ごとに無作為に選んだレースの一覧を `reports/展開の理論の検証/cases/一覧.md` に書く |
| `tally.py` | 入口③: ペースの測り方・脚質の分け方・逃げたい馬の数え方を比べ、成績を数えて `reports/展開の理論の検証/集計/` に書く |
| `analysis/repository/` | 元DB（事実表）から読む部品。1クラス = 1 SQL |
| `analysis/pace/` | 1行 = 1レースの表を作る（`RaceTable`）・ペースを決める（`RacePaceClassifier`）・馬場状態つきの基準（`ConditionPaceMeasure`）・3通りの測り方を並べる（`PaceMeasureTable`）・z を区分に直す（`PaceBands`） |
| `analysis/leaders/` | 各馬の今回より前の先頭率など（`EarlyRunHistory`）・レースごとに逃げたい馬を数える（`LeaderCountTable`） |
| `analysis/tally/` | 脚質の分け方（`StyleVariant`・`StyleColumns`）・オッズから見た勝率（`MarketWinProbability`）・成績（`PerformanceTally`）・展開の効き目（`PaceEffectScore`）・数え方の当たり具合（`LeaderPaceScore`） |
| `analysis/cases/` | 事例の型（`CasePattern` と `PATTERNS`）と、型ごとにレースを選ぶ（`CasePicker`） |
| `analysis/cache_store.py` | 中間データの parquet を DuckDB で読み書きする |
| `prompts/` | サブエージェントへの指示文（`事例の分析.md`: 1つの型の事例を1レースずつ読む） |
| `docs/` | 進め方（`01-進め方.md`）と、結果の読み方・決めたこと（`02-結果の読み方.md`） |
| `tests/` | 部品のテスト（架空の値だけ） |

## 動かし方

作業フォルダの直下で実行する。

```powershell
uv run python research/展開の理論の検証/extract.py          # 元DB を読んで中間データを作る（1分ほど。DB をそのあいだ握る）
uv run python research/展開の理論の検証/collect_cases.py    # 型ごとのレース数と事例の一覧を書く（--count 20 --from 2023-01-01 --seed 0 が既定）
uv run python tools/レース詳細/race.py <rid>                 # 一覧の rid の、ラップ・通過順・結果を見る
uv run python research/展開の理論の検証/tally.py            # 比べと内訳を数える（1分ほど。--measure と --style で内訳の組み合わせを選ぶ）
uv run python -m pytest -q research/展開の理論の検証         # テスト
```
