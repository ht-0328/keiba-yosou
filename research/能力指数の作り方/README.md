# 能力指数の作り方

出走馬ごとの「能力指数」（過去の走破タイムから作った、馬の基礎能力の数字）の作り方を、候補を実際に数えて比べて決める研究。
決まった作り方は、道具「能力指数」（`tools/能力指数/ability.py` と検索画面の「能力指数」タブ）が使う。計算の部品は `tools/共通/ability/`。

- 進め方と言葉の意味は [docs/01-進め方.md](docs/01-進め方.md)、比べたことと決めたことは [docs/02-結果の読み方.md](docs/02-結果の読み方.md)。
- 着順・人気・オッズは、指数の材料にも、良し悪しの物差しにも使わない。物差しはタイムから作ったスピード指数だけ。
- ペースの測り方と、脚質ごとの展開の得・損の向きは、研究「展開の理論の検証」（`research/展開の理論の検証/`）の結果を使う。
- 数値（JV-Data 由来の指数・相関）は Git 対象外の `reports/能力指数の作り方/` に出す。この README と `docs/` には数値を書かない。

## フォルダ構成

| 場所 | 中身 |
|---|---|
| `extract.py` | 入口①: 元DB から 2011年からの中央・平地の全出走を読み、`reports/能力指数の作り方/cache/runs.parquet` に保存する |
| `compare.py` | 入口②: スピード指数の補正・能力指数のまとめ方・血統で補う候補を比べ、既定の設定を選ぶのに使っていない期間で確かめ、年ごとの当たり具合を分けて、`reports/能力指数の作り方/比べ/` に書く |
| `analysis/figure_consistency.py` | 物差し①: 同じ馬の続けて走ったレースどうしの、スピード指数の相関（`FigureConsistency`） |
| `analysis/index_accuracy.py` | 物差し②: 能力指数と、その走のスピード指数の相関・ずれ・ばらつき（`IndexAccuracy`） |
| `analysis/accuracy_breakdown.py` | 年ごとの相関を、外れ方（ばらつき）と指数の広がり（クラスの間・クラスの中）に分ける（`AccuracyBreakdown`） |
| `analysis/era_race_table.py` | レースの水準を、降級制度の廃止（2019年6月）の前と後で別にするレースの表（`EraRaceTable`）。基準タイムの作り方が年ごとの当たり具合を下げていないかを確かめるのに使う |
| `docs/` | 進め方（`01-進め方.md`）と、結果の読み方・決めたこと（`02-結果の読み方.md`） |
| `tests/` | 物差しと、年ごとの分け方のテスト（架空の値だけ） |

## 動かし方

作業フォルダの直下で実行する。

```powershell
uv run python research/能力指数の作り方/extract.py    # 元DB を読んで中間データを作る（1分ほど。DB をそのあいだ握る。父・母の父の列も読む）
uv run python research/能力指数の作り方/compare.py    # 候補を比べて reports/能力指数の作り方/比べ/ に書く（15分ほど）
uv run python -m pytest -q research/能力指数の作り方 tools/共通/tests/test_ability.py   # テスト
```
