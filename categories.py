"""
Auto-categorization for Wealthsimple transactions using external YAML rules.

Rules are loaded from category_rules.yaml (copy from category_rules.example.yaml).
See that file for format documentation.
"""

from pathlib import Path
from typing import Optional

import yaml


def load_rules(path: Optional[Path] = None) -> dict:
    """Load category rules from a YAML file.

    Args:
        path: Path to the YAML rules file. Defaults to category_rules.yaml
              in the same directory as this module.

    Returns:
        Parsed rules dict with 'type_rules' and 'merchant_rules' keys.
        Returns empty rules if the file doesn't exist.
    """
    if path is None:
        path = Path(__file__).parent / 'category_rules.yaml'

    if not path.exists():
        print(f"Warning: Category rules file not found: {path}")
        print("  Transactions will not be categorized.")
        print("  Copy category_rules.example.yaml to category_rules.yaml to enable.")
        return {'type_rules': [], 'merchant_rules': []}

    with open(path, 'r', encoding='utf-8') as f:
        rules = yaml.safe_load(f)

    return {
        'type_rules': rules.get('type_rules', []),
        'merchant_rules': rules.get('merchant_rules', []),
    }


def categorize_transaction(
    tx_type: str,
    sub_type: Optional[str],
    merchant: str,
    rules: dict,
) -> str:
    """Determine the Monarch Money category for a transaction.

    Args:
        tx_type: Transaction type (e.g., 'CREDIT_CARD', 'INTEREST').
        sub_type: Transaction subType (e.g., 'PURCHASE', None).
        merchant: Cleaned merchant name (after prefix stripping).
        rules: Rules dict from load_rules().

    Returns:
        Category string, or empty string if no match.
    """
    type_rules = rules.get('type_rules', [])
    merchant_rules = rules.get('merchant_rules', [])

    # For CREDIT_CARD transactions, check type rules for specific subtypes first
    # (e.g., PAYMENT), then fall through to merchant matching for PURCHASE/REFUND.
    if tx_type == 'CREDIT_CARD':
        # Check if there's a type rule for this specific subtype
        for rule in type_rules:
            if rule.get('type') != tx_type:
                continue
            rule_subtype = rule.get('subtype')
            if rule_subtype is not None and rule_subtype == sub_type:
                return rule['category']

        # Fall through to merchant keyword matching
        merchant_lower = merchant.lower()
        for rule in merchant_rules:
            if rule['keyword'] in merchant_lower:
                return rule['category']

        return ''

    # For all other transaction types, match type rules
    # Try specific (type + subtype) first, then type-only
    best_match = None
    for rule in type_rules:
        if rule.get('type') != tx_type:
            continue
        rule_subtype = rule.get('subtype')
        if rule_subtype is not None and rule_subtype == sub_type:
            return rule['category']  # Exact match, return immediately
        if rule_subtype is None and best_match is None:
            best_match = rule['category']  # General match, keep as fallback

    if best_match is not None:
        return best_match

    return ''
