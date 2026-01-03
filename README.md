# Wealthsimple to Monarch CSV Converter

A Python tool that connects to your Wealthsimple account via the WS-API library, retrieves transaction and balance history, and exports them as CSV files formatted for Monarch Money import.

## Features

- Authenticates with Wealthsimple using secure credential storage (keyring)
- Retrieves all account transactions and balance history
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

The script will:
1. Prompt you for your Wealthsimple credentials (username, password, and TOTP if enabled)
2. Authenticate and retrieve your account data
3. Generate CSV files in the `output/` directory:
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
- Category (empty - you can categorize in Monarch)
- Account
- Original Statement
- Notes
- Amount (negative for debits, positive for credits)
- Tags (empty)

### Balance History CSV
- Date (MM/DD/YYYY)
- Amount (positive for assets, negative for liabilities)

## Security

- Credentials are stored securely using the system keyring
- Session tokens are persisted securely and reused to avoid repeated logins
- Never commit sensitive data or session tokens to the repository

## Requirements

- Python 3.7+
- ws-api library
- keyring library

## Testing

For manual testing instructions and validation, see [TESTING.md](TESTING.md).

You can validate exported CSV files using the validation utility:
```bash
python3 validate_csv.py output/*.csv
```

## License

[Add your license here]

