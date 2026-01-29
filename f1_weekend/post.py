from __future__ import annotations

import os
import random
from datetime import datetime, timezone, timedelta

from . import f1_api
from .discord_webhook import send_webhook
from .render import render_weekend_card
from .state import load_state, save_state
from .weather import get_hourly_forecast


WEBHOOK = os.getenv("DISCORD_F1_WEEKEND_WEBHOOK_URL")


def _utc_dt(date_str: str, time_str: str | None) -> datetime:
    t = (time_str or "00:00:00Z").replace("Z", "+00:00")
    return datetime.fromisoformat(f"{date_str}T{t}")


def _within_window(now: datetime, race_dt: datetime) -> bool:
    # Weekend window: Thu..Mon around race (UTC)
    return (race_dt - timedelta(days=3)) <= now <= (race_dt + timedelta(days=1))


def _driver_name(drv: dict) -> str:
    return f"{drv.get('givenName','')} {drv.get('familyName','')}".strip()


def _post_once(st, key: str, fn):
    if key in st.posted and os.getenv("F1_WEEKEND_ALLOW_DUPES", "false").lower() != "true":
        print(f"Already posted {key}; skipping")
        return
    fn()
    st.posted.add(key)
    save_state(st)


def _next_session_card(race: dict, now: datetime) -> tuple[str, list[str]] | None:
    sessions: list[tuple[str, datetime]] = []

    def add(label: str, node_key: str):
        if race.get(node_key):
            n = race[node_key]
            sessions.append((label, _utc_dt(n.get("date"), n.get("time"))))

    add("FP1", "FirstPractice")
    add("FP2", "SecondPractice")
    add("FP3", "ThirdPractice")
    add("Qualifying", "Qualifying")
    add("Sprint", "Sprint")

    sessions.append(("Race", _utc_dt(race.get("date"), race.get("time"))))

    sessions.sort(key=lambda x: x[1])
    for label, dt in sessions:
        if dt > now:
            delta = dt - now
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            lines = [
                f"Next: {label}",
                f"Starts (UTC): {dt.strftime('%a %d %b %H:%M')}",
                f"Countdown: {hours}h {minutes}m",
            ]
            return (label, lines)
    return None


