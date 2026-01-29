from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

from . import f1_api
from .discord_webhook import send_webhook
from .render import render_weekend_card
from .state import load_state, save_state


WEBHOOK = os.getenv("DISCORD_F1_WEEKEND_WEBHOOK_URL")


def _utc_dt(date_str: str, time_str: str) -> datetime:
    # Ergast provides date YYYY-MM-DD and time HH:MM:SSZ
    t = (time_str or "00:00:00Z").replace("Z", "+00:00")
    return datetime.fromisoformat(f"{date_str}T{t}")


def _within_window(now: datetime, race_dt: datetime) -> bool:
    # consider weekend window: Thu..Mon around race
    return (race_dt - timedelta(days=3)) <= now <= (race_dt + timedelta(days=1))


def post_weekend_update(mode: str) -> None:
    st = load_state()

    race = f1_api.get_next_race()
    season = race.get("season")
    round_ = race.get("round")
    race_name = race.get("raceName")
    circuit = ((race.get("Circuit") or {}).get("circuitName"))

    race_dt = _utc_dt(race.get("date"), race.get("time"))
    now = datetime.now(timezone.utc)

    # Only post during weekend window unless forced
    force = os.getenv("F1_WEEKEND_FORCE", "false").lower() == "true"
    if not force and not _within_window(now, race_dt):
        print("Not in race weekend window; skipping.")
        return

    key = f"{mode}:{season}:{round_}"
    if key in st.posted and os.getenv("F1_WEEKEND_ALLOW_DUPES", "false").lower() != "true":
        print(f"Already posted {key}; skipping")
        return

    lines: list[str] = []
    content = ""
    img: bytes | None = None

    if mode == "schedule":
        lines.append(f"Race: {race_name}")
        if circuit:
            lines.append(f"Circuit: {circuit}")
        lines.append(f"Race (UTC): {race_dt.strftime('%a %d %b %H:%M')}")
        if race.get("Qualifying"):
            q = race["Qualifying"]
            qdt = _utc_dt(q.get("date"), q.get("time"))
            lines.append(f"Qualifying (UTC): {qdt.strftime('%a %d %b %H:%M')}")
        if race.get("Sprint"):
            s = race["Sprint"]
            sdt = _utc_dt(s.get("date"), s.get("time"))
            lines.append(f"Sprint (UTC): {sdt.strftime('%a %d %b %H:%M')}")

        content = f"**F1 Weekend — {race_name}**\nSchedule in UTC (ask @Venbot if you want it in your timezone)."
        img = render_weekend_card(
            title=f"F1 Weekend: {race_name}",
            lines=lines,
            footer=f"Source: Ergast-compatible API · generated {now.strftime('%Y-%m-%d %H:%M UTC')}",
        )

    elif mode == "standings":
        ds = f1_api.get_driver_standings("current")[:10]
        cs = f1_api.get_constructor_standings("current")[:10]
        lines.append("Top 10 Drivers:")
        for d in ds:
            drv = d.get("Driver") or {}
            name = f"{drv.get('givenName','')} {drv.get('familyName','')}".strip()
            lines.append(f"{d.get('position')}. {name} — {d.get('points')} pts")
        lines.append("")
        lines.append("Top 10 Constructors:")
        for c in cs:
            con = c.get("Constructor") or {}
            lines.append(f"{c.get('position')}. {con.get('name')} — {c.get('points')} pts")

        content = "**F1 Standings (current)**"
        img = render_weekend_card(
            title="F1 Standings",
            lines=lines,
            footer=f"Source: Ergast-compatible API · generated {now.strftime('%Y-%m-%d %H:%M UTC')}",
        )

    elif mode == "results":
        results = f1_api.get_race_results(season, round_)
        if not results:
            print("No results available yet; skipping")
            return
        lines.append(f"Results: {race_name}")
        for r in results[:10]:
            drv = r.get("Driver") or {}
            name = f"{drv.get('givenName','')} {drv.get('familyName','')}".strip()
            cons = (r.get("Constructor") or {}).get("name")
            lines.append(f"{r.get('position')}. {name} ({cons})")

        content = f"**Race result — {race_name}**"
        img = render_weekend_card(
            title=f"Race result: {race_name}",
            lines=lines,
            footer=f"Source: Ergast-compatible API · generated {now.strftime('%Y-%m-%d %H:%M UTC')}",
        )

    else:
        raise ValueError("mode must be schedule|results|standings")

    send_webhook(WEBHOOK, content=content, file_bytes=img, filename=f"{mode}.png")
    st.posted.add(key)
    save_state(st)


if __name__ == "__main__":
    mode = os.getenv("F1_WEEKEND_MODE", "schedule")
    post_weekend_update(mode)
