"""
books_reconciliation.py
------------------------
A simple reconciliation tool that compares what was EXPECTED from each
person against what was actually PAID, and flags every kind of
inconsistency: people who haven't paid at all, people who paid part of
what they owe, people who underpaid, and people who overpaid.

Input file: payments.csv
Columns:    Person, Expected, Paid

No external APIs are used - only pandas and the Python standard library.
"""

import pandas as pd

CSV_FILE = "payments.csv"
ROUNDING_TOLERANCE = 0.01  # treat differences smaller than this as "exact"


# ---------------------------------------------------------------------------
# STEP 1: LOAD
# ---------------------------------------------------------------------------

def load_data(filepath):
    """Read the raw payment records from CSV."""
    return pd.read_csv(filepath)


# ---------------------------------------------------------------------------
# STEP 2: CLEAN + HANDLE MISSING VALUES
# ---------------------------------------------------------------------------

def clean_data(df):
    """
    Handle missing values gracefully, with two different rules depending
    on WHICH value is missing:

      - Missing Person name -> we can't drop a real payment record just
        because the name is blank, so it's labeled "Unknown" instead.

      - Missing Paid amount -> per the reconciliation rules for this
        project, a missing payment means the person hasn't paid, so it
        is treated as 0 (unpaid), NOT dropped.

      - Missing Expected amount -> this is different. "Expected" is the
        benchmark everything else is measured against; if we don't know
        what someone owed, we cannot reconcile their row at all. Rather
        than guessing (e.g. assuming 0, which would wrongly mark them as
        "fully settled"), these rows are excluded from the numeric
        reconciliation and reported separately so nothing is silently
        lost or misrepresented.
    """
    df = df.copy()

    # --- Person: fill blanks, don't drop the row -----------------------
    df["Person"] = df["Person"].astype(str).str.strip()
    df.loc[df["Person"].isin(["", "nan", "None"]), "Person"] = "Unknown"

    # --- Convert to numeric; non-numeric/blank entries become NaN ------
    df["Expected"] = pd.to_numeric(df["Expected"], errors="coerce")
    df["Paid"] = pd.to_numeric(df["Paid"], errors="coerce")

    # --- Rows with no Expected value can't be reconciled - set aside ---
    no_expected = df["Expected"].isna()
    excluded_rows = df[no_expected]
    if not excluded_rows.empty:
        print(f"[Note] {len(excluded_rows)} row(s) excluded - no Expected "
              f"amount on record, so there is nothing to reconcile against:")
        print(excluded_rows.to_string(index=False))
        print()
    df = df[~no_expected].copy()

    # --- Missing Paid amount = treated as unpaid (0), per requirements -
    missing_paid_count = df["Paid"].isna().sum()
    if missing_paid_count:
        print(f"[Note] {missing_paid_count} row(s) had no Paid amount on "
              f"record - treated as $0 (unpaid).\n")
    df["Paid"] = df["Paid"].fillna(0)

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# STEP 3: PER-PERSON DIFFERENCE
# ---------------------------------------------------------------------------

def add_difference_column(df):
    """
    Difference = Paid - Expected.
        Difference > 0  -> overpaid by that amount
        Difference < 0  -> short by that amount (underpaid)
        Difference == 0 -> paid in full, exactly as expected
    """
    df = df.copy()
    df["Difference"] = df["Paid"] - df["Expected"]
    return df


# ---------------------------------------------------------------------------
# STEP 4: TOTALS
# ---------------------------------------------------------------------------

def calculate_totals(df):
    """
    Expected Total = sum of everything that was supposed to come in.
    Received Total = sum of everything that actually came in.
    Missing Amount = Expected Total - Received Total (the net shortfall;
                     overpayments from some people DO offset shortfalls
                     from others in this net figure - see the
                     Verification section for a second, independent way
                     to compute the same number).
    """
    expected_total = df["Expected"].sum()
    received_total = df["Paid"].sum()
    missing_amount = expected_total - received_total
    return expected_total, received_total, missing_amount


# ---------------------------------------------------------------------------
# STEP 5: CATEGORIZATION
# ---------------------------------------------------------------------------

def categorize(df):
    """
    Split the reconciled records into the four categories requested:

      UNPAID           - paid nothing at all ($0), and something was
                          actually expected from them.
      PARTIALLY PAID   - paid something, but less than the full amount
                          expected.
      OVERPAID         - paid more than what was expected.
      UNDERPAID        - paid less than expected, period. This is the
                          umbrella "shortfall" view and deliberately
                          OVERLAPS with UNPAID and PARTIALLY PAID (every
                          unpaid or partially-paid person is, by
                          definition, also underpaid). It exists as a
                          single combined "who still owes money" list,
                          while UNPAID/PARTIALLY PAID break that down by
                          how much progress each person has made.

    People who paid exactly what was expected (Difference == 0, within
    rounding tolerance) appear in none of these four lists - they are
    fully reconciled and need no follow-up.
    """
    unpaid = df[(df["Paid"] <= 0) & (df["Expected"] > 0)]

    partially_paid = df[
        (df["Paid"] > 0) & (df["Difference"] < -ROUNDING_TOLERANCE)
    ]

    overpaid = df[df["Difference"] > ROUNDING_TOLERANCE]

    underpaid = df[
        (df["Difference"] < -ROUNDING_TOLERANCE) & (df["Expected"] > 0)
    ]

    return unpaid, partially_paid, overpaid, underpaid


# ---------------------------------------------------------------------------
# STEP 6: VERIFICATION (cross-check the math two independent ways)
# ---------------------------------------------------------------------------

