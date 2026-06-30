# Project 1 — Money Detective

## Problem

People often overlook recurring charges, duplicate payments, and forgotten subscriptions.

This project analyzes transaction history and identifies spending leaks automatically.

---

## AI Tool Used

Claude Sonnet

---

## Objective

Identify:

- recurring charges
- subscriptions
- duplicate payments
- spending categories

---

## Files Included

money_detective.py

sample_transactions.csv

prompts.md

screenshots/

---

## Verification

Expected recurring services:

- Netflix
- Spotify
- PTCL Internet Bill
- Zong Mobile Bill

Expected duplicate:

KFC

Date:
2026-04-02

Amount:
1450

The script successfully detected these patterns.

Verification passed.

---

## Results

Detected recurring services:

- Netflix
- Spotify
- PTCL
- Zong

Detected duplicates:

- KFC

Generated spending summaries.

---

## Limitations

The script incorrectly classified IMTIAZ SUPERMARKET as a possible subscription because purchases occurred at regular intervals.

This demonstrates the importance of human verification when using AI-generated solutions.

---

## Learning

AI can significantly accelerate financial analysis.

However, outputs should always be verified against known data.
