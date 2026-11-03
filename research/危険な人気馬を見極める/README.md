# 危険な人気馬を見極める

**何をする研究か。** 今週の予想の「消」（危険な人気馬）が、本当に来ない人気馬を選べるようにする。
消を決めている予想「人気馬が4着以下になるかを予想」の、危険度の比べる相手と学習の出発点を、「オッズだけのモデル」に替えて確かめる。

**なぜ始めたか。** 利用者から「人気馬をほとんど順番に並べただけにしか見えない。ちゃんと危険な人気馬を見極めてほしい」
「人気馬を消して馬券を当てて回収率を上げられるならなんでもいい」と言われた（2026-11-01）。
消を付けた人気馬が、同じ人気の馬全体とほとんど同じくらい3着以内に来ていた。
そのあと「もともと全レースを買って回収率 100% 超えを目指すのが目的」「6番人気以下はそもそも基本来ないのだから、来そうな馬を見つける考え方で」「6番人気以下で複勝回収率を 100% 超えるモデルを作って」と言われ、全頭の予想と、6番人気以下の複勝の選び方も確かめた。

**進め方と採否の基準**は [docs/01-仮定と進め方.md](docs/01-仮定と進め方.md)、**結果**は [docs/02-結果.md](docs/02-結果.md)。
数値（JV-Data 由来の成績・回収率）は Git 対象外の `reports/危険な人気馬を見極める/` に出し、この README と docs には書かない。

## この文書で使う言葉の意味

| 言葉 | 意味 | この研究では（架空の例） |
|---|---|---|
| 危険度 | 人気馬の予想の4着以下の確率 − 比べる相手の確率。同じオッズの馬より、どれだけ負けやすいか | 予想 0.45・比べる相手 0.35 なら 0.10 |
| オッズから計算した確率 | 単勝オッズから Harville の式で出した3着以内率を裏返した、4着以下の確率。今の本番の比べる相手 | 1番人気の 3着以内率 0.74 → 4着以下 0.26 |
| オッズだけのモデル | オッズの列（人気順位・単勝オッズ・オッズから見た勝率と3着以内率・頭数）だけで、4着以下の確率を学んだモデル。結果に合わせ直したオッズから見た確率 | 同じ1番人気の 4着以下を 0.34 と見る |
| 出発点（基準） | モデルが学ぶときの初めの値。モデルは、ここからの上げ下げだけを学ぶ | |
| 危険度の上位 x% | 人気帯ごとに、テスト期間の危険度の高い順に x% の人気馬 | 1番人気 1万頭の上位 5% は 500頭 |
| 同じ人気の馬全体 | 取り出した馬と同じ人気の馬全体の成績を、人気の内訳で重み付けした平均 | |
| 区切り | 過去で学習して次の半年を予想する検証の1回分（研究「既存モデルの改善」と同じ7つ） | 2025年後半 |

## フォルダの中身

| 場所 | 何があるか |
|---|---|
| `danger.py` | 入口。7つの区切りで学ぶ（`run`）・危険度の上位の成績（`top`）・線を厳しくした消の表（`flags`）・印の成績を並べる（`marks`）・全頭の予想もオッズだけのモデルを出発点に学ぶ（`form`）・穴馬の予想（`longshots`・`place`）・まだ見ていない期間の確かめ（`unseen`）・荒れ具合の予想をまだ見ていない期間で学び直す（`upset`） |
| `analysis/calibrated_window_trainer.py` | 1つの区切りで、オッズだけのモデルを先に学び、それを出発点にして人気馬の予想を学ぶ |
| `analysis/danger_top_report.py` | 危険度の上位の人気馬の成績を、同じ人気の馬全体と比べる表 |
| `analysis/mark_comparison.py` | 道具「印の成績」の結果を作り方ごとに読み、買い方ごとの回収率と的中率と、消の成績を並べる表 |
| `analysis/strict_danger_flags.py` | 線を「検証期間の危険度の上位 x%」にして、テスト期間の消（1レース1頭）を決める |
| `analysis/odds_only_baseline.py` | オッズの列だけで学んだモデルの確率を、学習の出発点（基準）にする |
| `analysis/market_based_window_trainer.py` | 1つの区切りで、全頭の予想（3着以内・1着）も、オッズだけのモデルを出発点にして学ぶ |
| `analysis/longshot_top_report.py` | 来そうと見た穴馬（穴馬度の上位）の成績を、同じ人気の馬全体と比べる表 |
| `analysis/place_market_window_trainer.py` | 1つの区切りで、穴馬の予想を複勝オッズから見た3着以内率を出発点にして学ぶ |
| `analysis/place_bet_report.py` | 6番人気以下の複勝を「予想 − 複勝オッズから見た3着以内率」が線以上の馬だけ買ったときの成績の表 |
| `docs/` | 仮定と進め方（01）、結果（02） |
| `tests/` | 架空の値で部品を確かめるテスト |
| `reports/危険な人気馬を見極める/`（Git 対象外） | 予測（`predictions/`）・危険度の上位（`危険度の上位.md`）・印の成績（`印の成績/`）・その比べ（`印の成績の比べ.md`） |

オッズだけのモデル（`OddsOnlyBaseline`）は `analysis/odds_only_baseline.py`。本番には入れていない（結果は docs/02）。
区切り・学習データの表・予測の保存は、研究「既存モデルの改善」の部品をそのまま使う。

