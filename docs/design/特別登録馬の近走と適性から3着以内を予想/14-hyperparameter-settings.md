# 14 ハイパーパラメータを外から指定する

**この文書で決めること:** 木の数などのハイパーパラメータを、プログラムを書き換えずに外から指定する方法。

**結論: 中央の予想と同じ。ハイパーパラメータは設定ファイル（TOML 形式）に書き、学習を始めるときに `--config` で指定する。ファイルに書かなかった項目は、初期値の設定ファイルの値を使う。**

設定ファイルの形（`[lightgbm]`・`[lightgbm.params]`・`[catboost]`・`[catboost.params]`）、決まり（表に無い名前はエラー・目的関数は変えられない・使った設定をモデルと一緒に保存）、読むクラス（`HyperparameterSettings`・`SettingsFile`・`SettingsNameCheck`・`SettingsOverlay`）は、中央の予想の [14 ハイパーパラメータを外から指定する](../近走と適性から3着以内を予想/14-hyperparameter-settings.md) を参照。

## この予想で違う点

| 項目 | 内容 |
|---|---|
| 初期値の設定ファイルの置き場所 | `src/yosou/special_registration_top3/setting/default_settings.toml`。中身は中央の初期値と同じ値から始める（[12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md)）。検証データで比べて直した値は、このファイルに書く |
| 指定のしかた | `uv run python -m yosou.special_registration_top3 train --config 設定ファイルのパス` |
| 時点ごとの設定 | 時点が1つなので「3つの時点は同じ設定」の決まりは当たらない。3着以内のモデルと1着のモデルは同じ設定で学ぶ（中央と同じ） |
| 7つの区切りでの確かめ | `backtest` は初期値のまま学ぶ（設定ファイルは受け取らない。中央の 16 の 4. と同じ） |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-10-13 |
