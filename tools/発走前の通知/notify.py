"""発走前の通知: 発走の10分前に速報を取り込んで予想し、印・買い目・◎ の理由と近走を Discord に投稿する。

    uv run python tools/発走前の通知/notify.py                       # 今日。朝の準備（出馬表・速報の取り込み・全レースの予想）のあと、発走10分前ごとに通知
    uv run python tools/発走前の通知/notify.py --date 2026-11-08     # その日
    uv run python tools/発走前の通知/notify.py --rid 2026110105041101   # そのレースだけ今すぐ（取り込み → 予想 → 投稿）
    uv run python tools/発走前の通知/notify.py --test                # 短い文を投稿して、ウェブフックがつながるかを確かめる
    uv run python tools/発走前の通知/notify.py --dry-run             # Discord に投稿せず標準出力に出す
    uv run python tools/発走前の通知/notify.py --no-prepare          # 朝の準備を飛ばす（週末の予想を済ませてあるとき）
    uv run python tools/発走前の通知/notify.py --no-sync             # 出馬表の取り込み（jvstore sync）だけ飛ばす
    uv run python tools/発走前の通知/notify.py --minutes 10          # 発走の何分前に始めるか（既定は設定ファイルか 10）
    uv run python tools/発走前の通知/notify.py --local               # 地方競馬（nvdata-store の速報と地方の予想モデル。印と、当日の単勝・複勝の買い目）

ウェブフック URL は reports/発走前の通知/設定.json（{"webhook_url": "https://discord.com/api/webhooks/…"}）か、
環境変数 KEIBA_DISCORD_WEBHOOK に置く（Git には入れない）。
速報の取り込みは隣の jvdata-store（jvstore）、予想は tools/今週の予想/forecast.py を別プロセスで動かす。
地方（--local）は nvdata-store（nvstore）と地方の予想モデル（yosou.local_form_aptitude_top3 の predict）。朝の全レースの予想は無く、
馬体重が届く前のレースは前日の時点（オッズだけ）で予想する。
取り込みと予想に 1〜2分かかるので、通知は発走の 8〜9分前に届く。
ダブルクリックなら同じフォルダの run.bat。毎日 8:30 に自動で動かすなら register_task.bat（解除は unregister_task.bat）。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 発走前の通知.console_poster import ConsolePoster  # noqa: E402
from 発走前の通知.day_notifier import DayNotifier, Schedule  # noqa: E402
from 発走前の通知.discord_webhook import DiscordWebhook  # noqa: E402
from 発走前の通知.notifier_parts import NotifierParts  # noqa: E402
from 発走前の通知.notify_settings import NotifySettings  # noqa: E402

#: --test で投稿する文。
TEST_MESSAGE = "keiba-yosou 発走前の通知: つながりました。開催日は発走の10分前に予想を投稿します。"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", help="開催日 YYYY-MM-DD（既定: 今日）")
    parser.add_argument("--rid", help="このレースだけを今すぐ通知する（16桁の rid）")
    parser.add_argument("--test", action="store_true", help="短い文を投稿して、ウェブフックがつながるかを確かめる")
    parser.add_argument("--dry-run", action="store_true", help="Discord に投稿せず、標準出力に出す")
    parser.add_argument("--no-prepare", action="store_true", help="朝の準備（出馬表・速報の取り込み・全レースの予想）を飛ばす")
    parser.add_argument("--no-sync", action="store_true", help="出馬表の取り込み（jvstore sync）を飛ばす")
    parser.add_argument("--minutes", type=int, help="発走の何分前に取り込みと予想を始めるか（既定: 設定ファイルの値か 10）")
    parser.add_argument("--local", action="store_true", help="地方競馬で動かす（nvdata-store の速報と地方の予想モデル）")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = NotifySettings.load()
    poster = ConsolePoster() if args.dry_run else DiscordWebhook(settings.require_webhook())
    if args.test:
        poster.post(TEST_MESSAGE)
        print("投稿しました", file=sys.stderr)
        return 0
    day = args.date or (f"{args.rid[:4]}-{args.rid[4:6]}-{args.rid[6:8]}" if args.rid else date.today().isoformat())
    parts = NotifierParts.local() if args.local else NotifierParts.jra()
    notifier = DayNotifier(minutes_before=args.minutes or settings.minutes_before, schedule=parts.schedule, fetcher=parts.fetcher,
                           runner=parts.runner, message=parts.message, poster=poster, store=parts.store, sync=not args.no_sync)
    if args.rid:
        return _notify_one(notifier, parts.schedule, day, args.rid)
    return notifier.run(day, prepare=not args.no_prepare)


def _notify_one(notifier: DayNotifier, schedule: Schedule, day: str, rid: str) -> int:
    race = next((race for race in schedule.read(day) if race.rid == rid), None)
    if race is None:
        print(f"{rid} は {day} のレース一覧にありません（障害レースか、rid の間違い）", file=sys.stderr)
        return 1
    return 0 if notifier.notify(race) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
