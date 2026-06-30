"""
money_detective.py
-------------------
A simple, dependency-light "money detective" that reads a bank/card
transaction CSV and reports on spending patterns.

It looks for:
    1. Recurring transactions   - same merchant, repeating over time
    2. Possible subscriptions   - recurring charges with a steady amount
                                   and a roughly monthly cadence
    3. Duplicate charges        - same merchant + same amount on the
                                   same day (likely double-billing)
    4. Category totals          - spending grouped into simple categories

Only pandas and the Python standard library are used.

Expected input file (same folder as this script):
    sample_transactions.csv
    Columns: Date, Description, Amount
"""

import re
import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

CSV_FILE = "sample_transactions.csv"

# Keywords used to recognise well-known subscription services even if a
# single charge hasn't repeated enough times yet to be caught statistically.
SUBSCRIPTION_KEYWORDS = [
    "NETFLIX", "SPOTIFY", "AMAZON PRIME", "PRIME VIDEO", "HULU", "DISNEY",
    "APPLE MUSIC", "APPLE TV", "YOUTUBE PREMIUM", "ICLOUD", "ADOBE",
    "MICROSOFT 365", "OFFICE 365", "GYM", "PATREON", "PLAYSTATION PLUS",
    "XBOX GAME PASS",
]

# Very simple keyword -> category map. Anything that doesn't match falls
# into "Other / Uncategorized". Edit/extend this list to fit your own
# statement (e.g. add your bank's grocery store names).
CATEGORY_KEYWORDS = {
    "Subscriptions & Entertainment": [
        "NETFLIX", "SPOTIFY", "HULU", "DISNEY", "YOUTUBE", "PRIME VIDEO",
        "APPLE MUSIC", "APPLE TV", "CINEMA", "MOVIE", "GAME PASS",
        "PLAYSTATION",
    ],
    "Food & Dining": [
        "KFC", "MCDONALD", "MCDONALDS", "PIZZA", "RESTAURANT", "CAFE",
        "COFFEE", "FOODPANDA", "UBER EATS", "BURGER", "DOMINOS", "KITCHEN",
        "DINER", "BAKERY",
    ],
    "Groceries": [
        "GROCERY", "SUPERMARKET", "MART", "CARREFOUR", "IMTIAZ", "METRO",
        "STORE",
    ],
    "Transport": [
        "UBER", "CAREEM", "FUEL", "PETROL", "GAS STATION", "TAXI", "TOLL",
        "PARKING",
    ],
    "Utilities & Bills": [
        "ELECTRICITY", "WATER BILL", "GAS BILL", "INTERNET", "WIFI",
        "PHONE BILL", "MOBILE BILL", "PTCL", "ZONG", "JAZZ", "TELENOR",
        "WARID",
    ],
    "Shopping": [
        "AMAZON", "DARAZ", "MALL", "CLOTHING", "SHOES", "ELECTRONICS",
    ],
    "Health": [
        "PHARMACY", "HOSPITAL", "CLINIC", "DOCTOR", "MEDICAL",
    ],
    "Income / Transfers": [
        "SALARY", "TRANSFER", "DEPOSIT", "REFUND",
    ],
}

# Thresholds used by the recurrence/subscription detector. Kept as named
# constants (instead of magic numbers buried in the code) so they're easy
# to tune for a different statement style.
MIN_OCCURRENCES_FOR_RECURRING = 2     # need at least this many charges
MONTHLY_INTERVAL_MIN_DAYS = 20        # "roughly monthly" lower bound
MONTHLY_INTERVAL_MAX_DAYS = 40        # "roughly monthly" upper bound
INTERVAL_STD_TOLERANCE_DAYS = 7       # allowed wobble in the gap between charges
AMOUNT_VARIATION_TOLERANCE = 0.05     # 5% - amount counts as "the same"


# ---------------------------------------------------------------------------
# STEP 1: LOAD
# ---------------------------------------------------------------------------

def load_data(filepath):
    """Load the raw CSV into a DataFrame."""
    df = pd.read_csv(filepath)
    return df


# ---------------------------------------------------------------------------
# STEP 2: CLEAN + NORMALIZE
# ---------------------------------------------------------------------------

