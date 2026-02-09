# UV Migration Guide

## What Changed

This project has been migrated from using `pip` with `requirements.txt` to using **uv** package manager.

### Key Changes:

1. **Updated `pyproject.toml`**
   - Added all dependencies from `requirements.txt` to the `dependencies` section
   - Added optional dev dependencies for linting and formatting (pytest, ruff, black)
   - Added tool configurations for ruff and black

2. **Generated `uv.lock`**
   - This file locks all dependency versions for reproducible installations
   - Should be committed to version control

3. **Updated `README.md`**
   - Changed installation instructions to use `uv sync`
   - Updated usage examples to use `uv run`

4. **`.venv` directory**
   - uv manages a virtual environment at `.venv/`
   - This replaces the need for manual `python -m venv` setup

## Installation & Usage

### First Time Setup

```bash
cd election_69_analyzer
uv sync
```

### Running Scripts

```bash
# Run the main script
uv run python main.py

# Run the election scraper
uv run python scripts/election_scraper.py

# Run the comparer
uv run python scripts/mp_pl_comparer.py
```

### Installing New Dependencies

```bash
uv add package_name
```

### Installing Dev Dependencies

```bash
uv add --dev pytest ruff black
```

### Updating Dependencies

```bash
uv lock --upgrade
```

## Benefits of UV

- **Faster** - Written in Rust, much faster than pip
- **Simpler** - Single tool for all package management tasks
- **Reproducible** - Lock file ensures consistent installations across environments
- **Cleaner** - Better error messages and output
- **Modern** - Uses PEP 621 (pyproject.toml) as the single source of truth

## Migration Checklist

- [x] Updated `pyproject.toml` with all dependencies
- [x] Generated `uv.lock` file
- [x] Updated `README.md` with uv instructions
- [x] Tested basic functionality with `uv run`
- [x] Verified virtual environment creation
- [x] Scripts work with uv

## Notes

- `requirements.txt` can still be kept for reference but is now redundant
- `.venv` directory is managed by uv and should not be manually modified
- All development should use `uv run` to ensure the correct environment
