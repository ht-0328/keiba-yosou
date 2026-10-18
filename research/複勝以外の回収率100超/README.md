# 複勝以外の回収率100超

**何をする研究か。** 複勝以外の券種（単勝・ワイド・馬連・馬単・3連複・3連単）で、回収率が 100% を超える買い方を探す。

**なぜ始めたか。** 研究「回収率100超」では、複勝だけが 100% を超えた。同じモデルで、組み合わせの券種の確率を「1着の確率から Harville の式で作る」形にして確かめたところ、どの券種も届かなかった（[../回収率100超/docs/05-券種ごとの検証.md](../回収率100超/docs/05-券種ごとの検証.md)）。
その原因として、組ごとの市場の情報を捨てていることが考えられた。そこで、**組の確率を、市場の組の値段（オッズ）から直接作る**形で確かめ直す。

**やり方の中心。** 複勝で効いた考え方「売上の大きい券種から確率を取り出し、売上の小さい券種の値段と比べて、割安なものを買う」を、組み合わせの券種に広げる。
例: 3連単のオッズから「1番と5番がどちらも3着以内に入る確率」を作り、ワイド 1-5 のオッズと比べる。

## この文書で使う言葉の意味

この研究に出てくる言葉のうち、分かりにくいものの意味をまとめた。

| 用語 | 意味 | この研究では（架空の例） |
|---|---|---|
| 市場の組の確率 | ある券種のオッズの逆数を、レースで合計 1 にそろえた値（ワイドは当たりの組が3つなので合計 3） | 馬連 1-5 が 20倍なら、そろえる前の値は 0.05 |
| 3連単から見た組の確率 | 3連単の市場の組の確率を足し合わせて作った、ほかの券種の組の確率 | ワイド 1-5 = 1番と5番が1〜3着に入っている3連単の組の合計 |
| 比 | 3連単から見た組の確率 ÷ その券種自身から見た組の確率。1 より大きい組は、その券種で割安に売られている | 0.030 ÷ 0.025 = 1.2 |
| 3連単を直す | 3連単の組の確率に、3連単のオッズの帯ごとの実績の倍率を掛けて、人気薄の組の買われすぎを直すこと | 3,000倍以上の組を 0.6倍にする |
| 上げ下げ | 研究「回収率100超」のモデルが見た「この馬は市場より3着以内に来る」の比を、組の各馬ぶん掛けること | 1番の比 1.2・5番の比 1.5 なら 1.8倍 |
| 上げ下げの強さ | 比を何乗して掛けるか。0 なら掛けない、1 ならそのまま | 0・0.5・1 |
| 作り方 | 組の確率の出どころ × 3連単を直すか × 上げ下げの強さ の組み合わせ | 「3連単から（3連単を直す）・上げ下げ 0.5」 |

## フォルダの中身

| 場所 | 何があるか |
|---|---|
| `docs/` | 進め方と、分かったこと |
| `cases.py` | 入口①。前半の年で、券種どうしの値段の食い違いが大きかったレースを集める |
| `backtest.py` | 入口②。すべての作り方で、線を前半で決めて後半で確かめる |
| `early_years.py` | 入口③。印のルールの買い目を、まだ見ていない 2021〜2022年で確かめるために、今の本番のモデルをその年の区切りで学習し、今の本番の予測と合わせる（docs/03）。`--from-year 2019` で手順5 の 2019〜2020年の区切りを、`tables` と `--from-year 2015` で手順6 の 2015〜2018年の区切り（2012年からの表で学ぶ）を作る（docs/04・05） |
| `combo_value.py` | 入口④。組の期待値（市場とモデルを重みで合わせた組の確率 × オッズ）で組を選ぶ買い方の、印付け・重みの推定・線の選び方・期間ごとの成績（docs/04）と、区切りごとの重み（直前1年・検証期間。docs/05） |
| `analysis/` | 市場の組の確率を作る部品（`market_combo_table.py`・`pool_derivation.py`・`horse_uplift.py`・`market_source.py`・`trifecta_corrections.py`・`variant.py`・`gap_cases.py`）と、入口③の区切りと学び直すモデル（`early_windows.py`・`retrain_target.py`・`retrain_targets.py`）と、入口④の部品（`backtest_marking.py`・`combo_month_frames.py`・`combo_rule_grid.py`・`combo_period_report.py`・`combo_operation_report.py`。組の確率そのものは本番と同じ `src/yosou/shared/combo_value/`） |
| `prompts/` | 事例の見方 |
| `tests/` | 架空の値で部品を確かめるテスト |
| `reports/複勝以外の回収率100超/`（Git 対象外） | 実測の数値。JV-Data 由来の値はここにだけ置く |

