# 馬券の買い方の検証

**何をするか。** 4つの予想モデル（近走と適性から3着以内・人気馬が4着以下・穴馬が3着以内・レースの荒れ具合）の出力と、
ルール集（`docs/rules/馬券の買い方/`）の買い方を組み合わせ、レースの参加パターン（全レース・荒れるレースだけ・自信のあるレースだけ・
両方・毎週上位・毎週 + 重賞）をいろいろ変えて、回収率が 100% を超える買い方があるかを過去レースで確かめる（ルール集の課題3）。

**決めごと。** 探索は検証期間（2025年7〜12月）だけで行い、良かった戦略を数個に絞ってテスト期間（2026年1〜9月）で1回だけ確かめる。
採否の基準としきい値の格子は、探索の前に [docs/03-protocol.md](docs/03-protocol.md) に固定した。

**状態。** 2回目の検証まで終わった（2026-09-23）。どちらの回も、確認期間で 100% を超える戦略は無かった。結論と次にやることは [docs/04-results.md](docs/04-results.md)。

## フォルダ

| 場所 | 中身 |
|---|---|
| `predict_all.py` | 入口①: 4モデルの当日時点の予測を期間ぶん一括で出し、`reports/馬券の買い方の検証/predictions/` に CSV で残す |
| `backtest.py` | 入口②: 予測・確定オッズ・払戻から精算表を作り（`--settle-only`）、探索（既定）と確認（`--confirm`）をする |
| `analysis/` | 部品。フォルダごとの仕事は `analysis/__init__.py` の表、クラスごとの仕事は各フォルダの `__init__.py` |
| `docs/` | [01 設計](docs/01-design.md)・[02 買い方の一覧](docs/02-ticket-plans.md)・[03 事前に固定した決まり](docs/03-protocol.md)・[04 結果](docs/04-results.md) |
| `tests/` | 合成データだけのテスト（`uv run python -m pytest -q research`） |

出力（JV-Data 由来の数値）はすべて `reports/馬券の買い方の検証/`（Git 対象外）に置く。この README と `docs/` には数値を書かない。

## 実行（リポジトリ直下で）

```powershell
# 1. 4モデルの予測を一括で出す（約15分。元DB を1モデルずつ開く）
uv run python research/馬券の買い方の検証/predict_all.py

# 2. 読めたデータの数を確かめる（任意）
uv run python research/馬券の買い方の検証/backtest.py --check-data

# 3. 精算表（買い方 × レース）を作る（約10分）
uv run python research/馬券の買い方の検証/backtest.py --settle-only --out reports/馬券の買い方の検証/settle-summary.md

# 4. 探索（検証期間）。全戦略の結果と、選んだ戦略（chosen.json）を書く
uv run python research/馬券の買い方の検証/backtest.py --out reports/馬券の買い方の検証/search/2025H2.md

# 5. 確認（テスト期間。1回だけ）
uv run python research/馬券の買い方の検証/backtest.py --confirm reports/馬券の買い方の検証/search/chosen.json --out reports/馬券の買い方の検証/confirm/2026.md
```

どの入口も `--help` で引数の全部が見られる。`--db` で元DB の場所を変えられる（既定は `../jvdata-store/jvdata.duckdb`）。

## 結果の置き場

| ファイル | 中身 |
|---|---|
| `reports/馬券の買い方の検証/predictions/` | 4モデルの予測（CSV）と記録（manifest.json） |
| `reports/馬券の買い方の検証/settlement.csv` | 精算表 |
| `reports/馬券の買い方の検証/search/` | 探索の結果（表・全戦略の CSV・chosen.json） |
| `reports/馬券の買い方の検証/confirm/` | 確認の結果 |
