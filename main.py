#!/usr/bin/env python3
"""
Wealthsimple to Monarch CSV Converter

This script authenticates with Wealthsimple, retrieves account transactions
and balance history, and exports them as CSV files formatted for Monarch Money.
"""

import argparse
import csv
import json
import keyring
import os
import sys
import tty
import termios
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from ws_api import WealthsimpleAPI, OTPRequiredException, LoginFailedException, WSAPISession

from categories import load_rules, categorize_transaction


def read_key() -> str:
    """Read a single keypress, handling arrow keys and special keys."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # Escape sequence
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'up'
                elif ch3 == 'B':
                    return 'down'
            return 'escape'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_terminal_width() -> int:
    """Get terminal width, defaulting to 80."""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def interactive_select(items: List[str]) -> List[int]:
    """Interactive multi-select menu with cursor navigation.

    Controls: j/down = move down, k/up = move up, enter/space = toggle, q = confirm

    Returns list of selected indices (0-based, excluding the 'All' option).
    """
    cursor = 0
    # selected[0] = All, selected[1..n] = individual items
    selected = [False] * (len(items) + 1)
    total_lines = len(items) + 1  # +1 for "All"
    term_width = get_terminal_width()
    # Fixed number of output lines: menu items + blank + help
    num_lines = total_lines + 2
    CLEAR_LINE = '\x1b[2K'  # ANSI: erase entire line

    def render():
        lines = []
        for i in range(total_lines):
            arrow = '>' if i == cursor else ' '
            check = 'x' if selected[i] else ' '
            if i == 0:
                line = f"  {arrow} [{check}] 0. All"
            else:
                line = f"  {arrow} [{check}] {i:>2}. {items[i - 1]}"
            # Truncate to terminal width to prevent wrapping
            lines.append(line[:term_width])
        lines.append("")
        lines.append("  j/\u2193 down  k/\u2191 up  enter toggle  q confirm")
        return lines

    # Initial draw
    output = render()
    sys.stdout.write('\n'.join(output))
    sys.stdout.flush()

    while True:
        key = read_key()

        if key in ('j', 'down'):
            cursor = min(cursor + 1, total_lines - 1)
        elif key in ('k', 'up'):
            cursor = max(cursor - 1, 0)
        elif key in ('\r', '\n', ' '):
            if cursor == 0:
                # Toggle All
                new_state = not selected[0]
                selected = [new_state] * (len(items) + 1)
            else:
                selected[cursor] = not selected[cursor]
                # Update All: checked if all individual items are selected
                selected[0] = all(selected[1:])
        elif key == 'q':
            break
        elif key == 'escape':
            break
        else:
            continue

        # Move cursor up to top of menu, clear each line, and redraw
        sys.stdout.write(f'\x1b[{num_lines - 1}A\r')
        output = render()
        for i, line in enumerate(output):
            sys.stdout.write(f'{CLEAR_LINE}{line}')
            if i < len(output) - 1:
                sys.stdout.write('\n')
        sys.stdout.flush()

    # Move past the menu
    sys.stdout.write('\n')

    # If All or nothing selected, return all
    indices = [i - 1 for i in range(1, total_lines) if selected[i]]
    if not indices or selected[0]:
        return list(range(len(items)))
    return indices


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    return sanitized


def format_date_for_monarch(date_str: str) -> str:
    """Convert Wealthsimple date format to Monarch's MM/DD/YYYY format."""
    try:
        # Parse the ISO format date from Wealthsimple
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Format as MM/DD/YYYY
        return dt.strftime('%m/%d/%Y')
    except (ValueError, AttributeError) as e:
        print(f"Warning: Could not parse date '{date_str}': {e}")
        return date_str