def post_weekend_update(mode: str) -> None:
    st = load_state()

    now = datetime.now(timezone.utc)
    force = os.getenv("F1_WEEKEND_FORCE", "false").lower() == "true"

    next_race = f1_api.get_next_race()
    season = next_race.get("season")
    round_ = next_race.get("round")
    race_name = next_race.get("raceName")
    circuit = (next_race.get("Circuit") or {})
    circuit_name = circuit.get("circuitName")
    loc = circuit.get("Location") or {}

    race_dt = _utc_dt(next_race.get("date"), next_race.get("time"))

    if not force and not _within_window(now, race_dt):
        print("Not in race weekend window; skipping.")
        return

    def post_schedule():
        lines: list[str] = []
        lines.append(f"Race: {race_name}")
        if circuit_name:
            lines.append(f"Circuit: {circuit_name}")
        lines.append(f"Race (UTC): {race_dt.strftime('%a %d %b %H:%M')}")
        if next_race.get("Qualifying"):
            q = next_race["Qualifying"]
            qdt = _utc_dt(q.get("date"), q.get("time"))
            lines.append(f"Qualifying (UTC): {qdt.strftime('%a %d %b %H:%M')}")
        if next_race.get("Sprint"):
            s = next_race["Sprint"]
            sdt = _utc_dt(s.get("date"), s.get("time"))
            lines.append(f"Sprint (UTC): {sdt.strftime('%a %d %b %H:%M')}")

        content = f"**F1 Weekend — {race_name}**\nSchedule in UTC (ask @Venbot if you want it in your timezone)."
        img = render_weekend_card(
            title=f"F1 Weekend: {race_name}",
            lines=lines,
            footer=f"Source: Ergast-compatible API · {now.strftime('%Y-%m-%d %H:%M UTC')}",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="schedule.png")

    def post_standings():
        ds = f1_api.get_driver_standings("current")[:10]
        cs = f1_api.get_constructor_standings("current")[:10]
        lines: list[str] = ["Top 10 Drivers:"]
        for d in ds:
            drv = d.get("Driver") or {}
            lines.append(f"{d.get('position')}. {_driver_name(drv)} — {d.get('points')} pts")
        lines.append("")
        lines.append("Top 10 Constructors:")
        for c in cs:
            con = c.get("Constructor") or {}
            lines.append(f"{c.get('position')}. {con.get('name')} — {c.get('points')} pts")

        content = "**F1 Standings (current)**"
        img = render_weekend_card(
            title="F1 Standings",
            lines=lines,
            footer=f"Source: Ergast-compatible API · {now.strftime('%Y-%m-%d %H:%M UTC')}",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="standings.png")

    def post_results():
        results = f1_api.get_race_results(season, round_)
        if not results:
            print("No race results available yet; skipping")
            return
        lines = [f"Results: {race_name}"]
        for r in results[:10]:
            drv = r.get("Driver") or {}
            cons = (r.get("Constructor") or {}).get("name")
            lines.append(f"{r.get('position')}. {_driver_name(drv)} ({cons})")
        content = f"**Race result — {race_name}**"
        img = render_weekend_card(
            title=f"Race result: {race_name}",
            lines=lines,
            footer=f"Source: Ergast-compatible API · {now.strftime('%Y-%m-%d %H:%M UTC')}",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="race_result.png")

    def post_quali():
        q = f1_api.get_qualifying_results(season, round_)
        if not q:
            print("No qualifying results available yet; skipping")
            return
        lines = [f"Qualifying: {race_name}"]
        for r in q[:10]:
            drv = r.get("Driver") or {}
            cons = (r.get("Constructor") or {}).get("name")
            q3 = r.get("Q3") or r.get("Q2") or r.get("Q1") or ""
            lines.append(f"{r.get('position')}. {_driver_name(drv)} ({cons}) {q3}")
        content = f"**Qualifying result — {race_name}**"
        img = render_weekend_card(
            title=f"Qualifying: {race_name}",
            lines=lines,
            footer="Note: penalties/grid changes may not be reflected · Ergast-compatible API",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="qualifying.png")

    def post_sprint():
        s = f1_api.get_sprint_results(season, round_)
        if not s:
            print("No sprint results available yet; skipping")
            return
        lines = [f"Sprint: {race_name}"]
        for r in s[:10]:
            drv = r.get("Driver") or {}
            cons = (r.get("Constructor") or {}).get("name")
            lines.append(f"{r.get('position')}. {_driver_name(drv)} ({cons})")
        content = f"**Sprint result — {race_name}**"
        img = render_weekend_card(
            title=f"Sprint: {race_name}",
            lines=lines,
            footer=f"Source: Ergast-compatible API · {now.strftime('%Y-%m-%d %H:%M UTC')}",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="sprint.png")

    def post_countdown():
        nxt = _next_session_card(next_race, now)
        if not nxt:
            print("No upcoming sessions; skipping")
            return
        _, lines = nxt
        content = f"**F1 weekend countdown — {race_name}**"
        img = render_weekend_card(
            title=f"Next session: {race_name}",
            lines=lines,
            footer=f"UTC · generated {now.strftime('%Y-%m-%d %H:%M')}",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="countdown.png")

    def post_track_facts():
        # Minimal track facts without a big dataset.
        country = loc.get("country")
        locality = loc.get("locality")
        lines = [
            f"Race: {race_name}",
        ]
        if circuit_name:
            lines.append(f"Circuit: {circuit_name}")
        if locality or country:
            lines.append(f"Location: {locality or ''} {('· ' + country) if country else ''}".strip())
        lines.append(f"Race (UTC): {race_dt.strftime('%a %d %b %H:%M')}")
        content = f"**Track card — {race_name}**"
        img = render_weekend_card(
            title=f"Track card: {race_name}",
            lines=lines,
            footer="Source: Ergast-compatible API",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="track.png")

    def post_weather():
        try:
            lat = float(loc.get("lat"))
            lon = float(loc.get("long"))
        except Exception:
            print("No circuit lat/long available; skipping weather")
            return
        data = get_hourly_forecast(lat, lon)
        hourly = data.get("hourly") or {}
        times = hourly.get("time") or []
        temps = hourly.get("temperature_2m") or []
        pops = hourly.get("precipitation_probability") or []
        winds = hourly.get("wind_speed_10m") or []

        # Find forecast hour closest to race start
        target = race_dt.replace(minute=0, second=0, microsecond=0)
        idx = None
        for i, t in enumerate(times):
            if t.startswith(target.strftime("%Y-%m-%dT%H")):
                idx = i
                break
        if idx is None:
            print("No matching forecast hour for race start; skipping weather")
            return

        t = temps[idx] if idx < len(temps) else None
        p = pops[idx] if idx < len(pops) else None
        w = winds[idx] if idx < len(winds) else None
        lines = [
            f"Race: {race_name}",
            f"Forecast (race hour, UTC): {target.strftime('%a %H:%M')}",
            f"Temp: {t}°C" if t is not None else "Temp: n/a",
            f"Rain chance: {p}%" if p is not None else "Rain chance: n/a",
            f"Wind: {w} km/h" if w is not None else "Wind: n/a",
        ]
        content = f"**Weather snapshot — {race_name}** (best effort)"
        img = render_weekend_card(
            title=f"Weather: {race_name}",
            lines=lines,
            footer="Source: Open-Meteo (UTC) · best effort",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="weather.png")

    def post_recap_last_race():
        last_race = f1_api.get_last_race()
        last_name = last_race.get("raceName")
        last_results = f1_api.get_last_race_results()
        if not last_results:
            print("No last race results available; skipping recap")
            return
        lines = [f"Last race: {last_name}"]
        for r in last_results[:5]:
            drv = r.get("Driver") or {}
            cons = (r.get("Constructor") or {}).get("name")
            lines.append(f"{r.get('position')}. {_driver_name(drv)} ({cons})")
        content = f"**Last race recap — {last_name}**"
        img = render_weekend_card(
            title=f"Recap: {last_name}",
            lines=lines,
            footer="Source: Ergast-compatible API",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="recap.png")

    def post_champ_delta():
        # Compare current standings vs previous round (if available)
        prev_round = str(max(1, int(round_) - 1))
        cur = {(_driver_name((d.get('Driver') or {}))): float(d.get('points', 0)) for d in f1_api.get_driver_standings('current')}
        prev = {(_driver_name((d.get('Driver') or {}))): float(d.get('points', 0)) for d in f1_api.get_driver_standings(season, prev_round)}
        if not prev:
            print("No previous-round standings available; skipping delta")
            return
        # pick top movers among current top 10
        top10 = list(cur.keys())[:10]
        deltas = []
        for name in top10:
            deltas.append((name, cur.get(name, 0) - prev.get(name, 0)))
        deltas.sort(key=lambda x: x[1], reverse=True)
        lines = [f"Championship delta (vs R{prev_round})"]
        for name, d in deltas[:5]:
            sign = "+" if d >= 0 else ""
            lines.append(f"{name}: {sign}{int(d)} pts")
        content = "**Championship delta** (best effort)"
        img = render_weekend_card(
            title="Champ delta",
            lines=lines,
            footer="Source: Ergast-compatible API",
        )
        send_webhook(WEBHOOK, content=content, file_bytes=img, filename="delta.png")

    def post_head_to_head():
        # Fun prompt only
        ds = f1_api.get_driver_standings("current")[:20]
        if len(ds) < 2:
            return
        a, b = random.sample(ds, 2)
        an = _driver_name((a.get("Driver") or {}))
        bn = _driver_name((b.get("Driver") or {}))
        content = f"**Head-to-head**\nWho finishes higher this weekend: **{an}** vs **{bn}**?"
        send_webhook(WEBHOOK, content=content)

    def post_thread_starter():
        content = (
            f"**Weekend thread — {race_name}**\n"
            "Predictions: \n"
            "• Pole: \n"
            "• Winner: \n"
            "• First DNF: \n"
            "• Surprise of the weekend: \n"
        )
        send_webhook(WEBHOOK, content=content)

    # Modes
    if mode != "auto":
        key = f"{mode}:{season}:{round_}"
        actions = {
            "schedule": post_schedule,
            "standings": post_standings,
            "results": post_results,
            "qualifying": post_quali,
            "sprint": post_sprint,
            "countdown": post_countdown,
            "track": post_track_facts,
            "weather": post_weather,
            "recap": post_recap_last_race,
            "delta": post_champ_delta,
            "h2h": post_head_to_head,
            "thread": post_thread_starter,
        }
        if mode not in actions:
            raise ValueError("Unknown mode")
        _post_once(st, key, actions[mode])
        return

    # AUTO: post a bundle across the weekend, de-duped.
    # Thursday/Friday: thread + schedule + track + recap
    weekday = now.weekday()  # Mon=0

    if weekday in (3, 4):
        _post_once(st, f"thread:{season}:{round_}", post_thread_starter)
        _post_once(st, f"schedule:{season}:{round_}", post_schedule)
        _post_once(st, f"track:{season}:{round_}", post_track_facts)
        _post_once(st, f"recap:{season}:{round_}", post_recap_last_race)

    # Countdown: only post on the Monday of the race weekend window (UTC).
    # (This keeps it low-noise while still providing a heads-up at the start of the week.)
    if weekday == 0:
        _post_once(st, f"countdown:{season}:{round_}", post_countdown)

    # Saturday: qualifying + sprint if available
    if weekday == 5:
        _post_once(st, f"qualifying:{season}:{round_}", post_quali)
        _post_once(st, f"sprint:{season}:{round_}", post_sprint)

    # Sunday: weather snapshot + race results + delta + standings
    if weekday == 6:
        _post_once(st, f"weather:{season}:{round_}", post_weather)
        _post_once(st, f"results:{season}:{round_}", post_results)
        _post_once(st, f"delta:{season}:{round_}", post_champ_delta)
        _post_once(st, f"standings:{season}:{round_}", post_standings)

    # Fun: head-to-head once per weekend
    _post_once(st, f"h2h:{season}:{round_}", post_head_to_head)


if __name__ == "__main__":
    mode = os.getenv("F1_WEEKEND_MODE", "auto")
    post_weekend_update(mode)
