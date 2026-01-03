# Manual Testing Guide

This guide provides steps for manually testing the Wealthsimple to Monarch CSV converter with your actual account data.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify Installation**
   ```bash
   python -c "import ws_api; import keyring; print('Dependencies OK')"
   ```

## Testing Steps

### 1. Initial Setup and Authentication

1. **Run the script:**
   ```bash
   python main.py
   ```

2. **First-time authentication:**
   - Enter your Wealthsimple username (email)
   - Enter your password
   - If TOTP is enabled, enter the TOTP code when prompted
   - Verify that authentication succeeds without errors

3. **Subsequent runs:**
   - The script should reuse your saved session
   - Verify that you don't need to re-enter credentials
   - If session expires, verify it prompts for login again

### 2. Account Retrieval Verification

After authentication, verify:
- [ ] All your Wealthsimple accounts are listed
- [ ] Account descriptions are correct
- [ ] Account numbers are displayed
- [ ] No error messages appear during account retrieval

### 3. Transaction Export Verification

For each account, check:

1. **File Generation:**
   - [ ] A `{account_number}_transactions.csv` file is created in the `output/` directory
   - [ ] Filename is sanitized (no invalid characters)

2. **CSV Format Validation:**
   ```bash
   python validate_csv.py output/{account_number}_transactions.csv
   ```
   - [ ] Validation passes with no errors
   - [ ] All required columns are present: Date, Merchant, Category, Account, Original Statement, Notes, Amount, Tags
   - [ ] Column order matches Monarch requirements

3. **Data Accuracy:**
   - [ ] Open the CSV file and spot-check several transactions
   - [ ] Dates are in MM/DD/YYYY format
   - [ ] Amounts are properly formatted (2 decimal places)
   - [ ] Debits are negative, credits are positive
   - [ ] Transaction descriptions are readable
   - [ ] Account name matches the account
   - [ ] Compare a few transactions with your Wealthsimple account to verify accuracy

4. **Edge Cases:**
   - [ ] Accounts with no transactions: Verify script handles gracefully (no crash, appropriate message)
   - [ ] Special characters in account names: Verify filenames are sanitized correctly

### 4. Balance History Export Verification

For each account, check:

1. **File Generation:**
   - [ ] A `{account_number}_balances.csv` file is created in the `output/` directory
   - [ ] Filename is sanitized

2. **CSV Format Validation:**
   ```bash
   python validate_csv.py output/{account_number}_balances.csv
   ```
   - [ ] Validation passes with no errors
   - [ ] Required columns are present: Date, Amount
   - [ ] Column order is correct

3. **Data Accuracy:**
   - [ ] Open the CSV file and verify balance history
   - [ ] Dates are in MM/DD/YYYY format
   - [ ] Amounts are properly formatted
   - [ ] Balance values match your expectations (compare with Wealthsimple account)

4. **Edge Cases:**
   - [ ] Accounts with no balance history: Verify script handles gracefully

### 5. Monarch Import Testing

1. **Import Transactions:**
   - [ ] Log in to Monarch Money
   - [ ] Navigate to the account
   - [ ] Click "Edit" → "Import transactions"
   - [ ] Upload the `{account_number}_transactions.csv` file
   - [ ] Verify import succeeds without errors
   - [ ] Spot-check imported transactions match the CSV

2. **Import Balance History:**
   - [ ] Navigate to the account in Monarch
   - [ ] Click "Edit" → "Import balance history"
   - [ ] Upload the `{account_number}_balances.csv` file
   - [ ] Verify import succeeds
   - [ ] Verify balance history is displayed correctly

### 6. Error Handling Verification

Test error scenarios:

1. **Invalid Credentials:**
   - [ ] Enter wrong password
   - [ ] Verify helpful error message is displayed
   - [ ] Verify script allows retry

2. **Network Issues:**
   - [ ] Disconnect internet and run script
   - [ ] Verify error message is clear
   - [ ] Verify script doesn't crash

3. **Empty Accounts:**
   - [ ] Test with accounts that have no transactions/balances
   - [ ] Verify appropriate messages are displayed
   - [ ] Verify no empty CSV files are created (or they're handled properly)

### 7. Validation Utility Testing

Run the validation script on all generated files:

```bash
# Validate all files in output directory
python validate_csv.py

# Validate specific file
python validate_csv.py output/ACCOUNT123_transactions.csv
```

- [ ] All files pass validation
- [ ] Error messages are clear if validation fails

## Testing Checklist Summary

### Authentication
- [ ] First-time login works
- [ ] TOTP authentication works (if enabled)
- [ ] Session persistence works
- [ ] Invalid credentials handled gracefully

### Data Export
- [ ] All accounts are retrieved
- [ ] Transaction CSV files are generated correctly
- [ ] Balance CSV files are generated correctly
- [ ] Filenames are sanitized properly

### CSV Format
- [ ] Transaction CSVs pass validation
- [ ] Balance CSVs pass validation
- [ ] Dates are in correct format (MM/DD/YYYY)
- [ ] Amounts are properly formatted
- [ ] All required columns are present
- [ ] Column order is correct

### Data Accuracy
- [ ] Transaction data matches Wealthsimple account
- [ ] Balance history matches Wealthsimple account
- [ ] Amount signs are correct (negative for debits)
- [ ] Dates are accurate

### Monarch Import
- [ ] Transactions import successfully
- [ ] Balance history imports successfully
- [ ] Imported data displays correctly in Monarch

### Error Handling
- [ ] Invalid credentials handled
- [ ] Network errors handled
- [ ] Empty accounts handled
- [ ] Error messages are helpful

## Troubleshooting

### Common Issues

1. **"Import 'ws_api' could not be resolved"**
   - Solution: Run `pip install -r requirements.txt`

2. **"Login failed"**
   - Check your credentials
   - Verify TOTP code if enabled
   - Check if Wealthsimple has changed their API

3. **"No CSV files found"**
   - Verify the script ran successfully
   - Check the `output/` directory exists
   - Verify accounts have data to export

4. **CSV validation fails**
   - Check the specific error message
   - Verify the CSV file isn't corrupted
   - Re-run the export script

## Next Steps

After manual testing is complete and verified:
- Document any issues found
- Plan automated testing (unit tests, integration tests)
- Consider adding more edge case handling if needed