def verify_reconciliation(df, missing_amount, underpaid_df, overpaid_df):
    """
    A reconciliation isn't trustworthy unless it's been checked. Here the
    Missing Amount is computed a SECOND, independent way and compared
    against the first:

      Method 1 (already done in calculate_totals):
          Missing Amount = Expected Total - Received Total

      Method 2 (computed here):
          Missing Amount = (total shortfall from underpaid people)
                            - (total excess from overpaid people)

    If both methods agree, the books are internally consistent. If they
    don't, something in the data or the logic needs a second look.
    """
    total_shortfall = (underpaid_df["Expected"] - underpaid_df["Paid"]).sum()
    total_excess = (overpaid_df["Paid"] - overpaid_df["Expected"]).sum()
    method_2_value = total_shortfall - total_excess

    matches = abs(method_2_value - missing_amount) < ROUNDING_TOLERANCE
    return total_shortfall, total_excess, method_2_value, matches


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def money(x):
    return f"${x:,.2f}"


def print_summary(expected_total, received_total, missing_amount):
    print_header("SUMMARY")
    print(f"Expected Total : {money(expected_total)}")
    print(f"Received Total : {money(received_total)}")
    print(f"Missing Amount : {money(missing_amount)}")


def print_group(title, group_df, amount_label="Owed", show_as_positive=True):
    """
    show_as_positive=True displays the gap as a plain positive number
    (e.g. "Owed: 3000" rather than "-3000"), which reads more naturally
    for shortfall amounts. Overpaid amounts are already positive, so
    this flag is set to False for that group.
    """
    print_header(title)
    if group_df.empty:
        print("None.")
        return
    view = group_df[["Person", "Expected", "Paid", "Difference"]].copy()
    amount = view["Difference"].abs() if show_as_positive else view["Difference"]
    view = view.drop(columns=["Difference"])
    view[amount_label] = amount
    print(view.to_string(index=False))


def print_verification(expected_total, received_total, missing_amount,
                        total_shortfall, total_excess, method_2_value, matches):
    print_header("VERIFICATION")
    print(f"Method 1: Expected Total - Received Total")
    print(f"          {money(expected_total)} - {money(received_total)} "
          f"= {money(missing_amount)}")
    print()
    print(f"Method 2: Total Shortfall - Total Excess")
    print(f"          {money(total_shortfall)} - {money(total_excess)} "
          f"= {money(method_2_value)}")
    print()
    if matches:
        print("RESULT: Both methods agree - the reconciliation balances.")
    else:
        print("RESULT: MISMATCH - the two methods disagree. Re-check the "
              "underlying data before relying on these figures.")


def print_explanation():
    print_header("HOW RECONCILIATION WORKS (PLAIN ENGLISH)")
    print("""
1. Reading & Cleaning
   Payment records are loaded from payments.csv. A missing Person name
   is labeled "Unknown" rather than dropped. A missing Paid amount is
   treated as $0 - if there's no record of a payment, the safest
   assumption is that none was made. A missing Expected amount, however,
   is treated differently: without knowing what someone owed, there is
   nothing to compare their payment against, so that row is excluded
   from the totals and reported separately rather than guessed at.

2. The Difference
   For every remaining person, Difference = Paid - Expected.
     - A positive Difference means they paid MORE than expected
       (an overpayment).
     - A negative Difference means they paid LESS than expected
       (a shortfall).
     - A Difference of zero (within a tiny rounding tolerance) means
       they paid exactly what was expected - fully reconciled, no
       action needed.

3. The Four Categories
     UNPAID            -> paid $0 of an amount that was expected.
     PARTIALLY PAID     -> paid something, but not the full amount.
     OVERPAID           -> paid more than was expected.
     UNDERPAID          -> paid less than expected, full stop. This is
                            a combined view that includes everyone who
                            is UNPAID or PARTIALLY PAID - it answers the
                            single question "who still owes money?" in
                            one list, while the other two categories
                            show exactly how far along each of those
                            people is.

4. The Totals
   Expected Total and Received Total are simply the sums of the
   Expected and Paid columns. Missing Amount is Expected Total minus
   Received Total - the net amount still outstanding once
   overpayments from some people have offset shortfalls from others.

5. Verification
   Good reconciliation work is never taken on faith - it's checked a
   second way. Here, the Missing Amount is recalculated independently
   as (everyone's shortfall added together) minus (everyone's
   overpayment added together). Because every dollar in the books is
   accounted for in exactly one of these two methods, they should
   always produce the same final number. If they don't, it's a signal
   that something in the data needs to be re-examined before the
   figures are trusted.
""")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    raw_df = load_data(CSV_FILE)
    df = clean_data(raw_df)
    df = add_difference_column(df)

    expected_total, received_total, missing_amount = calculate_totals(df)
    unpaid, partially_paid, overpaid, underpaid = categorize(df)

    total_shortfall, total_excess, method_2_value, matches = verify_reconciliation(
        df, missing_amount, underpaid, overpaid
    )

    print_summary(expected_total, received_total, missing_amount)
    print_group("UNPAID", unpaid)
    print_group("PARTIALLY PAID", partially_paid)
    print_group("OVERPAID", overpaid, amount_label="Overpaid By", show_as_positive=False)
    print_group("UNDERPAID", underpaid, amount_label="Short By")
    print_verification(expected_total, received_total, missing_amount,
                        total_shortfall, total_excess, method_2_value, matches)
    print_explanation()


if __name__ == "__main__":
    main()