def clean_data(df):
    """
    Handle missing values and create a normalized description column so
    that minor formatting differences (extra spaces, transaction IDs,
    mixed case) don't make the same merchant look like two different ones.
    """
    df = df.copy()

    # --- Missing values --------------------------------------------------
    # A row with no Date or no Amount can't be analyzed meaningfully, so we
    # drop those rows. A missing Description is recoverable, so we just
    # label it instead of dropping the transaction.
    df["Description"] = df["Description"].fillna("UNKNOWN")
    df = df.dropna(subset=["Date", "Amount"])

    # --- Type conversion ---------------------------------------------------
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    # Rows that failed to parse (bad date format, non-numeric amount, etc.)
    # become NaT/NaN above, so we drop them now that conversion is done.
    rows_before = len(df)
    df = df.dropna(subset=["Date", "Amount"])
    rows_dropped = rows_before - len(df)
    if rows_dropped:
        print(f"[Note] Dropped {rows_dropped} row(s) with missing/unreadable Date or Amount.\n")

    # --- Normalize description ---------------------------------------------
    # 1. Uppercase, so "Netflix" and "NETFLIX" match.
    # 2. Strip digits and punctuation, so "KFC #4421" and "KFC #9981" match
    #    (these trailing numbers are usually store/terminal/transaction IDs,
    #    not part of the merchant's real name).
    # 3. Collapse repeated whitespace left behind by the cleanup.
    def normalize(desc):
        desc = str(desc).strip().upper()
        desc = re.sub(r"[^A-Z\s]", " ", desc)   # drop digits/punctuation
        desc = re.sub(r"\s+", " ", desc).strip()
        return desc if desc else "UNKNOWN"

    df["NormDescription"] = df["Description"].apply(normalize)

    df = df.sort_values("Date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# STEP 3: RECURRING TRANSACTIONS
# ---------------------------------------------------------------------------

def detect_recurring(df):
    """
    Group transactions by normalized merchant name and flag a merchant as
    "recurring" if it charged on at least two different days AND either:
      (a) the gap between charges is roughly monthly and fairly consistent, or
      (b) the charged amount is essentially identical each time.
    Same-day double charges (true duplicates) are deliberately excluded
    here - they are handled separately by detect_duplicates().
    """
    records = []

    for name, group in df.groupby("NormDescription"):
        distinct_dates = group["Date"].dt.normalize().nunique()
        if len(group) < MIN_OCCURRENCES_FOR_RECURRING or distinct_dates < 2:
            continue

        group = group.sort_values("Date")
        dates = group["Date"].tolist()
        amounts = group["Amount"].tolist()

        # Gaps (in days) between consecutive charges.
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        avg_interval = sum(intervals) / len(intervals)
        interval_std = pd.Series(intervals).std(ddof=0) if len(intervals) > 1 else 0.0

        is_monthlyish = (
            MONTHLY_INTERVAL_MIN_DAYS <= avg_interval <= MONTHLY_INTERVAL_MAX_DAYS
            and interval_std <= INTERVAL_STD_TOLERANCE_DAYS
        )

        avg_amount = sum(amounts) / len(amounts)
        amount_std = pd.Series(amounts).std(ddof=0) if len(amounts) > 1 else 0.0
        consistent_amount = (
            avg_amount == 0
            or (amount_std / abs(avg_amount)) <= AMOUNT_VARIATION_TOLERANCE
        )

        if is_monthlyish or consistent_amount:
            records.append({
                "Description": name,
                "Occurrences": len(group),
                "AvgAmount": round(avg_amount, 2),
                "AvgIntervalDays": round(avg_interval, 1),
                "ConsistentAmount": consistent_amount,
                "LooksMonthly": is_monthlyish,
            })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# STEP 4: POSSIBLE SUBSCRIPTIONS
# ---------------------------------------------------------------------------

def detect_subscriptions(recurring_df):
    """
    A "subscription" is treated as a stricter subset of recurring charges:
    a roughly-monthly cadence with a steady amount, OR a merchant name
    matching a known subscription service (Netflix, Spotify, etc.), which
    catches subscriptions even before they've repeated enough times for the
    statistical test alone to be confident.
    """
    if recurring_df.empty:
        return pd.DataFrame(columns=recurring_df.columns)

    def looks_like_subscription(row):
        keyword_hit = any(k in row["Description"] for k in SUBSCRIPTION_KEYWORDS)
        pattern_hit = row["LooksMonthly"] and row["ConsistentAmount"]
        return keyword_hit or pattern_hit

    mask = recurring_df.apply(looks_like_subscription, axis=1)
    return recurring_df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# STEP 5: DUPLICATE CHARGES
# ---------------------------------------------------------------------------

def detect_duplicates(df):
    """
    Flag transactions that share the same calendar day, the same normalized
    merchant name, AND the same amount - the classic signature of a
    double-billing error (e.g. KFC charged twice on the same day).
    """
    key_cols = [df["Date"].dt.normalize(), "NormDescription", "Amount"]
    dup_mask = df.duplicated(subset=["NormDescription", "Amount"], keep=False) & \
               df.groupby([df["Date"].dt.normalize(), "NormDescription", "Amount"])["Amount"] \
                 .transform("count").gt(1)

    duplicates = df[dup_mask].sort_values(["Date", "NormDescription"])
    return duplicates


# ---------------------------------------------------------------------------
# STEP 6 & 7: CATEGORIZE + TOTALS
# ---------------------------------------------------------------------------

def categorize_description(norm_desc):
    """Match a normalized description against the keyword map."""
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in norm_desc for keyword in keywords):
            return category
    return "Other / Uncategorized"


