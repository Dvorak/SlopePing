# Ski Coach Checker

A small Python automation project for checking ski coach availability or status.

## Project structure

- `README.md` — project overview
- `.gitignore` — files to ignore in git
- `requirements.txt` — Python dependencies
- `.env.example` — example environment variables
- `prompts/` — step-by-step task descriptions for the project

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment values:
   ```bash
   cp .env.example .env
   ```

## Notes

This repository is organized around task prompts for bootstrapping the project, implementing login and scraping, adding Telegram notifications, and documenting job scheduling.