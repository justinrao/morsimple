# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wealthsimple to Monarch CSV Converter — a Python CLI tool that authenticates with Wealthsimple via the `ws-api` library, retrieves transaction and balance history for all accounts, and exports CSV files formatted for Monarch Money import.

## Commands

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the converter (interactive — prompts for credentials)
python3 main.py

# Validate exported CSVs
python3 validate_csv.py output/*.csv        # specific files
python3 validate_csv.py                      # all files in output/
python3 validate_csv.py --output-dir output  # custom directory
```

There are no automated tests. See TESTING.md for manual testing procedures.

## Architecture

- **`main.py`** — Entry point. Handles Wealthsimple authentication (with keyring-based session persistence), fetches accounts via `ws.get_accounts()`, then for each account fetches transactions (`ws.get_activities()`) and balance history (`ws.get_account_historical_financials()`). Converts each to Monarch format and writes per-account CSVs to `output/`. Supports `--start-date` and `--end-date` flags.

- **`categories.py`** — Auto-categorization engine. Loads rules from `category_rules.yaml` (gitignored, personal). Maps transactions to Monarch categories using type-based rules (INTEREST, DIVIDEND, etc.) and keyword-based merchant matching for credit card transactions. Returns empty string for unrecognized transactions.

- **`category_rules.example.yaml`** — Template rules file. Copy to `category_rules.yaml` to enable categorization. Contains `type_rules` (matched on transaction type/subtype) and `merchant_rules` (case-insensitive keyword substring matching, first match wins).

- **`validate_csv.py`** — Standalone validation utility. Checks exported CSVs against Monarch's expected format (column names, column order, date format MM/DD/YYYY, amount format).

## Key Data Formats

**Transactions CSV** columns (order matters for Monarch): `Date, Merchant, Category, Account, Original Statement, Notes, Amount, Tags`

**Balances CSV** columns: `Date, Amount`

Amounts: negative for debits, positive for credits. `DIY_BUY` transactions are always negative. The `amountSign` field from the API controls sign for other transaction types.

## Transaction Description Cleaning

Wealthsimple prepends prefixes to descriptions (e.g., `"Credit card purchase: "`, `"(Pending) Credit card refund: "`). These are stripped from both Merchant and Original Statement fields. Prefix matching is order-dependent — longer/more specific prefixes are checked first (see `prefixes_to_remove` list in `convert_transaction_to_monarch`).

## Dependencies

- `ws-api` — Wealthsimple API client (provides `WealthsimpleAPI`, `WSAPISession`, `OTPRequiredException`, `LoginFailedException`)
- `keyring` — System keyring for secure credential/session storage (service name: `morsimple.wealthsimple`)
- `pyyaml` — YAML parser for category rules file
