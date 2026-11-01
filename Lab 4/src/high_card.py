import json
from pathlib import Path
import sys
from typing import Any

import requests


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LOG_FILE = PROJECT_DIR / "logs" / "lab4.log"
ROUNDS_FILE = DATA_DIR / "high_card_rounds.json"
RESULT_FILE = DATA_DIR / "high_card_result.txt"
DECK_URL = "https://deckofcardsapi.com/api/deck/new/shuffle/?deck_count=1"
CARD_VALUES = {
    **{str(value): value for value in range(2, 11)},
    "JACK": 11,
    "QUEEN": 12,
    "KING": 13,
    "ACE": 14,
}


class ApiError(Exception):
    pass


def log_marker(marker: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{marker}\n")


def report_error(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    log_marker("LAB4_ERR")
    return 1


def read_player_count() -> int:
    while True:
        try:
            response = input("How many players are playing? ")
        except EOFError as error:
            raise ValueError("No player count was provided.") from error

        try:
            player_count = int(response)
        except ValueError:
            print("Enter a whole number from 2 to 52.", file=sys.stderr)
            continue

        if not 2 <= player_count <= 52:
            print("Enter a whole number from 2 to 52.", file=sys.stderr)
            continue
        return player_count


def request_json(url: str, action: str) -> dict[str, Any]:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise ApiError(f"{action} returned HTTP {response.status_code}.")

    data = response.json()
    if not isinstance(data, dict):
        raise ApiError(f"{action} returned an invalid JSON object.")
    if data.get("success") is not True:
        raise ApiError(f"{action} was not successful.")
    return data


def card_value(card: dict[str, Any]) -> int:
    value = card.get("value")
    if not isinstance(value, str) or value.upper() not in CARD_VALUES:
        raise ApiError("A drawn card had an unrecognized rank.")
    return CARD_VALUES[value.upper()]


def card_description(card: dict[str, Any]) -> str:
    value = card.get("value")
    suit = card.get("suit")
    if not isinstance(value, str) or not isinstance(suit, str):
        raise ApiError("A drawn card was missing its rank or suit.")
    return f"{value.title()} of {suit.title()}"


def save_rounds(game_data: dict[str, Any]) -> None:
    ROUNDS_FILE.write_text(
        f"{json.dumps(game_data, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        player_count = read_player_count()
        deck = request_json(DECK_URL, "Deck creation")
        deck_id = deck.get("deck_id")
        if not isinstance(deck_id, str) or not deck_id:
            raise ApiError("Deck creation response did not contain a deck ID.")
        log_marker("LAB4_DECK_CREATE_OK")

        game_data: dict[str, Any] = {
            "deck_id": deck_id,
            "players": player_count,
            "rounds": [],
        }
        save_rounds(game_data)

        active_players = list(range(1, player_count + 1))
        final_winner = 0
        final_card: dict[str, Any] = {}
        round_number = 1

        while True:
            is_tie_breaker = round_number > 1
            draw_url = (
                f"https://deckofcardsapi.com/api/deck/{deck_id}/draw/"
                f"?count={len(active_players)}"
            )
            draw_data = request_json(draw_url, "Card draw")
            cards = draw_data.get("cards")
            if not isinstance(cards, list) or len(cards) != len(active_players):
                raise ApiError("Card draw did not return one card per active player.")

            dealt_cards: list[dict[str, Any]] = []
            for player, card in zip(active_players, cards):
                if not isinstance(card, dict):
                    raise ApiError("Card draw returned an invalid card.")
                dealt_cards.append({"player": player, "card": card})

            ranked_cards = [
                (card_value(entry["card"]), entry["player"], entry["card"])
                for entry in dealt_cards
            ]
            highest_value = max(value for value, _, _ in ranked_cards)
            tied_players = [
                (player, card)
                for value, player, card in ranked_cards
                if value == highest_value
            ]

            game_data["rounds"].append(
                {
                    "round": round_number,
                    "type": "tie_breaker" if is_tie_breaker else "initial",
                    "eligible_players": active_players,
                    "response": draw_data,
                    "cards": dealt_cards,
                    "tied_players": [player for player, _ in tied_players],
                }
            )
            save_rounds(game_data)

            if is_tie_breaker:
                log_marker("LAB4_TIE_ROUND")
            else:
                log_marker("LAB4_DRAW_OK")

            if len(tied_players) == 1:
                final_winner, final_card = tied_players[0]
                break

            active_players = [player for player, _ in tied_players]
            round_number += 1

        lines = ["HIGH CARD GAME RESULTS", "", f"Players: {player_count}", ""]
        for game_round in game_data["rounds"]:
            label = (
                f"Round {game_round['round']}:"
                if game_round["type"] == "initial"
                else f"Tie-breaker Round {game_round['round']}:"
            )
            lines.append(label)
            for entry in game_round["cards"]:
                lines.append(
                    f"Player {entry['player']}: {card_description(entry['card'])}"
                )
            if len(game_round["tied_players"]) > 1:
                tied = ", ".join(
                    f"Player {player}" for player in game_round["tied_players"]
                )
                lines.append(f"Tie: {tied}")
            lines.append("")

        lines.extend(
            [
                f"Winner: Player {final_winner}",
                f"Final Winning Card: {card_description(final_card)}",
                "",
            ]
        )
        RESULT_FILE.write_text("\n".join(lines), encoding="utf-8")

        print("\n".join(lines), end="")
        log_marker("LAB4_GAME_END")
        return 0
    except requests.Timeout:
        return report_error("A card API request timed out.")
    except requests.RequestException as error:
        return report_error(f"A card API request failed: {error}")
    except (ApiError, OSError, ValueError) as error:
        return report_error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