def convert_transaction_to_monarch(transaction: dict, account_description: str, rules: dict) -> dict:
    """Convert a Wealthsimple transaction to Monarch CSV format."""
    # Parse the occurredAt date
    date = format_date_for_monarch(transaction.get('occurredAt', ''))
    
    # Extract merchant from description or use transaction type
    description = transaction.get('description', '')
    
    # Remove common prefixes that ws-api/Wealthsimple adds to descriptions
    # Order matters: check longer/more specific prefixes first
    prefixes_to_remove = [
        '(Pending) Credit card purchase: ',
        '(Pending) Credit card refund: ',
        'Credit card purchase: ',
        'Credit card refund: ',
        'Deposit: ',
        'Withdrawal: ',
        '(Pending) ',
    ]
    
    def remove_prefixes(text: str) -> str:
        """Remove common prefixes from transaction descriptions."""
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return text
    
    # Clean up merchant name by removing common prefixes
    merchant = description if description else transaction.get('type', 'Unknown')
    merchant = remove_prefixes(merchant)
    
    # Auto-categorize based on transaction type and merchant name
    category = categorize_transaction(
        tx_type=transaction.get('type', ''),
        sub_type=transaction.get('subType'),
        merchant=merchant,
        rules=rules,
    )
    
    # Account name
    account = account_description
    
    # Original statement - also cleaned of prefixes
    original_statement = remove_prefixes(description) if description else description
    
    # Notes include transaction type and subtype if available
    notes_parts = []
    if transaction.get('type'):
        notes_parts.append(f"Type: {transaction['type']}")
    if transaction.get('subType'):
        notes_parts.append(f"SubType: {transaction['subType']}")
    notes = ' | '.join(notes_parts) if notes_parts else ''
    
    # Amount: negative for debits, positive for credits
    amount_str = transaction.get('amount', '0')
    try:
        amount = float(amount_str)
        # If amountSign is 'negative', make it negative
        if transaction.get('amountSign') == 'negative':
            amount = -abs(amount)
        elif transaction.get('amountSign') == 'positive':
            amount = abs(amount)
        # Special handling for DIY_BUY transactions
        if transaction.get('type') == 'DIY_BUY':
            amount = -abs(amount)
    except (ValueError, TypeError):
        amount = 0.0
    
    # Tags are left empty
    tags = ''
    
    return {
        'Date': date,
        'Merchant': merchant,
        'Category': category,
        'Account': account,
        'Original Statement': original_statement,
        'Notes': notes,
        'Amount': f"{amount:.2f}",
        'Tags': tags
    }


def convert_balance_to_monarch(balance_data: dict) -> dict:
    """Convert Wealthsimple balance history to Monarch CSV format."""
    date = format_date_for_monarch(balance_data.get('date', ''))
    
    # Get net liquidation value
    net_liquidation = balance_data.get('netLiquidationValueV2') or {}
    if 'cents' in net_liquidation:
        amount = net_liquidation['cents'] / 100.0
    elif 'amount' in net_liquidation:
        try:
            amount = float(net_liquidation['amount'])
        except (ValueError, TypeError):
            amount = 0.0
    else:
        amount = 0.0
    
    return {
        'Date': date,
        'Amount': f"{amount:.2f}"
    }


def export_transactions_csv(transactions: list, account_description: str, account_number: str, output_dir: Path, rules: dict):
    """Export transactions to CSV file in Monarch format."""
    if not transactions:
        print(f"  No transactions found for account {account_number}")
        return
    
    # Sanitize account number for filename
    safe_account_number = sanitize_filename(account_number)
    filename = output_dir / f"{safe_account_number}_transactions.csv"
    
    # Convert transactions to Monarch format
    monarch_transactions = [
        convert_transaction_to_monarch(tx, account_description, rules)
        for tx in transactions
    ]
    
    # Write CSV file
    fieldnames = ['Date', 'Merchant', 'Category', 'Account', 'Original Statement', 'Notes', 'Amount', 'Tags']
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(monarch_transactions)
    
    print(f"  Exported {len(monarch_transactions)} transactions to {filename}")


def export_balances_csv(balances: list, account_number: str, output_dir: Path):
    """Export balance history to CSV file in Monarch format."""
    if not balances:
        print(f"  No balance history found for account {account_number}")
        return
    
    # Sanitize account number for filename
    safe_account_number = sanitize_filename(account_number)
    filename = output_dir / f"{safe_account_number}_balances.csv"
    
    # Convert balances to Monarch format
    monarch_balances = [
        convert_balance_to_monarch(bal)
        for bal in balances
    ]
    
    # Write CSV file
    fieldnames = ['Date', 'Amount']
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(monarch_balances)
    
    print(f"  Exported {len(monarch_balances)} balance records to {filename}")


