import json
from pathlib import Path

STATE_FILE = Path.home() / ".local" / "share" / "usawa" / "state.json"


class StateManager:

    @staticmethod
    def get_state() -> dict:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
        return {}

    @staticmethod
    def save_state(data: dict):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(data, indent=2))

    @staticmethod
    def get(key: str, default=None):
        return StateManager.get_state().get(key, default)

    @staticmethod
    def set(key: str, value):
        state = StateManager.get_state()
        state[key] = value
        StateManager.save_state(state)
