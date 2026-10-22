"""Yahtzee para dos jugadores y experimentos Montecarlo. Solo biblioteca estándar."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import random
from pathlib import Path


CATEGORIES = ("unos", "doses", "treses", "cuatros", "cincos", "seises",
              "trio", "cuarteto", "full", "escalera_corta", "escalera_larga",
              "yahtzee", "azar")
UPPER = CATEGORIES[:6]
RESERVATION = {**{name: 1.5 * (i + 1) for i, name in enumerate(UPPER)},
               "trio": 9, "cuarteto": 13, "full": 14,
               "escalera_corta": 16, "escalera_larga": 22,
               "yahtzee": 25, "azar": 16}


def roll(rng: random.Random, dice: list[int] | None = None,
         keep: set[int] | None = None) -> list[int]:
    """Lanza cinco dados, o relanza los índices no retenidos."""
    if dice is None:
        return [rng.randint(1, 6) for _ in range(5)]
    keep = keep or set()
    return [value if i in keep else rng.randint(1, 6)
            for i, value in enumerate(dice)]


def is_yahtzee(dice: list[int]) -> bool:
    return len(set(dice)) == 1


def legal_categories(dice: list[int], card: dict[str, int]) -> list[str]:
    available = [name for name in CATEGORIES if name not in card]
    if is_yahtzee(dice) and "yahtzee" in card:
        matching_upper = UPPER[dice[0] - 1]
        if matching_upper in available:
            return [matching_upper]
        lower = [name for name in available if name not in UPPER]
        if lower:
            return lower
    return available


def points(dice: list[int], category: str, joker: bool = False) -> int:
    counts = Counter(dice)
    total = sum(dice)
    unique = set(dice)
    if category in UPPER:
        face = UPPER.index(category) + 1
        return face * counts[face]
    if category == "trio":
        return total if max(counts.values()) >= 3 else 0
    if category == "cuarteto":
        return total if max(counts.values()) >= 4 else 0
    if category == "full":
        return 25 if joker or sorted(counts.values()) == [2, 3] else 0
    if category == "escalera_corta":
        return 30 if joker or any(set(range(start, start + 4)) <= unique
                                  for start in (1, 2, 3)) else 0
    if category == "escalera_larga":
        return 40 if joker or unique in ({1, 2, 3, 4, 5},
                                        {2, 3, 4, 5, 6}) else 0
    if category == "yahtzee":
        return 50 if is_yahtzee(dice) else 0
    if category == "azar":
        return total
    raise ValueError(f"Categoría desconocida: {category}")


def score_for(dice: list[int], category: str, card: dict[str, int]) -> int:
    joker = (is_yahtzee(dice) and "yahtzee" in card
             and UPPER[dice[0] - 1] in card)
    if joker and category in UPPER:
        return 0
    return points(dice, category, joker)


def total_score(card: dict[str, int], bonuses: int = 0) -> int:
    upper = sum(card.get(name, 0) for name in UPPER)
    return sum(card.values()) + (35 if upper >= 63 else 0) + bonuses


def best_category(dice: list[int], card: dict[str, int]) -> str:
    available = legal_categories(dice, card)
    return max(available, key=lambda name: (score_for(dice, name, card)
                                             - RESERVATION[name],
                                             score_for(dice, name, card)))


def keep_for(dice: list[int], category: str) -> set[int]:
    counts = Counter(dice)
    if category in UPPER:
        face = UPPER.index(category) + 1
        return {i for i, value in enumerate(dice) if value == face}
    if category in ("trio", "cuarteto", "yahtzee", "full"):
        if category == "full" and sorted(counts.values()) == [2, 3]:
            return set(range(5))
        face = max(counts, key=lambda value: (counts[value], value))
        return {i for i, value in enumerate(dice) if value == face}
    if category in ("escalera_corta", "escalera_larga"):
        length = 4 if category == "escalera_corta" else 5
        starts = (1, 2, 3) if length == 4 else (1, 2)
        target = max(starts, key=lambda start: len(set(dice) &
                                                  set(range(start, start + length))))
        wanted = set(range(target, target + length))
        found = set()
        kept = set()
        for i, value in enumerate(dice):
            if value in wanted and value not in found:
                found.add(value)
                kept.add(i)
        return kept
    return {i for i, value in enumerate(dice) if value >= 4}


def monte_carlo_keep(dice: list[int], remaining: int, card: dict[str, int],
                     rng: random.Random, samples: int) -> set[int]:
    """Estima la utilidad de cada objetivo con muestreo uniforme."""
    best_value = float("-inf")
    best_keep: set[int] = set()
    for category in CATEGORIES:
        if category in card:
            continue
        keep = keep_for(dice, category)
        # Retener todo permite cerrar el turno con una buena mano actual.
        candidates = (keep, set(range(5)))
        for candidate in candidates:
            value = 0.0
            for _ in range(samples):
                trial = dice[:]
                for throw in range(remaining):
                    trial = roll(rng, trial, candidate if throw == 0 else
                                 keep_for(trial, category))
                if category in legal_categories(trial, card):
                    value += score_for(trial, category, card) - RESERVATION[category]
                else:
                    chosen = best_category(trial, card)
                    value += score_for(trial, chosen, card) - RESERVATION[chosen]
            value /= samples
            if value > best_value:
                best_value, best_keep = value, candidate
    return best_keep


def choose_keep(dice: list[int], remaining: int, card: dict[str, int],
                policy: str, rng: random.Random, samples: int) -> set[int]:
    if policy == "mc":
        return monte_carlo_keep(dice, remaining, card, rng, samples)
    category = best_category(dice, card)
    return keep_for(dice, category)


def bot_turn(card: dict[str, int], policy: str, rng: random.Random,
             samples: int) -> tuple[list[int], str, int, int]:
    dice = roll(rng)
    for remaining in (2, 1):
        keep = choose_keep(dice, remaining, card, policy, rng, samples)
        if len(keep) == 5:
            break
        dice = roll(rng, dice, keep)
    category = best_category(dice, card)
    earned = score_for(dice, category, card)
    bonus = 100 if is_yahtzee(dice) and card.get("yahtzee") == 50 else 0
    card[category] = earned
    return dice, category, earned, bonus


def human_turn(card: dict[str, int], rng: random.Random) -> tuple[list[int], str, int, int]:
    dice = roll(rng)
    for throw in (1, 2, 3):
        print(f"Lanzamiento {throw}: {dice}")
        if throw == 3:
            break
        while True:
            answer = input("Índices a conservar (1-5, separados por espacios; Enter para anotar): ").strip()
            if not answer:
                break
            try:
                keep = {int(part) - 1 for part in answer.split()}
                if not keep <= set(range(5)):
                    raise ValueError
            except ValueError:
                print("Ingrese solo índices del 1 al 5.")
                continue
            dice = roll(rng, dice, keep)
            break
        if not answer:
            break
    available = legal_categories(dice, card)
    print("Categorías disponibles:", ", ".join(f"{name}={score_for(dice, name, card)}"
                                                    for name in available))
    while True:
        category = input("Categoría para anotar: ").strip().lower()
        if category in available:
            break
        print("Elija una categoría disponible.")
    earned = score_for(dice, category, card)
    bonus = 100 if is_yahtzee(dice) and card.get("yahtzee") == 50 else 0
    card[category] = earned
    return dice, category, earned, bonus


def game(policy1: str, policy2: str, rng: random.Random, samples: int,
         verbose: bool = False) -> dict:
    cards = [{}, {}]
    bonuses = [0, 0]
    policies = (policy1, policy2)
    for round_no in range(1, 14):
        for player in range(2):
            if verbose:
                print(f"\nRonda {round_no}, jugador {player + 1} ({policies[player]})")
            if policies[player] == "human":
                dice, category, earned, bonus = human_turn(cards[player], rng)
            else:
                dice, category, earned, bonus = bot_turn(cards[player], policies[player],
                                                          rng, samples)
            bonuses[player] += bonus
            if verbose:
                print(f"Dados {dice} -> {category}: {earned} puntos; bono Yahtzee: {bonus}")
                print(f"Total provisional: {total_score(cards[player], bonuses[player])}")
    scores = [total_score(cards[i], bonuses[i]) for i in range(2)]
    winner = 0 if scores[0] == scores[1] else (1 if scores[0] > scores[1] else 2)
    return {"scores": scores, "winner": winner, "cards": cards,
            "yahtzee_bonuses": bonuses}


def simulate(games: int, samples: int, seed: int) -> dict:
    rng = random.Random(seed)
    outcomes = [game("mc", "greedy", rng, samples) for _ in range(games)]
    scores_mc = [item["scores"][0] for item in outcomes]
    scores_greedy = [item["scores"][1] for item in outcomes]
    return {"seed": seed, "games": games, "samples_per_candidate": samples,
            "policies": ["mc", "greedy"],
            "wins": {"mc": sum(item["winner"] == 1 for item in outcomes),
                     "greedy": sum(item["winner"] == 2 for item in outcomes),
                     "ties": sum(item["winner"] == 0 for item in outcomes)},
            "mean_score": {"mc": round(sum(scores_mc) / games, 2),
                           "greedy": round(sum(scores_greedy) / games, 2)},
            "min_score": {"mc": min(scores_mc), "greedy": min(scores_greedy)},
            "max_score": {"mc": max(scores_mc), "greedy": max(scores_greedy)}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    play = sub.add_parser("play", help="jugar una partida")
    play.add_argument("--player1", choices=("human", "mc", "greedy"), default="human")
    play.add_argument("--player2", choices=("human", "mc", "greedy"), default="mc")
    play.add_argument("--samples", type=int, default=32)
    play.add_argument("--seed", type=int)
    batch = sub.add_parser("simulate", help="comparar estrategias en muchas partidas")
    batch.add_argument("--games", type=int, default=100)
    batch.add_argument("--samples", type=int, default=32)
    batch.add_argument("--seed", type=int, default=2026)
    batch.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.samples < 1 or (args.command == "simulate" and args.games < 1):
        parser.error("--samples y --games deben ser enteros positivos")
    if args.command == "play":
        result = game(args.player1, args.player2, random.Random(args.seed),
                      args.samples, verbose=True)
        print("\nMarcador final:", result["scores"], "| Ganador:",
              "empate" if result["winner"] == 0 else f"jugador {result['winner']}")
    else:
        result = simulate(args.games, args.samples, args.seed)
        encoded = json.dumps(result, ensure_ascii=False, indent=2)
        print(encoded)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