## 動かし方

リポジトリ直下（`keiba-yosou/`）から実行する。先に研究「既存モデルの改善」の `build_tables.py` で、人気馬の予想の学習データの表（`favorites_out_of_top3`）を作っておく。

```bash
uv run python research/危険な人気馬を見極める/danger.py run   # 1. 2段の学び方を7つの区切りで学ぶ（30分ほど）
uv run python research/危険な人気馬を見極める/danger.py top   # 2. 危険度の上位の人気馬の成績を、今の本番と比べる（数秒）
# 3. 印と全券種の買い目の成績（1つ 1時間ほど。DB を使うので1つずつ）
uv run python tools/印の成績/mark_stats.py --out-dir reports/危険な人気馬を見極める/印の成績/本番
uv run python tools/印の成績/mark_stats.py --no-danger --out-dir reports/危険な人気馬を見極める/印の成績/消なし
uv run python tools/印の成績/mark_stats.py --danger reports/危険な人気馬を見極める/predictions/favorites_out_of_top3/calibrated.pkl --out-dir reports/危険な人気馬を見極める/印の成績/新しい危険度
uv run python research/危険な人気馬を見極める/danger.py flags   # 3'. 線を検証期間の上位 5%・10% にした消の表（数秒）。このあと 3 と同じく --danger-flags で印の成績を出す
uv run python tools/印の成績/mark_stats.py --danger-flags "reports/危険な人気馬を見極める/predictions/消の表/新しい危険度・上位5%.pkl" --out-dir "reports/危険な人気馬を見極める/印の成績/新しい危険度・上位5%"
uv run python research/危険な人気馬を見極める/danger.py marks   # 4. 印の成績を並べる（数秒）
uv run python research/危険な人気馬を見極める/danger.py form    # 5. 全頭の予想（前日の3着以内と1着）も、オッズだけのモデルを出発点にして学ぶ（1〜2時間）
uv run python tools/印の成績/mark_stats.py --form reports/危険な人気馬を見極める/predictions/h2h_ability/h2h-day_before.pkl --win reports/危険な人気馬を見極める/predictions/h2h_ability/win-day_before.pkl --danger-flags "reports/危険な人気馬を見極める/predictions/消の表/新しい危険度・上位5%.pkl" --out-dir "reports/危険な人気馬を見極める/印の成績/全頭も新しい出発点"
uv run python research/既存モデルの改善/build_tables.py --only longshots_in_top3 --tables reports/危険な人気馬を見極める/tables   # 6. 穴馬の予想の表を今の材料で作る（DB を使う。数分）
uv run python research/危険な人気馬を見極める/danger.py longshots   # 6'. 穴馬の予想もオッズだけのモデルを出発点に学び、穴馬度の上位の成績を出す（30分ほど）
uv run python research/危険な人気馬を見極める/danger.py place       # 7. 穴馬の予想を複勝オッズを出発点に学び、6番人気以下の複勝の成績を全頭の予想と比べる（30分ほど）
uv run python research/危険な人気馬を見極める/danger.py unseen      # 8. 6番人気以下の複勝の選び方を、まだ見ていない 2021年前半〜2022年前半で確かめる（30分ほど）
# 9. 6番人気以下の複勝を本番に入れたあとの印の成績を、今の消と新しい消で出し、4 で並べる（1つ 1時間ほど）
uv run python tools/印の成績/mark_stats.py --out-dir reports/危険な人気馬を見極める/印の成績/穴馬の複勝を足した本番
uv run python tools/印の成績/mark_stats.py --danger reports/危険な人気馬を見極める/predictions/favorites_out_of_top3/calibrated.pkl --out-dir "reports/危険な人気馬を見極める/印の成績/新しい危険度＋穴馬の複勝"
uv run python tools/印の成績/mark_stats.py --danger-flags "reports/危険な人気馬を見極める/predictions/消の表/新しい危険度・上位5%.pkl" --out-dir "reports/危険な人気馬を見極める/印の成績/新しい危険度・上位5%＋穴馬の複勝"
# 10. 3連複を、3連複の荒れ具合（超荒れと固いは確率の線で決める）ごとの形（固い 買わない・中荒れ 穴−強−9番人気まで・
#     大荒れ 穴−9番人気まで−9番人気まで・超荒れ 穴−強−消を除いた全頭。比べる行も）で数える（1つ 1時間ほど）
uv run python tools/印の成績/mark_stats.py --out-dir "reports/危険な人気馬を見極める/印の成績/荒れ具合ごとの3連複"
uv run python research/危険な人気馬を見極める/danger.py upset   # 10'. 荒れ具合の予想を、まだ見ていない 2021〜2022年の区切りで学び直す（1時間ほど）
uv run python tools/印の成績/mark_stats.py --form reports/危険な人気馬を見極める/predictions/h2h_ability/h2h-day_before-unseen.pkl --no-win --no-danger --upset reports/危険な人気馬を見極める/predictions/upset_level/unseen.pkl --out-dir "reports/危険な人気馬を見極める/印の成績/荒れ具合ごとの3連複・まだ見ていない期間"
uv run python -m pytest -q research/危険な人気馬を見極める   # 部品のテスト（架空の値だけ）
```
