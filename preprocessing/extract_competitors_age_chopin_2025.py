#!/usr/bin/env python3
"""Extract competitor ages from HTML biographies and add to chopin_2025.json."""

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path


def normalize_name(name: str) -> str:
    """
    Normalize name for matching by removing diacritics and parentheticals.

    Args:
        name: Name to normalize

    Returns:
        Normalized name (ASCII, no parentheticals, collapsed spaces)
    """
    # Remove parenthetical nicknames like "(Zach)"
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)
    # Remove diacritics
    name = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )
    # Collapse multiple spaces
    name = ' '.join(name.split())
    return name.lower()


def extract_name_and_age(html_content: str) -> tuple[str, str, int] | None:
    """
    Extract first name, last name, and age from biography HTML.

    Args:
        html_content: HTML content of biography page

    Returns:
        Tuple of (first_name, last_name, age) or None if not found
    """
    # Extract birth date from "Born on DD Month YYYY"
    birth_match = re.search(r'Born on\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', html_content)
    if not birth_match:
        return None

    day_str, month_str, year_str = birth_match.groups()

    # Map month names to numbers
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    month = months.get(month_str.lower())
    if not month:
        return None

    try:
        birth_date = datetime(int(year_str), month, int(day_str))
    except ValueError:
        return None

    # Calculate age at competition date (2025-10-03)
    competition_date = datetime(2025, 10, 3)
    age = competition_date.year - birth_date.year
    if (competition_date.month, competition_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    # Extract names from pattern: children\\":[\\"FirstName\\",\\" \\",\\"\\",\\" \\",\\"LastName\\"]
    # File contains literal: children\\":[\\"Yanyan\\",\\" \\",\\"\\",\\" \\",\\"Bao\\"]
    birth_index = html_content.find('Born on')
    if birth_index <= 0:
        return None

    # Search backwards from birth date - the names appear within ~1100 chars before
    search_start = max(0, birth_index - 1500)
    context = html_content[search_start:birth_index]

    # Pattern: children\\":\[\\\"FirstName\\"...\\\"LastName\\"]
    # File has: children\":[\\"Yanyan\\",\\" \\",\\"\\",\\" \\",\\"Bao\\"]
    # Array has 5 elements: first name, space, empty, space, last name
    # Match first element and last element (before closing bracket)
    # Names can include: spaces, hyphens, parentheses, extended Latin chars
    # Examples: "Chun Lam", "Kai-Min", "Yang (Jack)", "Krzysztof", "Kałduński"
    name_pattern = r'children\\":\[\\"([A-Za-z\u00C0-\u017F\s\-()]+)\\"[^]]*,\\"([A-Za-z\u00C0-\u017F\s\-()]+)\\"]'
    name_match = re.search(name_pattern, context)

    if name_match:
        # Strip extra spaces from extracted names
        first_name = name_match.group(1).strip()
        last_name = name_match.group(2).strip()
        return first_name, last_name, age

    return None


def find_matching_participant(
    bio_first: str,
    bio_last: str,
    participants: list[dict]
) -> dict | None:
    """
    Find matching participant using various strategies.

    Args:
        bio_first: First name from biography
        bio_last: Last name from biography
        participants: List of participant dictionaries

    Returns:
        Matching participant dict or None
    """
    # Normalize biography name
    bio_full = normalize_name(f"{bio_first} {bio_last}")

    # Try matching each participant
    for p in participants:
        json_first = p["first_name"]
        json_last = p["last_name"]
        json_full = normalize_name(f"{json_first} {json_last}")

        # Strategy 1: Exact normalized match
        if bio_full == json_full:
            return p

        # Strategy 2: Try alternative name splits
        # Biography "Chun Lam" + "U" vs JSON "Chun" + "Lam U"
        bio_parts = bio_full.split()
        json_parts = json_full.split()

        # Check if all parts match (regardless of split position)
        if bio_parts == json_parts:
            return p

    return None


def main() -> None:
    """Extract ages from biography files and add to chopin_2025.json."""
    competitors_dir = Path("data/www.chopincompetition.pl/competitors")
    json_file = Path("data/chopin_2025.json")

    if not json_file.exists():
        print(f"Error: {json_file} not found")
        return

    # Load existing JSON
    with open(json_file) as f:
        data = json.load(f)

    ages_added = 0
    names_updated = 0
    names_not_found = 0

    # Process each biography file (only numeric filenames)
    for bio_file in sorted(competitors_dir.iterdir()):
        if not bio_file.is_file():
            continue
        # Only process numeric filenames (biography IDs)
        if not bio_file.name.isdigit():
            continue

        try:
            with open(bio_file, encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            print(f"Error reading {bio_file}: {e}")
            continue

        result = extract_name_and_age(html_content)
        if result is None:
            names_not_found += 1
            print(f"Could not extract from {bio_file.name}")
            continue

        bio_first, bio_last, age = result
        print(f"{bio_first} {bio_last}: {age} years")

        # Find matching participant
        participant = find_matching_participant(bio_first, bio_last, data["participants"])

        if participant:
            # Update age
            participant["age"] = age
            ages_added += 1

            # Update name if different (to add diacritics)
            if participant["first_name"] != bio_first or participant["last_name"] != bio_last:
                print(f"  Updating name: {participant['first_name']} {participant['last_name']} → {bio_first} {bio_last}")
                participant["first_name"] = bio_first
                participant["last_name"] = bio_last
                names_updated += 1
        else:
            names_not_found += 1
            print(f"  WARNING: Not found in participants list")

    # Write updated JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nSummary:")
    print(f"  Added ages to {ages_added} participants")
    print(f"  Updated {names_updated} names with correct spelling")
    if names_not_found > 0:
        print(f"  Could not match {names_not_found} biographies")


if __name__ == "__main__":
    main()
