# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wealthsimple to Monarch CSV Converter — a Python CLI tool that authenticates with Wealthsimple via the `ws-api` library, retrieves transaction and balance history for selected accounts, and exports CSV files formatted for Monarch Money import with auto-categorization.

## Commands

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the converter (interactive — prompts for credentials, account selection)
python3 main.py

# Filter by date range
python3 main.py --start-date 2024-01-01
python3 main.py --start-date 2024-01-01 --end-date 2024-12-31

# Validate exported CSVs
python3 validate_csv.py output/*.csv        # specific files
python3 validate_csv.py                      # all files in output/
python3 validate_csv.py --output-dir output  # custom directory
```

There are no automated tests. See TESTING.md for manual testing procedures.

## Architecture

- **`main.py`** — Entry point. Handles authentication (with keyring session persistence and saved username via `.config.yaml`), fetches accounts, presents an interactive account selector (j/k navigation, enter to toggle, q to confirm), then fetches transactions (`ws.get_activities()`) and balance history (`ws.get_account_historical_financials()`) per account. Supports `--start-date`/`--end-date` for transactions (balance history always fetches full history). Writes per-account CSVs to `output/`.

- **`categories.py`** — Auto-categorization engine. Loads rules from `category_rules.yaml` (gitignored). Two rule types: `type_rules` match on transaction type/subtype (INTEREST, DIVIDEND, DIY_BUY, etc.), `merchant_rules` do case-insensitive keyword substring matching for credit card transactions. First match wins. Returns empty string for unrecognized transactions.

- **`category_rules.example.yaml`** — Template rules file with generic Canadian merchants. Copy to `category_rules.yaml` to enable categorization. The personal copy is gitignored.

- **`validate_csv.py`** — Standalone CSV validation against Monarch's format (column names/order, date format MM/DD/YYYY, amount format).

- **`.config.yaml`** — Stores last-used Wealthsimple username (gitignored).

## Key Data Formats

**Transactions CSV** columns (order matters for Monarch): `Date, Merchant, Category, Account, Original Statement, Notes, Amount, Tags`

**Balances CSV** columns: `Date, Amount`

Amounts: negative for debits, positive for credits. `DIY_BUY` transactions are always negative. The `amountSign` field from the API controls sign for other transaction types.

## Transaction Description Cleaning

Wealthsimple prepends prefixes to descriptions (e.g., `"Credit card purchase: "`, `"(Pending) Credit card refund: "`). These are stripped from both Merchant and Original Statement fields. Prefix matching is order-dependent — longer/more specific prefixes are checked first (see `prefixes_to_remove` list in `convert_transaction_to_monarch`).

## Gitignored Personal Files

- `category_rules.yaml` — personal category rules
- `.config.yaml` — saved username
- `output/` — exported CSV files

## Dependencies

- `ws-api` — Wealthsimple API client (provides `WealthsimpleAPI`, `WSAPISession`, `OTPRequiredException`, `LoginFailedException`)
- `keyring` — System keyring for secure credential/session storage (service name: `morsimple.wealthsimple`)
- `pyyaml` — YAML parser for category rules and config files