def categorize_spending(df):
    df = df.copy()
    df["Category"] = df["NormDescription"].apply(categorize_description)
    return df


def calculate_category_totals(df):
    totals = (
        df.groupby("Category")["Amount"]
        .agg(Total="sum", Count="count")
        .sort_values("Total", ascending=False)
    )
    return totals


# ---------------------------------------------------------------------------
# OUTPUT HELPERS
# ---------------------------------------------------------------------------

def print_header(title):
    print("\n" + "=" * 72)
    print(title.upper())
    print("=" * 72)


def print_recurring(recurring_df):
    print_header("Recurring Charges")
    if recurring_df.empty:
        print("No recurring charges detected.")
        return
    view = recurring_df[["Description", "Occurrences", "AvgAmount", "AvgIntervalDays"]]
    view = view.rename(columns={
        "Description": "Merchant",
        "Occurrences": "Times Charged",
        "AvgAmount": "Avg Amount",
        "AvgIntervalDays": "Avg Days Between Charges",
    })
    print(view.to_string(index=False))


def print_subscriptions(sub_df):
    print_header("Possible Subscriptions")
    if sub_df.empty:
        print("No likely subscriptions detected.")
        return
    view = sub_df[["Description", "Occurrences", "AvgAmount", "AvgIntervalDays"]]
    view = view.rename(columns={
        "Description": "Service",
        "Occurrences": "Times Charged",
        "AvgAmount": "Avg Amount",
        "AvgIntervalDays": "Avg Days Between Charges",
    })
    print(view.to_string(index=False))


def print_duplicates(dup_df):
    print_header("Duplicates")
    if dup_df.empty:
        print("No duplicate same-day charges detected.")
        return
    view = dup_df[["Date", "Description", "Amount"]].copy()
    view["Date"] = view["Date"].dt.strftime("%Y-%m-%d")
    print(view.to_string(index=False))
    print(f"\n{len(dup_df)} transaction row(s) involved in possible duplicate billing.")


def print_category_totals(totals_df):
    print_header("Category Totals")
    view = totals_df.copy()
    view["Total"] = view["Total"].round(2)
    print(view.to_string())
    print(f"\nGrand Total: {round(totals_df['Total'].sum(), 2)}")


def print_explanation():
    print_header("How This Was Detected (Plain English)")
    print("""
1. Loading & Cleaning
   The CSV is read with pandas. Rows missing a Date or Amount are dropped,
   since nothing useful can be calculated without them. A missing
   Description is kept but labeled "UNKNOWN" rather than thrown away.

2. Normalizing Descriptions
   Raw merchant text is messy - "Netflix.com 8841", "NETFLIX *123" and
   "netflix" should all count as the same merchant. Each description is
   uppercased, stripped of digits/punctuation (which are usually random
   store or transaction IDs), and tidied up. This lets the script match
   the same merchant reliably even when the raw text varies slightly.

3. Recurring Charges
   Transactions are grouped by their cleaned merchant name. A merchant is
   called "recurring" if it appears on at least two different calendar
   days AND either (a) the gap between charges is roughly monthly and
   fairly steady, or (b) the amount charged barely changes between visits.
   This catches both fixed monthly bills and habitual repeat purchases.

4. Possible Subscriptions
   This is a tighter filter on top of "recurring": charges that are both
   roughly monthly AND a steady amount, which is exactly how subscriptions
   like Netflix or Spotify bill. Well-known subscription service names are
   also matched directly by keyword, so a real subscription is still
   flagged even if it has only appeared once or twice so far.

5. Duplicates
   A duplicate is a same merchant, same amount charge appearing more than
   once on the SAME calendar day - the classic fingerprint of an accidental
   double-swipe or a billing glitch (e.g. KFC charged twice in one day).
   This check is deliberately separate from the recurring-charge check
   above, since a recurring bill repeats across different days, while a
   duplicate repeats within the same day.

6. Categorization & Totals
   Each cleaned description is checked against a keyword list (e.g. "KFC"
   -> Food & Dining, "ZONG"/"PTCL" -> Utilities & Bills). Anything that
   doesn't match a known keyword falls into "Other / Uncategorized" so
   nothing is silently dropped. Amounts are then summed per category to
   show where the money actually went.

Note: All thresholds (monthly window, amount tolerance, etc.) are
heuristics, not certainties - they're meant to surface likely patterns for
you to review, not to make final financial judgments.
""")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    raw_df = load_data(CSV_FILE)
    df = clean_data(raw_df)

    recurring_df = detect_recurring(df)
    subscriptions_df = detect_subscriptions(recurring_df)
    duplicates_df = detect_duplicates(df)

    categorized_df = categorize_spending(df)
    totals_df = calculate_category_totals(categorized_df)

    print_recurring(recurring_df)
    print_subscriptions(subscriptions_df)
    print_duplicates(duplicates_df)
    print_category_totals(totals_df)
    print_explanation()


if __name__ == "__main__":
    main()
