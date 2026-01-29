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


def _race0(path: str) -> dict:
    data = _get_json(path)
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        raise RuntimeError(f"No race returned by API for {path}")
    return races[0]


def get_next_race() -> dict:
    return _race0("/f1/current/next.json")


def get_last_race() -> dict:
    return _race0("/f1/current/last.json")


def get_race(season: str, round_: str) -> dict:
    return _race0(f"/f1/{season}/{round_}.json")


def get_race_results(season: str, round_: str) -> list[dict]:
    data = _get_json(f"/f1/{season}/{round_}/results.json")
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        return []
    return races[0].get("Results") or []


def get_last_race_results() -> list[dict]:
    data = _get_json("/f1/current/last/results.json")
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        return []
    return races[0].get("Results") or []


def get_qualifying_results(season: str, round_: str) -> list[dict]:
    data = _get_json(f"/f1/{season}/{round_}/qualifying.json")
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        return []
    return races[0].get("QualifyingResults") or []


def get_sprint_results(season: str, round_: str) -> list[dict]:
    data = _get_json(f"/f1/{season}/{round_}/sprint.json")
    races = (((data.get("MRData") or {}).get("RaceTable") or {}).get("Races") or [])
    if not races:
        return []
    return races[0].get("SprintResults") or []


def get_driver_standings(season: str = "current", round_: str | None = None) -> list[dict]:
    path = f"/f1/{season}/driverStandings.json" if not round_ else f"/f1/{season}/{round_}/driverStandings.json"
    data = _get_json(path)
    lists = (((data.get("MRData") or {}).get("StandingsTable") or {}).get("StandingsLists") or [])
    if not lists:
        return []
    return (lists[0].get("DriverStandings") or [])


def get_constructor_standings(season: str = "current", round_: str | None = None) -> list[dict]:
    path = f"/f1/{season}/constructorStandings.json" if not round_ else f"/f1/{season}/{round_}/constructorStandings.json"
    data = _get_json(path)
    lists = (((data.get("MRData") or {}).get("StandingsTable") or {}).get("StandingsLists") or [])
    if not lists:
        return []
    return (lists[0].get("ConstructorStandings") or [])
