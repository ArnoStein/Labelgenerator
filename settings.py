import json
import os


DEFAULT_SETTINGS = {
    "output_dir": "output",
    "printer_name": "",
    "sumatra_path": "",
    "quick_print": False,
}


def load_settings(path):
    if not os.path.exists(path):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = DEFAULT_SETTINGS.copy()
        merged.update({k: v for k, v in data.items() if k in merged})
        return merged
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()


def save_settings(path, settings):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=True, indent=2)
