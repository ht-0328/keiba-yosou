# 近走の文の評価のことば

近走の文（`tools/近走の文/`）に添える評価のことば（「負けて強し」「上向き」「人気薄で好走の実績」「大敗続き」）と、
苦手の傾向の線（重い馬場・芝ダ・距離の対比を出す走の数と3着以内率の差）を、過去の走で確かめる研究。

- ことばは「その走までの材料」だけで付け（後の走は使わない）、ことばが付いた馬の次の走の3着以内率を、同じ人気の馬がふつう出す率と比べる（人気から見た差。`tools/共通/popularity_expectation.py`）。
- 採る線は、ことばの向き（良いことばなら差が正、悪いことばなら負）に、差が標準誤差の 2倍以上あること。届かないことばは予想の出力に付けない。
- 数値（JV-Data 由来の成績・回収率）は Git 対象外の `reports/近走の文の評価のことば/` に出す。この README と `docs/` には数値を書かない。
- 決めたことは [docs/01-結果の読み方.md](docs/01-結果の読み方.md)。

## フォルダ構成

| 場所 | 中身 |
|---|---|
| `verify_words.py` | 入口: 元DB と回顧の表から全走を読み、候補のことばと苦手の傾向を付けて、次走の成績を `reports/近走の文の評価のことば/評価のことばの確かめ.md` に書く |
| `analysis/run_frame_repository.py` | 元DB の事実表（出走した走）と回顧の表3（不利）を読む（`RunFrameRepository`。1 SQL + 回顧の1読み） |
| `analysis/word_labels.py` | 候補のことばを、各走の「その走までの材料」から付ける（`WordLabels`。線の定数は `tools/近走の文/evaluation_words.py` と同じ） |
| `analysis/tendency_labels.py` | 苦手の傾向（重い馬場・芝ダ・距離の対比）を、線の候補ごとに各走の「その走までの成績」から付ける（`TendencyLabels`） |
| `analysis/label_tally.py` | ことばごとに、付いた走の3着以内率・人気から見た差・標準誤差・単勝と複勝の回収率を数える（`LabelTally`） |
| `analysis/report_writer.py` | 結果の表を Markdown にする（`ReportWriter`） |
| `docs/` | 結果の読み方と決めたこと（`01-結果の読み方.md`） |
| `tests/` | 部品のテスト（架空の値だけ） |

## 動かし方

作業フォルダの直下で実行する。

```powershell
uv run python research/近走の文の評価のことば/verify_words.py        # 全走で確かめて reports/ に書く（1〜2分）
uv run python -m pytest -q research/近走の文の評価のことば             # テスト
```
