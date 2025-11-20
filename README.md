> Co-Authored-By: Claude

# Functionality overview

Interactive visualization of competition jury ratings with timeline and heatmap views.

Available at https://marcindulak.github.io/competition-rating-visualization.

It is designed to accommodate any competition judged by multiple jurors in multiple stages,
and currently contains the following competitions:
- **2025 Chopin Competition**

> **Note**: This project is not associated with the Fryderyk Chopin Institute.

## Features

### Timeline View

The timeline view shows pianist performances in chronological order with their jury ratings, with error bars showing the spread of jury opinions for each performance. This interactive visualization is inspired by Hans Rosling's ["The best stats you've ever seen"](https://www.youtube.com/watch?v=hVimVzgtD6w) talk.

**Visualization elements:**
- **Participant circles**: Each filled circle represents a pianist's performance. The circle's red color shade indicates the average rating. The circle's size is proportional to the participant's age (when age data is available for all participants).
- **Standard deviation bars**: Vertical lines extending above and below each completed performance show ±1 standard deviation of the juror ratings, visualizing how much the jury opinions varied.
- **Extreme juror ratings**: Two empty outline circles appear for the last finished performance, marking the most extreme outlier ratings from the jury - one showing the lowest outlier score and one showing the highest outlier score.

### Heatmap View

In the heatmap view each cell shows the juror's rating and the difference from that participant's average in parentheses, e.g., `18.00 (+1.00)` means the juror rated 1.00 points above the participant's average.
The cells are interactive, click on rating cells to see original and corrected ratings across all stages for that participant-juror pair, including the "Wrt avg" column showing the deviation from participant average per stage

Participant Sorting:

- **Default**: Sort by participant number (competition order)
- **Name**: Alphabetical by last name
- **Mean**: Sort by average rating across all jurors (descending, left to right)
- **SD**: Sort by standard deviation of ratings (descending, left to right) - identifies participants with most disagreement among jurors

Juror Sorting:

- **Default**: Original juror order from competition
- **Name**: Alphabetical by last name
- **Mean**: Sort by average rating given (descending, top to bottom) - identifies most generous/strict jurors
- **SD**: Sort by standard deviation of ratings given (descending, top to bottom) - identifies jurors with most variation in rating
- **Wrt avg**: Sort by Euclidean distance to participant averages (ascending, top to bottom) - identifies jurors closest to consensus. Calculate the Euclidean distance between each juror's ratings and the participant averages. Jurors with smaller distances are more aligned with the overall jury consensus.

# Usage examples

## Local development

Run a local web server to serve the application (required for CORS to work):

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Then open http://localhost:8000 in your browser.

## Adding a New Competition

The instructions below describe how to add ratings from a future competition.

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

2. Clone this repository:

   ```
   git clone https://github.com/USER/chopin-competition-rating-visualization
   cd chopin-competition-rating-visualization
   ```

3. Install Python dependencies:

   ```
   uv sync --frozen
   ```

4. Set appropriate values in the `preprocessing/extract_scores_chopin_2025.py` script:
   - Update `JUROR_NAMES` list (if PDF encoding issues persist)
   - Update `pdf_path` to point to the new PDF
   - Update `stage_page_map` to match the PDF structure
   - Adjust table extraction logic if PDF format changed

5. Extract ratings to raw JSON:

   ```
   uv run preprocessing/extract_scores_chopin_2025.py > data/chopin_2025.raw.json
   ```

6. Obtain performance schedules from the competition website and save as text files with naming pattern `data/chopin-2025-stageN-YYYY-MM-DD.txt`

7. Copy raw ratings to working file and add schedule information:

   ```
   /bin/cp -f data/chopin_2025.raw.json data/chopin_2025.json
   uv run preprocessing/extract_schedules_chopin_2025.py data/chopin_2025.json data/chopin-2025-*.txt
   ```

8. (Optional) Extract competitor ages from biography pages to enable age-based circle sizing in timeline view:

   ```
   uv run preprocessing/extract_competitors_age_chopin_2025.py
   ```

   This script reads HTML biography files from `data/www.chopincompetition.pl/competitors/`, extracts birth dates and calculates ages at competition date, updates participant names to include proper diacritics, and adds the age field to each participant in the JSON. If all stage 1 participants have ages, the timeline view will scale circle sizes proportionally to age.

9. Manually verify the extracted data, especially:
    - Participant number, name, and age
    - Student markers ('s')
    - Stages and final ratings (often have different table structures)
    - Performance dates and times

9. Data is automatically loaded from `data/chopin_2025.json`:
    - No manual updates to `index.html` are needed
    - The application automatically discovers available stages and populates the competition selector
    - When deployed to GitHub Pages, the JSON file will be served from the same domain (CORS-compatible)

# Running tests

## Test data extraction from pdf

```
bash scripts/test_chopin_2025.sh
```

## Type checking

Run mypy static type checking:

```
uv run --frozen python -m mypy preprocessing
```

# Implementation overview

All object sizes are controlled through a single `body` font-size property (8px desktop, 4px mobile landscape), with all dimensions specified in `em` units to scale proportionally.

The frontend is a static HTML application with embedded JavaScript, hosted on GitHub Pages.
PDF files are saved under the `data` folder and processed using Python scripts in the `preprocessing` folder.
The output JSON is loaded from `data/chopin_2025.json` at runtime via the Fetch API, which works on GitHub Pages since the JSON is served from the same domain.

# Abandoned ideas

- **PyScript/matplotlib**: Discarded in favor of vanilla JavaScript for better performance and simplicity
- **Embedded JSON in index.html**: Initially embedded for CORS compatibility when opening with `file://`, but this created maintainability issues and made the HTML file very large.
- **Automatic juror name extraction**: PDF text encoding issues (reversed, fragmented text) made hardcoding necessary
- **Converting 's' to null**: Kept as string to preserve student-teacher relationships in modals
- **Analysis of jurors rating variability** - Performed in [Chopin competition 2025: detailed scoring](https://euge.ca/chopin-2025) and discussed in [What the data reveal about the 2025 Chopin Competition](https://www.youtube.com/watch?v=AzsruBUVdfA)
- **Analysis of results dependence on voting scheme** - Performed in [Voting analysis for the 19th Chopin competition](https://kencaldeira.com/2025/11/chopin-voting-analysis/)
