# AI Coding Agent Instructions for election_69_analyzer

## Project Overview
Thai Election 69 Correlative Analyzer - A data scraping and statistical analysis tool investigating correlations between Constituency MP candidate numbers and Party List rankings. Educational/analytical project inspired by Khajochi's blog observations.

## Architecture & Data Flow

### Two-Phase Pipeline
1. **Data Collection** (`scripts/election_scraper.py`): Scrapes Thai PBS unofficial election APIs
   - Fetches MP (constituency) data and PL (party-list) data for area codes 1001-9999
   - Uses intelligent province-skipping: when an area returns 403, jumps to next XX01 block
   - Stores JSON files wrapped in format: `{"area_code": "1001", "entries": [...]}`
   
2. **Analysis** (`scripts/mp_pl_comparer.py`): Correlates MP winner candidate numbers with top-7 PL party codes
   - Extracts MP number from `candidateCode` (e.g., CANDIDATE-MP-100105 → "05")
   - Compares against last 2 digits of party codes ranked 1-7
   - **Excludes parties 06 and 09** by design (known statistical bias)
   - Outputs matches grouped by party with counts

### Data Structure
```
data/
├── mp/       # Constituency results {area_code, entries: [{candidateCode, partyCode, ...}]}
└── pl/       # Party-list results   {area_code, entries: [{partyCode, rank, ...}]}
```

## Critical Implementation Details

### Timestamp Versioning (election_scraper.py)
- API endpoints require `TIMESTAMP_VERSION` (e.g., "2026-02-09-19-58-02-921")
- Update this when fetching fresh data - check Thai PBS site for current version
- Configured as module constant, not CLI argument

### Comparison Logic (mp_pl_comparer.py)
- MP number extraction: `CANDIDATE-MP-{area_code}` prefix + last 2 digits
- PL party code comparison: uses only last 2 digits (right-padded with zeros)
- Party filter: hardcoded `if last_2 in ["06", "09"]` skip logic
- Only compares top 7 PL ranks, ignores rank 8+

### Error Handling Patterns
- `fetch_json_data()` returns `None` for 403 (area invalid), `"ERROR"` for exceptions
- Main loop uses this to trigger province jumps without losing data
- File operations wrapped in try-except with print statements (no logging framework)

## Development Workflow

### Environment Setup
```bash
# Uses uv package manager (recently migrated from pip)
uv sync                    # Install dependencies
uv run python main.py      # Run any script
uv add <package>           # Add dependency
```

### Project Structure
- `pyproject.toml`: Single source of truth for dependencies (no requirements.txt needed)
- `uv.lock`: Reproducible dependency lock file
- `main.py`: Placeholder/entry point
- `scripts/`: Two production scripts, never imported as modules
- `data/`: Output directory, gitignored

### Testing Considerations
- No test suite exists (educational project)
- Manual validation: run scraper, verify JSON in data/ directory, run comparer
- Comparer validates input: checks for missing corresponding MP/PL files

## Common Tasks & Patterns

### Adding New Analysis
- New analyses should follow comparer pattern: load JSON files, iterate entries, aggregate results
- Add to `scripts/` directory, run with `uv run python scripts/new_script.py`
- Always validate area_code extraction logic before deploying

### Updating Scraper
- Change `TIMESTAMP_VERSION` constant when API version updates
- Modify area code ranges in main loop if scope changes
- Keep HTTP headers (User-Agent, Referer) valid - API may reject missing ones

### Code Style
- 100 character line length (configured in pyproject.toml for ruff/black)
- Python 3.12.1+ (check `.python-version` file)
- Dev tools available: ruff (lint), black (format) via optional dependencies
- No import statements for project modules - scripts are standalone files

## Important Gotchas
1. **API Endpoint Requires Timestamp**: Forgetting to update `TIMESTAMP_VERSION` causes all requests to fail silently
2. **Area Code Extraction Bug Risk**: String slicing logic in both scraper (save) and comparer (extract) must match exactly
3. **Missing Files**: Comparer silently skips areas without both MP and PL files
4. **Province Jump Logic**: Relies on 403 response detection - API behavior change could break it
5. **Party Filtering**: Hard-coded "06" and "09" exclusions - update in comparer if requirements change

## Data Quality Notes
- Results are **unofficial** from Thai PBS (as-is, no validation)
- Analysis excludes 2 parties by design (mitigation for known bias)
- Some area codes are intentionally invalid - province jump handles this
- No data cleaning pipeline (raw JSON stored as-is)