研究「回収率100超」の部品（点数付け・オッズの帯ごとの較正・線の決め方・中間データ・保存した予測）をそのまま使う。

## 読む順

1. [docs/01-進め方.md](docs/01-進め方.md) — 何をどの順で確かめるか
2. [docs/02-結果.md](docs/02-結果.md) — 事例から分かったことと、検証の結果
3. [docs/03-印の買い目の確かめ.md](docs/03-印の買い目の確かめ.md) — 印のルールの買い目を、まだ見ていない年で確かめる手順と採用の基準（手順4）
4. [docs/04-組の期待値で選ぶ買い方.md](docs/04-組の期待値で選ぶ買い方.md) — 組ごとの期待値で組を選ぶ買い方と、2019〜2020年で確かめる手順・基準・結果（手順5）
5. [docs/05-直前1年の重みと2015年から.md](docs/05-直前1年の重みと2015年から.md) — 重みを区切りごとに直前1年で推定し直し、2016〜2018年で確かめる手順・基準・結果（手順6）

## 動かし方

リポジトリ直下（`keiba-yosou/`）から実行する。先に研究「回収率100超」の `extract.py`・`extract_tickets.py`・`backtest_tickets.py` を回しておく。

```bash
uv run python research/複勝以外の回収率100超/cases.py      # 事例を集める（数分）
uv run python research/複勝以外の回収率100超/backtest.py   # すべての作り方を確かめる
uv run python research/複勝以外の回収率100超/early_years.py run       # 手順4: 今の本番のモデルを 2021〜2022年の区切りで学習する（1時間ほど）
uv run python research/複勝以外の回収率100超/early_years.py combine   # 手順4: 今の本番の予測と合わせる（そのあと道具「印の成績」で数える。docs/03）
uv run python research/複勝以外の回収率100超/early_years.py run --from-year 2019      # 手順5: 2019〜2020年の区切りで学習する（1時間ほど）
uv run python research/複勝以外の回収率100超/early_years.py combine --from-year 2019  # 手順5: 2021年からの予測と合わせる
uv run python research/複勝以外の回収率100超/combo_value.py mark                      # 手順5: 2019年からの当日の予測に印を付ける
uv run python research/複勝以外の回収率100超/combo_value.py fit                       # 手順5: 2023〜2026年で組の確率の重みを推定する
uv run python research/複勝以外の回収率100超/combo_value.py grid                      # 手順5: 2023〜2026年で線・上限・対象を数える
uv run python research/複勝以外の回収率100超/combo_value.py check                     # 手順5: 道具「印の成績」の買い目から期間ごとの成績を出す（docs/04）
uv run python research/複勝以外の回収率100超/early_years.py tables                     # 手順6: 2012年からの表を用意する
uv run python research/複勝以外の回収率100超/early_years.py run --from-year 2015 --tables reports/複勝以外の回収率100超/tables-2012 --only 当日・3着以内 当日・1着 危険な人気馬
uv run python research/複勝以外の回収率100超/early_years.py combine --from-year 2015 --only 当日・3着以内 当日・1着 危険な人気馬
uv run python research/複勝以外の回収率100超/combo_value.py mark --from-year 2015      # 手順6: 2015年からの当日の予測に印を付ける
uv run python research/複勝以外の回収率100超/combo_value.py rolling --from-year 2015   # 手順6: 区切りごとに直前1年で重みを推定する
uv run python research/複勝以外の回収率100超/combo_value.py rolling --latest-only --save-models   # 本番の重み（ワイド・3連複・3連単）
uv run python -m pytest -q research/複勝以外の回収率100超                                  # 部品のテスト（架空の値だけ）
```
