import os
import requests


DEFAULT_TIMEOUT = 30

# Prefer Jolpica (Ergast-compatible). Fall back to legacy Ergast if needed.
BASE_URLS = [
    os.getenv("F1_API_BASE", "https://api.jolpi.ca/ergast"),
    "https://ergast.com/mrd",
]


def _get_json(path: str) -> dict:
    last_err = None
    for base in BASE_URLS:
        url = base.rstrip("/") + "/" + path.lstrip("/")
        try:
            r = requests.get(url, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"F1 API request failed for {path}: {last_err}")


def get_next_race() -> dict:
    # Ergast-compatible: /f1/current/next.json
    data = _get_json("/f1/current/next.json")
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        raise RuntimeError("No next race returned by API")
    return races[0]


def get_race(season: str, round_: str) -> dict:
    data = _get_json(f"/f1/{season}/{round_}.json")
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        raise RuntimeError("No race returned by API")
    return races[0]


def get_race_results(season: str, round_: str) -> list[dict]:
    data = _get_json(f"/f1/{season}/{round_}/results.json")
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        return []
    race = races[0]
    results = race.get("Results") or []
    return results


def get_driver_standings(season: str = "current") -> list[dict]:
    data = _get_json(f"/f1/{season}/driverStandings.json")
    lists = (((data.get("MRData") or {}).get("StandingsTable") or {}).get("StandingsLists") or [])
    if not lists:
        return []
    return (lists[0].get("DriverStandings") or [])


def get_constructor_standings(season: str = "current") -> list[dict]:
    data = _get_json(f"/f1/{season}/constructorStandings.json")
    lists = (((data.get("MRData") or {}).get("StandingsTable") or {}).get("StandingsLists") or [])
    if not lists:
        return []
    return (lists[0].get("ConstructorStandings") or [])
