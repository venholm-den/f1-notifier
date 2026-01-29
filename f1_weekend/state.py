import json
import os
from dataclasses import dataclass


STATE_FILE = os.getenv("F1_WEEKEND_STATE_FILE", "f1_weekend_state.json")


@dataclass
class State:
    posted: set[str]


def load_state() -> State:
    if not os.path.exists(STATE_FILE):
        return State(posted=set())
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    posted = set((data.get("posted") or []))
    return State(posted=posted)


def save_state(state: State) -> None:
    data = {"posted": sorted(state.posted)}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
