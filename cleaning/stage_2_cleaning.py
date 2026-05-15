import re
import json
import time
import requests
from pathlib import Path
from collections import defaultdict

# =========================
# CONFIG
# =========================

INPUT_DOC = "XX_system_raw.md"
OUTPUT_DOC = "XX_clean.md"


# =========================
# FILTER PATTERNS (AI BULLSHIT)
# =========================

REMOVE_PATTERNS = [
    r"This sequence highlights",
    r"standalone component",
    r"does not depend on any external",
    r"no execution order dependencies",
    r"Since there are no specific actions",
    r"can be considered",
    r"it is not possible to construct",
    r"no direct data flow",
    r"based on the input provided",
]

CHUNK_PATTERN = re.compile(r"^## Chunk \d+", re.IGNORECASE)

# =========================
# CLEANING
# =========================

def clean_text(text):
    return "\n".join([l.rstrip() for l in text.splitlines()])


def remove_noise(text):
    out = []

    for line in text.splitlines():
        l = line.strip()

        # remove chunk headers
        if CHUNK_PATTERN.match(l):
            continue

        # remove bullshit sentences
        if any(p.lower() in l.lower() for p in REMOVE_PATTERNS):
            continue

        out.append(line)

    return "\n".join(out)


def deduplicate_exact(text):
    seen = set()
    out = []

    for line in text.splitlines():
        key = line.strip()

        if not key:
            out.append("")
            continue

        if key not in seen:
            seen.add(key)
            out.append(line)

    return "\n".join(out)


# =========================
# MAIN
# =========================

def main():

    print("STEP 4 START")

    text = Path(INPUT_DOC).read_text(encoding="utf-8")

    print("Cleaning whitespace...")
    text = clean_text(text)

    print("Removing AI noise...")
    text = remove_noise(text)

    print("Deduplicating...")
    text = deduplicate_exact(text)

    Path(OUTPUT_DOC).write_text(text, encoding="utf-8")

    print("DONE →", OUTPUT_DOC)


# =========================

if __name__ == "__main__":
    main()