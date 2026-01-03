#!/usr/bin/env python3
"""
CSV Validation Utility for Monarch Money Format

This script validates that exported CSV files conform to Monarch Money's
required format for transaction and balance history imports.
"""

import csv
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


def validate_date_format(date_str: str) -> Tuple[bool, str]:
    """Validate that date is in MM/DD/YYYY format."""
    pattern = r'^\d{2}/\d{2}/\d{4}$'
    if not re.match(pattern, date_str):
        return False, f"Date '{date_str}' is not in MM/DD/YYYY format"
    
    # Additional validation: check if it's a valid date
    try:
        parts = date_str.split('/')
        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
        if month < 1 or month > 12:
            return False, f"Invalid month: {month}"
        if day < 1 or day > 31:
            return False, f"Invalid day: {day}"
        if year < 1900 or year > 2100:
            return False, f"Year {year} seems unreasonable"
    except (ValueError, IndexError) as e:
        return False, f"Could not parse date: {e}"
    
    return True, ""


def validate_amount_format(amount_str: str) -> Tuple[bool, str]:
    """Validate that amount is a properly formatted decimal number."""
    try:
        amount = float(amount_str)
        # Check if it has at most 2 decimal places
        if '.' in amount_str:
            decimal_part = amount_str.split('.')[1]
            if len(decimal_part) > 2:
                return False, f"Amount '{amount_str}' has more than 2 decimal places"
        return True, ""
    except ValueError:
        return False, f"Amount '{amount_str}' is not a valid number"


def validate_transactions_csv(filepath: Path) -> Tuple[bool, List[str]]:
    """Validate a transactions CSV file against Monarch format."""
    errors = []
    required_columns = ['Date', 'Merchant', 'Category', 'Account', 
                       'Original Statement', 'Notes', 'Amount', 'Tags']
    
    if not filepath.exists():
        return False, [f"File does not exist: {filepath}"]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check headers
            if not reader.fieldnames:
                return False, ["CSV file has no headers"]
            
            missing_columns = set(required_columns) - set(reader.fieldnames)
            if missing_columns:
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            
            extra_columns = set(reader.fieldnames) - set(required_columns)
            if extra_columns:
                errors.append(f"Unexpected columns: {', '.join(extra_columns)}")
            
            # Check column order (Monarch is strict about this)
            if list(reader.fieldnames) != required_columns:
                errors.append(f"Column order is incorrect. Expected: {required_columns}")
            
            # Validate each row
            row_num = 1
            for row in reader:
                row_num += 1
                
                # Validate date
                date = row.get('Date', '').strip()
                if date:
                    valid, msg = validate_date_format(date)
                    if not valid:
                        errors.append(f"Row {row_num}: {msg}")
                
                # Validate amount
                amount = row.get('Amount', '').strip()
                if amount:
                    valid, msg = validate_amount_format(amount)
                    if not valid:
                        errors.append(f"Row {row_num}: {msg}")
                
                # Check for empty required fields (some can be empty, but warn)
                if not row.get('Date', '').strip():
                    errors.append(f"Row {row_num}: Date is empty")
                if not row.get('Amount', '').strip():
                    errors.append(f"Row {row_num}: Amount is empty")
            
            if row_num == 1:
                errors.append("CSV file contains no data rows (only headers)")
    
    except Exception as e:
        return False, [f"Error reading CSV file: {e}"]
    
    return len(errors) == 0, errors


def validate_balances_csv(filepath: Path) -> Tuple[bool, List[str]]:
    """Validate a balance history CSV file against Monarch format."""
    errors = []
    required_columns = ['Date', 'Amount']
    
    if not filepath.exists():
        return False, [f"File does not exist: {filepath}"]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check headers
            if not reader.fieldnames:
                return False, ["CSV file has no headers"]
            
            missing_columns = set(required_columns) - set(reader.fieldnames)
            if missing_columns:
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            
            extra_columns = set(reader.fieldnames) - set(required_columns)
            if extra_columns:
                errors.append(f"Unexpected columns: {', '.join(extra_columns)}")
            
            # Check column order
            if list(reader.fieldnames) != required_columns:
                errors.append(f"Column order is incorrect. Expected: {required_columns}")
            
            # Validate each row
            row_num = 1
            for row in reader:
                row_num += 1
                
                # Validate date
                date = row.get('Date', '').strip()
                if date:
                    valid, msg = validate_date_format(date)
                    if not valid:
                        errors.append(f"Row {row_num}: {msg}")
                else:
                    errors.append(f"Row {row_num}: Date is empty")
                
                # Validate amount
                amount = row.get('Amount', '').strip()
                if amount:
                    valid, msg = validate_amount_format(amount)
                    if not valid:
                        errors.append(f"Row {row_num}: {msg}")
                else:
                    errors.append(f"Row {row_num}: Amount is empty")
            
            if row_num == 1:
                errors.append("CSV file contains no data rows (only headers)")
    
    except Exception as e:
        return False, [f"Error reading CSV file: {e}"]
    
    return len(errors) == 0, errors


def validate_all_csvs(output_dir: Path = Path("output")) -> Tuple[bool, Dict[str, List[str]]]:
    """Validate all CSV files in the output directory."""
    all_results = {}
    all_valid = True
    
    if not output_dir.exists():
        return False, {"error": [f"Output directory does not exist: {output_dir}"]}
    
    # Find all CSV files
    transaction_files = list(output_dir.glob("*_transactions.csv"))
    balance_files = list(output_dir.glob("*_balances.csv"))
    
    if not transaction_files and not balance_files:
        return False, {"error": [f"No CSV files found in {output_dir}"]}
    
    # Validate transaction files
    for tx_file in transaction_files:
        valid, errors = validate_transactions_csv(tx_file)
        all_results[str(tx_file.name)] = errors
        if not valid:
            all_valid = False
    
    # Validate balance files
    for bal_file in balance_files:
        valid, errors = validate_balances_csv(bal_file)
        all_results[str(bal_file.name)] = errors
        if not valid:
            all_valid = False
    
    return all_valid, all_results


def main():
    """Main function to validate CSV files."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate CSV files for Monarch Money import format"
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Specific CSV files to validate (if not provided, validates all in output/)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path("output"),
        help='Directory containing CSV files (default: output/)'
    )
    
    args = parser.parse_args()
    
    if args.files:
        # Validate specific files
        all_valid = True
        for filepath in args.files:
            path = Path(filepath)
            if '_transactions.csv' in path.name:
                valid, errors = validate_transactions_csv(path)
            elif '_balances.csv' in path.name:
                valid, errors = validate_balances_csv(path)
            else:
                print(f"Warning: Unknown file type for {path.name}")
                continue
            
            if valid:
                print(f"✓ {path.name} is valid")
            else:
                print(f"✗ {path.name} has errors:")
                for error in errors:
                    print(f"  - {error}")
                all_valid = False
        
        sys.exit(0 if all_valid else 1)
    else:
        # Validate all files in output directory
        print(f"Validating all CSV files in {args.output_dir}...")
        valid, results = validate_all_csvs(args.output_dir)
        
        if valid:
            print("✓ All CSV files are valid!")
            sys.exit(0)
        else:
            print("✗ Validation found errors:")
            for filename, errors in results.items():
                if errors:
                    print(f"\n{filename}:")
                    for error in errors:
                        print(f"  - {error}")
            sys.exit(1)


if __name__ == "__main__":
    main()

