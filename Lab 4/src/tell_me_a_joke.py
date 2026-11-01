import json
from pathlib import Path
import sys

import requests


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LOG_FILE = PROJECT_DIR / "logs" / "lab4.log"
JOKE_URL = "https://icanhazdadjoke.com/"


def log_marker(marker: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{marker}\n")


def report_error(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    log_marker("LAB4_ERR")
    return 1


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(
            JOKE_URL,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if response.status_code != 200:
            return report_error(f"Joke API returned HTTP {response.status_code}.")
        log_marker("LAB4_JOKE_HTTP_OK")

        data = response.json()
        if not isinstance(data, dict):
            return report_error("Joke API returned an invalid JSON object.")
        log_marker("LAB4_JOKE_JSON_OK")

        joke = data.get("joke")
        if not isinstance(joke, str) or not joke.strip():
            return report_error("Joke API response did not contain joke text.")

        (DATA_DIR / "joke.json").write_text(
            f"{json.dumps(data, indent=2, ensure_ascii=False)}\n",
            encoding="utf-8",
        )
        (DATA_DIR / "joke.txt").write_text(f"{joke}\n", encoding="utf-8")

        print(joke)
        log_marker("LAB4_JOKE_PRINTED")
        return 0
    except requests.Timeout:
        return report_error("Joke API request timed out.")
    except requests.RequestException as error:
        return report_error(f"Joke API request failed: {error}")
    except (OSError, ValueError) as error:
        return report_error(f"Could not process the joke API response: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