def authenticate_wealthsimple(keyring_service_name: str = "morsimple.wealthsimple") -> Tuple[WealthsimpleAPI, str]:
    """Authenticate with Wealthsimple and return API object and username."""
    # Define function to persist session
    def persist_session_fct(sess, uname):
        keyring.set_password(f"{keyring_service_name}.{uname}", "session", sess)
    
    # Load saved username as default
    config_file = Path(__file__).parent / '.config.yaml'
    saved_username = ''
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
            saved_username = config.get('username', '')

    # Prompt for username with saved default
    if saved_username:
        username = input(f"Wealthsimple username (email) [{saved_username}]: ").strip()
        if not username:
            username = saved_username
    else:
        username = input("Wealthsimple username (email): ").strip()

    # Save username for next time
    with open(config_file, 'w') as f:
        yaml.dump({'username': username}, f)
    session = keyring.get_password(f"{keyring_service_name}.{username}", "session")
    
    if session:
        try:
            session = WSAPISession.from_json(session)
            print("Found existing session, attempting to reuse...")
        except Exception as e:
            print(f"Could not load existing session: {e}")
            session = None
    
    # If no valid session, login
    if not session:
        password = None
        otp_answer = None
        
        while True:
            try:
                if not password:
                    password = input("Password: ").strip()
                
                WealthsimpleAPI.login(username, password, otp_answer, persist_session_fct=persist_session_fct)
                # Login successful, get the session
                session_json = keyring.get_password(f"{keyring_service_name}.{username}", "session")
                if session_json:
                    session = WSAPISession.from_json(session_json)
                break
            except OTPRequiredException:
                otp_answer = input("TOTP code: ").strip()
            except LoginFailedException as e:
                print(f"Login failed: {e}")
                print("Please try again.")
                username = input("Wealthsimple username (email): ").strip()
                password = None
                otp_answer = None
    
    # Create API object from session
    ws = WealthsimpleAPI.from_token(session, persist_session_fct, username)
    return ws, username


def parse_date(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.")


def main():
    """Main function to fetch data and export CSVs."""
    parser = argparse.ArgumentParser(description="Wealthsimple to Monarch CSV Converter")
    parser.add_argument('--start-date', type=parse_date, default=None,
                        help='Start date for transactions/balances (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=parse_date, default=None,
                        help='End date for transactions/balances (YYYY-MM-DD)')
    args = parser.parse_args()

    print("Wealthsimple to Monarch CSV Converter")
    print("=" * 50)

    if args.start_date:
        print(f"Start date: {args.start_date.strftime('%Y-%m-%d')}")
    if args.end_date:
        print(f"End date: {args.end_date.strftime('%Y-%m-%d')}")

    # Load category rules
    rules = load_rules()

    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    try:
        # Authenticate
        print("\nAuthenticating with Wealthsimple...")
        ws, username = authenticate_wealthsimple()
        print("Authentication successful!")

        # Fetch accounts
        print("\nFetching accounts...")
        accounts = ws.get_accounts()
        print(f"Found {len(accounts)} account(s)")

        # Interactive account selection
        print("\nSelect accounts to export:")
        account_labels = []
        for a in accounts:
            desc = a.get('description', '')
            number = a.get('number', a['id'])
            currency = a.get('currency', 'CAD')
            if desc and desc != number:
                account_labels.append(f"{desc} ({number}) [{currency}]")
            else:
                account_labels.append(f"{number} [{currency}]")
        selected_indices = interactive_select(account_labels)
        accounts = [accounts[i] for i in selected_indices]

        print(f"Processing {len(accounts)} account(s)...")

        # Process each account
        for account in accounts:
            account_id = account['id']
            account_number = account.get('number', account_id)
            account_description = account.get('description', account_number)
            currency = account.get('currency', 'CAD')

            print(f"\nProcessing account: {account_description} ({account_number})")

            # Fetch transactions
            try:
                print("  Fetching transactions...")
                transactions = ws.get_activities(
                    account_id,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    load_all=True,
                )
                # Reverse to get chronological order (oldest first)
                if transactions:
                    transactions.reverse()
                export_transactions_csv(transactions, account_description, account_number, output_dir, rules)
            except Exception as e:
                print(f"  Error fetching transactions: {e}")

            # Fetch balance history
            try:
                print("  Fetching balance history...")
                balances = ws.get_account_historical_financials(account_id, currency)
                export_balances_csv(balances, account_number, output_dir)
            except Exception as e:
                print(f"  Error fetching balance history: {e}")

        print("\n" + "=" * 50)
        print("Export complete! CSV files are in the 'output' directory.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

