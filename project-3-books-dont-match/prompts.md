# Initial Prompt

Create a Python script to compare expected payments with actual payments.

---

# Improved Prompt

You are a financial reconciliation specialist.

Create a Python script called books_reconciliation.py.

Input file:

payments.csv

Columns:

Person
Expected
Paid

Requirements:

Use pandas.

Handle missing values gracefully.

Treat missing Paid amounts as unpaid.

Exclude missing Expected amounts from reconciliation.

Calculate:

* expected total
* received total
* outstanding balance

Identify:

* unpaid individuals
* partially paid individuals
* overpayments
* underpayments

Provide:

SUMMARY

UNPAID

PARTIALLY PAID

OVERPAID

UNDERPAID

VERIFICATION

PLAIN ENGLISH EXPLANATION

Include comments throughout the code.

---

# Final Prompt

<Prompt used to generate books_reconciliation.py>
