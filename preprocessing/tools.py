"""Common utility functions for Chopin Competition score extraction."""

import json
import logging
import sys
from collections.abc import Callable
from typing import Any

import pdfplumber

logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)


def parse_score(score_str: str | None) -> float | str | None:
    """
    Parse score from string, handling special cases.

    Args:
        score_str: String containing score (number, 's', 'ss', etc.)

    Returns:
        Float score, 's' for student marker, or None if empty/invalid
    """
    if not score_str:
        return None

    score_str = str(score_str).strip()

    if not score_str:
        return None

    if 's' in score_str.lower() and not any(c.isdigit() for c in score_str):
        return 's'

    score_str_clean = score_str.split()[0].replace(',', '.')

    try:
        score_val = float(score_str_clean)
        return score_val if score_val != 0.0 else 0.0
    except ValueError:
        return None


def extract_stage_from_title(title: str) -> str | None:
    """
    Extract stage identifier from page title.

    Args:
        title: Page title text (e.g., "XIX Międzynarodowy Konkurs im. Fryderyka Chopina – punkty w 1. etapie")

    Returns:
        Stage identifier ('stage1', 'stage2', 'stage3', 'final') or None
    """
    title_lower = title.lower()

    if '1. etap' in title_lower or '1st stage' in title_lower:
        return 'stage1'
    elif '2. etap' in title_lower or '2nd stage' in title_lower:
        return 'stage2'
    elif '3. etap' in title_lower or '3rd stage' in title_lower:
        return 'stage3'
    elif 'finał' in title_lower or 'final' in title_lower:
        return 'final'

    return None


def extract_jurors_from_header(header_row: list[Any]) -> list[str]:
    """
    Extract juror names from table header row.

    Args:
        header_row: First row of table containing juror names

    Returns:
        List of juror names (columns between participant info and final score)
    """
    jurors = []

    for i, cell in enumerate(header_row):
        if i < 3:
            continue

        cell_str = str(cell).strip() if cell else ""

        if not cell_str:
            continue

        if 'wynik' in cell_str.lower() or 'score' in cell_str.lower():
            break

        jurors.append(cell_str)

    return jurors


def parse_participant_row(row: list[Any], jurors: list[str], row_type: str) -> dict[str, Any] | None:
    """
    Parse a single row of participant scores.

    Args:
        row: Table row data
        jurors: List of juror names (from header)
        row_type: 'original' or 'corrected'

    Returns:
        Dictionary with participant data or None if invalid row
    """
    if not row or len(row) < 4:
        return None

    nr_str = str(row[0]).strip() if row[0] else ""
    first_name = str(row[1]).strip() if row[1] else ""
    last_name = str(row[2]).strip() if row[2] else ""

    if not nr_str or not first_name or not last_name:
        return None

    if not nr_str.isdigit():
        return None

    juror_scores: dict[str, float | str | None] = {}
    for i, juror in enumerate(jurors):
        cell_index = 3 + i
        if cell_index >= len(row):
            juror_scores[juror] = None
        else:
            juror_scores[juror] = parse_score(row[cell_index])

    final_score = parse_score(row[-1])

    return {
        "nr": int(nr_str),
        "first_name": first_name,
        "last_name": last_name,
        "row_type": row_type,
        "juror_scores": juror_scores,
        "final_score": final_score
    }


def extract_chopin_data(pdf_path: str, process_chopin: Callable[[pdfplumber.pdf.Page, str], list[dict[str, Any]]], stage_page_map: dict[int, str], competition_year: int, jurors: list[str]) -> dict[str, Any]:
    """
    Extract Chopin Competition score data from PDF using year-specific processing function.

    Args:
        pdf_path: Path to the PDF file
        process_chopin: Function that processes a page and returns list of entries
        stage_page_map: Mapping of page numbers to stage identifiers
        competition_year: Year of the competition
        jurors: List of juror names

    Returns:
        Dictionary with competition data ready for JSON output
    """
    all_entries: list[dict[str, Any]] = []

    with pdfplumber.open(pdf_path) as pdf:
        logger.info(f"Processing {len(pdf.pages)} pages from {pdf_path}")

        for page_num in range(1, min(len(pdf.pages) + 1, max(stage_page_map.keys()) + 1)):
            if page_num not in stage_page_map:
                continue

            logger.info(f"Page {page_num} ({stage_page_map[page_num]}):")
            page = pdf.pages[page_num - 1]
            entries = process_chopin(page, stage_page_map[page_num])

            if entries:
                logger.info(f"  Extracted {len(entries)} participants")
                all_entries.extend(entries)

    participants_by_name: dict[str, dict[str, Any]] = {}

    for entry in all_entries:
        key = f"{entry['first_name']} {entry['last_name']}"

        if key not in participants_by_name:
            participants_by_name[key] = {
                "nr": entry["nr"],
                "first_name": entry["first_name"],
                "last_name": entry["last_name"],
                "stages": {}
            }

        stage = entry["stage"]
        participants_by_name[key]["stages"][stage] = {
            "original": entry["original"],
            "corrected": entry["corrected"]
        }

    output = {
        "competition_year": competition_year,
        "jurors": jurors,
        "participants": list(participants_by_name.values())
    }

    logger.info(f"\nTotal unique participants: {len(participants_by_name)}")
    logger.info(f"Total jurors: {len(jurors)}")

    return output
