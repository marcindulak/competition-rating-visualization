#!/usr/bin/env python3
"""Extract Chopin Competition 2025 jury scores from PDF and convert to JSON format."""

import json
from typing import Any

import pdfplumber

from tools import extract_chopin_data, logger, parse_score


# Juror names hardcoded due to PDF text encoding issues (reversed, fragmented across cells).
JUROR_NAMES = [
    "Garrick Ohlsson",
    "John Allison",
    "Yulianna Avdeeva",
    "Michel Beroff",
    "Sa Chen",
    "Dang Thai Son",
    "Akiko Ebi",
    "Nelson Goerner",
    "Krzysztof Jabłoński",
    "Kevin Kenner",
    "Momo Kodama",
    "Robert McDonald",
    "Piotr Paleczny",
    "Ewa Pobłocka",
    "K. Popowa-Zydroń",
    "John Rink",
    "Wojciech Świtała"
]


def process_chopin_2025(page: pdfplumber.pdf.Page, expected_stage: str) -> list[dict[str, Any]]:
    """
    Extract scores from a single PDF page for 2025 Chopin Competition.

    Args:
        page: PDF page object
        expected_stage: Expected stage identifier for this page

    Returns:
        List of participant score entries
    """
    table_settings = {
        'vertical_strategy': 'text',
        'horizontal_strategy': 'text',
        'intersection_tolerance': 3,
    }

    tables = page.extract_tables(table_settings)

    if not tables:
        logger.info(f"  No tables found")
        return []

    table = tables[0]

    if len(table) < 2:
        return []

    logger.info(f"  Table has {len(table)} rows, {len(table[0])} columns")

    entries = []
    i = 0

    while i < len(table):
        row = table[i]

        if not row or len(row) < 18:
            i += 1
            continue

        row_text = ' '.join(str(c) for c in row if c).lower()

        if 'punktacja' in row_text:
            import re

            nr_str = str(row[0]).strip() if row[0] else ""
            cell1 = str(row[1]).strip() if row[1] else ""
            cell2 = str(row[2]).strip() if row[2] else ""

            nr = None
            first_name = ""
            last_name = ""
            scores_start_col = 4

            if 'punktacja' in cell2.lower():
                match = re.match(r'^(\d+)', nr_str)
                if match:
                    nr = int(match.group(1))
                    first_name = nr_str[len(match.group(1)):].strip()
                    last_name = cell1
                    scores_start_col = 3
            else:
                nr_parts = nr_str.split('\n')
                if nr_parts and nr_parts[0].isdigit():
                    nr = int(nr_parts[0])
                    first_name = cell1
                    last_name = cell2

            original_scores = {}
            corrected_final = None

            if nr is not None and first_name and last_name:
                for j, juror in enumerate(JUROR_NAMES):
                    col_idx = scores_start_col + j
                    if col_idx < len(row):
                        original_scores[juror] = parse_score(row[col_idx])
                    else:
                        original_scores[juror] = None

                final_cell = str(row[21]).strip() if len(row) > 21 and row[21] else ""
                final_parts = final_cell.split('\n')

                # Only extract corrected final score; original average was not officially provided
                if len(final_parts) >= 2:
                    corrected_final = parse_score(final_parts[1])
                elif len(final_parts) == 1:
                    corrected_final = parse_score(final_parts[0])

            corrected_scores: dict[str, float | str | None] = {}

            if i + 1 < len(table):
                next_row = table[i + 1]
                next_row_text = ' '.join(str(c) for c in next_row if c).lower()

                if 'p. kor' in next_row_text or 'p.kor' in next_row_text:
                    for j, juror in enumerate(JUROR_NAMES):
                        col_idx = scores_start_col + j
                        if col_idx < len(next_row):
                            if original_scores.get(juror) == 's':
                                corrected_scores[juror] = 's'
                            else:
                                cell_value = str(next_row[col_idx]).strip() if next_row[col_idx] else ""

                                if col_idx > 4:
                                    prev_cell = str(next_row[col_idx - 1]).strip() if next_row[col_idx - 1] else ""
                                    parts = prev_cell.split()
                                    if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 1:
                                        cell_value = parts[-1] + cell_value

                                corrected_scores[juror] = parse_score(cell_value)
                        else:
                            corrected_scores[juror] = None
                    i += 1

            if first_name and last_name:
                entry = {
                    "nr": nr,
                    "first_name": first_name,
                    "last_name": last_name,
                    "stage": expected_stage,
                    "original": {
                        "juror_scores": original_scores,
                        "final_score": None  # Uncorrected average not officially provided
                    },
                    "corrected": {
                        "juror_scores": corrected_scores,
                        "final_score": corrected_final
                    }
                }

                entries.append(entry)

        i += 1

    return entries


def main() -> None:
    """Extract scores from all stages of the 2025 competition."""
    pdf_path = "data/475810_Chopin_Competition_2025_scores.pdf"

    stage_page_map = {
        1: "stage1", 2: "stage1", 3: "stage1",
        4: "stage2", 5: "stage2",
        6: "stage3",
        7: "final"
    }

    output = extract_chopin_data(pdf_path, process_chopin_2025, stage_page_map, 2025, JUROR_NAMES)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
