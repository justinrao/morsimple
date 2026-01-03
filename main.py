#!/usr/bin/env python3
"""
Wealthsimple to Monarch CSV Converter

This script authenticates with Wealthsimple, retrieves account transactions
and balance history, and exports them as CSV files formatted for Monarch Money.
"""

import csv
import json
import keyring
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Tuple

from ws_api import WealthsimpleAPI, OTPRequiredException, LoginFailedException, WSAPISession


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


def convert_transaction_to_monarch(transaction: dict, account_description: str) -> dict:
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
    
    # Category is left empty for user to categorize in Monarch
    category = ''
    
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
    net_liquidation = balance_data.get('netLiquidationValueV2', {})
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


def export_transactions_csv(transactions: list, account_description: str, account_number: str, output_dir: Path):
    """Export transactions to CSV file in Monarch format."""
    if not transactions:
        print(f"  No transactions found for account {account_number}")
        return
    
    # Sanitize account number for filename
    safe_account_number = sanitize_filename(account_number)
    filename = output_dir / f"{safe_account_number}_transactions.csv"
    
    # Convert transactions to Monarch format
    monarch_transactions = [
        convert_transaction_to_monarch(tx, account_description)
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
    
    # Try to get existing session
    username = input("Wealthsimple username (email): ").strip()
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


def main():
    """Main function to fetch data and export CSVs."""
    print("Wealthsimple to Monarch CSV Converter")
    print("=" * 50)
    
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
                transactions = ws.get_activities(account_id)
                # Reverse to get chronological order (oldest first)
                if transactions:
                    transactions.reverse()
                export_transactions_csv(transactions, account_description, account_number, output_dir)
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

