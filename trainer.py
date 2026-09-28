#!/usr/bin/env python3
"""Interactive line-by-line memorization quiz for the poem in lyrics.txt."""

from __future__ import annotations

import argparse
import difflib
import random
import re
import sys
from pathlib import Path

DEFAULT_FILE = Path(__file__).resolve().parent / "lyrics.txt"

# Answers at or above this similarity count as correct; typos and modernized
# spelling ("dimmed" for "dimm'd") should not read as a failed recall.
CORRECT = 0.97
CLOSE = 0.80

# Apostrophes are dropped rather than spaced out, so "summer's" stays one word
# and lines up with how the reader types it.
APOSTROPHE = re.compile(r"['‘’]")
NON_WORD = re.compile(r"[^a-z0-9\s]")

HELP = """Commands: :hint  reveal first letters    :show  reveal the line
          :skip  move on                 :quit  end the round"""


def normalize(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace — for comparison only."""
    return " ".join(NON_WORD.sub(" ", APOSTROPHE.sub("", text.lower())).split())


def similarity(answer: str, expected: str) -> float:
    return difflib.SequenceMatcher(None, normalize(answer), normalize(expected)).ratio()


def missed_indices(answer: str, expected: str) -> list[int]:
    """Indices of words in `expected` that `answer` failed to produce."""
    want = normalize(expected).split()
    got = normalize(answer).split()
    matched: set[int] = set()
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(None, want, got).get_opcodes():
        if tag == "equal":
            matched.update(range(i1, i2))
    return [i for i in range(len(want)) if i not in matched]


def underline_misses(answer: str, expected: str) -> str:
    """The expected line with missed words bracketed."""
    words = expected.split()
    misses = set(missed_indices(answer, expected))
    if len(normalize(expected).split()) != len(words):
        return expected  # word counts drifted; show it plainly
    return " ".join(f"[{w}]" if i in misses else w for i, w in enumerate(words))


def first_letters(line: str) -> str:
    return " ".join(w[0] + "_" * (len(w) - 1) for w in line.split())


def load_lines(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.exit(f"Could not read {path}: {exc}")
    lines = [stripped for ln in raw.splitlines() if (stripped := ln.strip())]
    if not lines:
        sys.exit(f"No nonblank lines in {path}")
    return lines


def make_blanks(line: str, fraction: float) -> tuple[str, str]:
    """Return the line with some words blanked, and those words in order."""
    words = line.split()
    count = min(len(words), max(1, round(len(words) * fraction)))
    blanked = set(random.sample(range(len(words)), count))
    shown = " ".join(
        "_" * max(3, len(normalize(w))) if i in blanked else w
        for i, w in enumerate(words)
    )
    return shown, " ".join(words[i] for i in sorted(blanked))


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ":quit"


def run_question(cue: str, expected: str, label: str) -> str:
    """Ask one question. Returns 'correct', 'close', 'missed', 'skip' or 'quit'."""
    print(f"\n{label}")
    print(f"  {cue}")
    used_hint = False

    while True:
        answer = ask("> ")
        command = answer.lower()

        if command == ":quit":
            return "quit"
        if command == ":skip":
            print(f"  ... {expected}")
            return "skip"
        if command == ":show":
            print(f"  ... {expected}")
            return "missed"
        if command == ":hint":
            used_hint = True
            print(f"  hint: {first_letters(expected)}")
            continue
        if command in (":help", "?"):
            print(HELP)
            continue
        if not answer:
            continue

        score = similarity(answer, expected)
        if score >= CORRECT:
            print("  correct." if not used_hint else "  correct (with a hint).")
            return "close" if used_hint else "correct"
        if score >= CLOSE:
            print(f"  close — {underline_misses(answer, expected)}")
            return "close"

        print(f"  not quite — {expected}")
        return "missed"


def quiz_round(lines: list[str], order: list[int], mode: str, fraction: float) -> tuple[dict[str, int], list[int]]:
    tally = {"correct": 0, "close": 0, "missed": 0, "skip": 0}
    review: list[int] = []

    for position, index in enumerate(order, start=1):
        line = lines[index]
        label = f"Question {position} of {len(order)}  ·  line {index + 1}"

        if mode == "blanks":
            shown, expected = make_blanks(line, fraction)
            cue = shown
            label += " — fill in the blanks (missing words, in order)"
        else:
            expected = line
            cue = "(opening line)" if index == 0 else lines[index - 1]
            label += " — what comes next?"

        result = run_question(cue, expected, label)
        if result == "quit":
            print("\nStopping the round early.")
            break
        tally[result] += 1
        if result != "correct":
            review.append(index)

    return tally, review


def report(tally: dict[str, int]) -> None:
    answered = sum(tally.values())
    if not answered:
        print("\nNothing attempted.")
        return
    print(
        f"\n  {tally['correct']} correct · {tally['close']} close · "
        f"{tally['missed']} missed · {tally['skip']} skipped"
    )
    solid = tally["correct"] + tally["close"]
    print(f"  {solid}/{answered} lines recalled ({solid / answered:.0%}).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="lyrics file to study")
    parser.add_argument(
        "--mode",
        choices=("recall", "blanks", "review"),
        default="recall",
        help="recall: type the next line; blanks: fill in missing words; review: just print it",
    )
    parser.add_argument("--shuffle", action="store_true", help="ask lines out of order")
    parser.add_argument(
        "--blank-fraction",
        type=float,
        default=0.4,
        metavar="F",
        help="share of words to blank out in blanks mode (default: 0.4)",
    )
    parser.add_argument("--seed", type=int, help="seed the shuffle and blanks for a repeatable session")
    args = parser.parse_args()

    if not 0 < args.blank_fraction <= 1:
        parser.error("--blank-fraction must be between 0 and 1")
    if args.seed is not None:
        random.seed(args.seed)

    lines = load_lines(args.file)

    if args.mode == "review":
        for number, line in enumerate(lines, start=1):
            print(f"{number:2}  {line}")
        return

    print(f"{len(lines)} lines loaded from {args.file.name}.")
    print(HELP)

    order = list(range(len(lines)))
    if args.shuffle:
        random.shuffle(order)

    while True:
        tally, review = quiz_round(lines, order, args.mode, args.blank_fraction)
        report(tally)
        if not review:
            if sum(tally.values()):
                print("  Whole round clean.")
            return
        again = ask(f"\nDrill the {len(review)} line(s) you stumbled on? [Y/n] ").lower()
        if again in (":quit", "n", "no"):
            return
        order = review


if __name__ == "__main__":
    main()
