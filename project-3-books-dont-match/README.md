# Project 3 — The Books Don't Match

## Problem

Financial records often contain incomplete, inconsistent, or missing information.

This project compares expected payments against actual payments and automatically identifies discrepancies.

---

## AI Tool Used

Claude Sonnet

---

## Files Included

* books_reconciliation.py
* payments.csv
* prompts.md
* screenshots/

---

## Objective

Determine:

* Total expected amount
* Total received amount
* Outstanding balance

Identify:

* Unpaid individuals
* Partially paid individuals
* Overpayments
* Underpayments

---

## Verification

Known records:

Hamza paid only 500 out of 1000.

Bilal has no payment recorded.

Ayaan paid 800 out of 1000.

Sara overpaid by 200.

Expected Total:

8500

Received Total:

7000

Outstanding Amount:

1500

The script independently verified the reconciliation using two different calculation methods.

Verification passed.

---

## Findings

The script successfully detected:

* unpaid records
* partial payments
* overpayments
* underpayments

It also excluded records without an Expected amount, since they cannot be reconciled reliably.

---

## Challenges

Some payment records intentionally contained missing values.

Missing payment amounts were treated as unpaid.

Missing Expected values were excluded and reported separately.

---

## Learning

AI can automate reconciliation tasks effectively.

However, reconciliation results should always be independently verified before making financial decisions.
