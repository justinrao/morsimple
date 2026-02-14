# Wealthsimple to Monarch CSV Converter

A Python tool that connects to your Wealthsimple account via the WS-API library, retrieves transaction and balance history, and exports them as CSV files formatted for Monarch Money import.

## Features

- Authenticates with Wealthsimple using secure credential storage (keyring)
- Interactive account selector with keyboard navigation (j/k, arrow keys, enter to toggle, q to confirm)
- Auto-categorizes transactions using customizable YAML rules (type/subtype matching and merchant keyword matching)
- Date filtering with `--start-date` and `--end-date` options
- Remembers your username across sessions
- Exports separate CSV files per account in Monarch Money's required format
- Supports both transaction history and balance history exports

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd morsimple
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Install keyring (if not already installed):
```bash
pip3 install keyring
```

## Usage

Run the main script:
```bash
python3 main.py
```

With date filtering:
```bash
python3 main.py --start-date 2024-01-01
python3 main.py --start-date 2024-01-01 --end-date 2024-12-31
```

The script will:
1. Prompt you for your Wealthsimple credentials (username saved for next time, password, and TOTP if enabled)
2. Authenticate and retrieve your account data
3. Present an interactive account selector — choose individual accounts or "All"
4. Auto-categorize transactions using rules from `category_rules.yaml`
5. Generate CSV files in the `output/` directory:
   - `{account_number}_transactions.csv` - Transaction history
   - `{account_number}_balances.csv` - Balance history

## Importing into Monarch Money

### Transactions
1. Log in to your Monarch Money account
2. Navigate to the specific account
3. Click "Edit" and select "Import transactions"
4. Upload the corresponding `{account_number}_transactions.csv` file

### Balance History
1. Navigate to the account in Monarch Money
2. Click "Edit" and select "Import balance history"
3. Upload the corresponding `{account_number}_balances.csv` file

## CSV Format

### Transactions CSV
- Date (MM/DD/YYYY)
- Merchant
- Category (auto-filled from rules, or empty if no match)
- Account
- Original Statement
- Notes (includes transaction type and subtype)
- Amount (negative for debits, positive for credits)
- Tags (empty)

### Balance History CSV
- Date (MM/DD/YYYY)
- Amount (positive for assets, negative for liabilities)

## Auto-Categorization

Transactions are automatically categorized using rules defined in `category_rules.yaml`. To get started:

```bash
cp category_rules.example.yaml category_rules.yaml
```

Then customize `category_rules.yaml` with your own merchants. The file has two rule sections:

- **type_rules** — Match on transaction type (e.g., `INTEREST`, `DIY_BUY`) and optional subtype
- **merchant_rules** — Match credit card purchases by merchant name keyword (case-insensitive substring match)

Rules are evaluated top-to-bottom; first match wins. Your personal `category_rules.yaml` is gitignored so it stays private.

## Security

- Credentials are stored securely using the system keyring
- Session tokens are persisted securely and reused to avoid repeated logins
- Personal config (`.config.yaml`) and category rules (`category_rules.yaml`) are gitignored
- Never commit sensitive data or session tokens to the repository

## Requirements

- Python 3.7+
- ws-api library
- keyring library
- pyyaml library

## Testing

For manual testing instructions and validation, see [TESTING.md](TESTING.md).

You can validate exported CSV files using the validation utility:
```bash
python3 validate_csv.py output/*.csv
```

## License

This project is licensed under the [GPL-3.0](LICENSE).

