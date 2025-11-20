#!/usr/bin/env python3
"""Extract performance schedules from text files and add to competition JSON."""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def normalize_name(name: str) -> str:
    """Normalize name by removing parenthetical content and diacritical marks for matching."""
    # Remove content in parentheses like "(Zach)" or "(WN 44)"
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)
    # Remove diacritical marks (é -> e, ó -> o, ł -> l, etc.)
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    # Clean up extra spaces
    name = ' '.join(name.split())
    return name


def parse_schedule_file(file_path: str) -> dict[str, dict[str, Any]]:
    """
    Parse schedule text file and extract participant performance times.

    Uses fixed playing durations by stage (15-minute resolution):
    - Stage 1: 30 minutes (approx. 25-30 min performances)
    - Stage 2: 45 minutes (40-50 min as per official regulations)
    - Stage 3: 60 minutes (45-55 min as per official regulations)
    - Final: 60 minutes (Polonaise-Fantasy + Piano Concerto)

    Official regulations: https://konkursy.nifc.pl/en/miedzynarodowy/regulamin

    Start times are extracted directly from schedule files (preserving actual times like 20:20).

    Args:
        file_path: Path to schedule text file (e.g., data/chopin-2025-stage1-2025-10-03.txt)

    Returns:
        Dictionary mapping "FirstName LastName" to {"date": "YYYY-MM-DD", "time_start": "HH:MM", "time_stop": "HH:MM"}
    """
    schedule = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Extract date from filename: data/chopin-2025-stage1-2025-10-03.txt or chopin-2025-final-2025-10-18.txt
    file_stem = Path(file_path).stem
    parts = file_stem.split('-')
    if len(parts) >= 3:
        date_str = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
    else:
        raise ValueError(f"Cannot extract date from filename {file_path}")

    # Determine stage and playing duration
    if 'final' in file_path.lower():
        stage = 'final'
        playing_duration_minutes = 60
    elif 'stage3' in file_path.lower():
        stage = 'stage3'
        playing_duration_minutes = 60
    elif 'stage2' in file_path.lower():
        stage = 'stage2'
        playing_duration_minutes = 45
    elif 'stage1' in file_path.lower():
        stage = 'stage1'
        playing_duration_minutes = 30
    else:
        raise ValueError(f"Cannot determine stage from filename {file_path}")

    # Extract participant names and their scheduled start times
    participants_with_times = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for participant name pattern (first line starts with capital, next line is name+country)
        if len(line) > 0 and line[0].isupper() and not any(skip in line.lower() for skip in ['session', 'programme', 'orchestra', 'conductor']):
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

            # Clean participant name (remove URLs if present, like in stage 3)
            participant_name_clean = re.sub(r'"https://.*?"', '', line).strip()

            # Check if next line is name + country (starts with current name and is longer)
            if next_line and next_line.startswith(participant_name_clean) and len(next_line) > len(participant_name_clean):
                # Found participant name
                participant_name = participant_name_clean

                # Find the time (HH:MM) after the name
                # Search up to 15 lines ahead to handle stage3/final formats with orchestra/conductor info
                time_start = None
                for j in range(i + 2, min(i + 15, len(lines))):
                    check_line = lines[j].strip()
                    if re.match(r'^\d{2}:\d{2}$', check_line):
                        time_start = check_line
                        break

                if time_start:
                    participants_with_times.append((participant_name, time_start))

                i += 2
                continue

        i += 1

    # Apply fixed playing duration to all participants
    for name, time_start in participants_with_times:
        start_h, start_m = map(int, time_start.split(':'))
        start_total = start_h * 60 + start_m
        stop_total = start_total + playing_duration_minutes

        # Convert back to HH:MM
        stop_h = stop_total // 60
        stop_m = stop_total % 60
        time_stop = f"{stop_h:02d}:{stop_m:02d}"

        schedule[name] = {
            "date": date_str,
            "time_start": time_start,
            "time_stop": time_stop
        }

    return schedule


def add_schedule_to_json(json_path: str, schedule_files: list[str]) -> None:
    """
    Add schedule information to competition JSON file.

    Args:
        json_path: Path to competition JSON file
        schedule_files: List of schedule text file paths
    """
    # Read JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract stage from schedule file name and parse each file
    # Format: data/chopin-2025-stageN-YYYY-MM-DD.txt or chopin-2025-final-YYYY-MM-DD.txt
    stage_schedules: dict[str, dict[str, dict[str, Any]]] = {}
    for schedule_file in schedule_files:
        # Extract stage from filename
        match = re.search(r'stage(\d+)', schedule_file)
        if match:
            stage = f"stage{match.group(1)}"
        else:
            match = re.search(r'final', schedule_file)
            if match:
                stage = 'final'
            else:
                continue

        schedule = parse_schedule_file(schedule_file)
        if stage not in stage_schedules:
            stage_schedules[stage] = {}
        stage_schedules[stage].update(schedule)

    # Add schedule to participants
    updated_count = 0
    for participant in data['participants']:
        name = f"{participant['first_name']} {participant['last_name']}"
        normalized_name = normalize_name(name)

        for stage, schedule in stage_schedules.items():
            if stage in participant['stages']:
                # Try to match with normalized names (handles accents like ó -> o)
                matched_schedule = None
                if name in schedule:
                    # Exact match first
                    matched_schedule = schedule[name]
                else:
                    # Try normalized match
                    for schedule_name, schedule_data in schedule.items():
                        if normalize_name(schedule_name) == normalized_name:
                            matched_schedule = schedule_data
                            break

                if matched_schedule:
                    # Add schedule data to this stage
                    participant['stages'][stage]['date'] = matched_schedule['date']
                    participant['stages'][stage]['time_start'] = matched_schedule['time_start']
                    participant['stages'][stage]['time_stop'] = matched_schedule['time_stop']
                    updated_count += 1

    # Write updated JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Updated {json_path} with schedule information")
    print(f"Added schedule to {updated_count} participant-stage entries")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_schedules_chopin_2025.py <json_file> <schedule_file1> [schedule_file2] ...")
        print("Example: python extract_schedules_chopin_2025.py data/chopin_2025.json data/chopin-2025-stage1-2025-10-03.txt data/chopin-2025-stage1-2025-10-04.txt")
        sys.exit(1)

    json_file = sys.argv[1]
    schedule_files = sys.argv[2:]

    add_schedule_to_json(json_file, schedule_files)
