#!/bin/bash
set -eo pipefail

PDF_URL="https://storage.nifc.pl/web_files/_plik/file_manager_pmp/files/475810_Chopin_Competition_2025_scores.pdf"
PDF_PATH="data/$(basename "$PDF_URL")"

if [ ! -f "$PDF_PATH" ]; then
    echo "Downloading PDF..."
    curl -L -o "$PDF_PATH" "$PDF_URL"
fi

echo "Extracting ratings from PDF..."
uv run --frozen python preprocessing/extract_scores_chopin_2025.py > chopin_2025.raw.json

echo "Comparing extracted JSON with committed version..."
diff data/chopin_2025.raw.json chopin_2025.raw.json

echo "Checking for schedule files..."
if ls data/chopin-2025-*.txt 1> /dev/null 2>&1; then
    echo "Adding schedule information..."
    /bin/cp -f chopin_2025.raw.json chopin_2025.json
    uv run --frozen python preprocessing/extract_schedules_chopin_2025.py chopin_2025.json data/chopin-2025-*.txt
else
    echo "No schedule files found, skipping schedule extraction (using ratings only)"
fi

echo "Test passed: extracted JSON matches committed version"
