# Project 2 — What's My Grade Really?

## Problem

Students often struggle to determine their current grade and estimate what score they need on the final exam to achieve a target overall grade.

This project uses AI-generated Python code to automate weighted grade calculations and predict the required Final Exam score.

---

## AI Tool Used

Claude Sonnet

---

## Files Included

* grade_calculator.py
* grades.csv
* prompts.md
* screenshots/

---

## Objective

Calculate:

* Assignment average
* Quiz average
* Midterm score
* Current grade
* Required Final Exam score for:

  * 85%
  * 90%
  * 95%

---

## Verification

Known data:

Assignment Average = 85.00%

Quiz Average = 86.25%

Midterm = 78.00%

Manual weighted calculation:

Assignments

85 × 0.20 = 17.00

Quizzes

86.25 × 0.20 = 17.25

Midterm

78 × 0.25 = 19.50

Weighted contribution so far:

17.00 + 17.25 + 19.50

= 53.75

Completed weight:

20% + 20% + 25%

= 65%

Current Grade:

53.75 ÷ 0.65

= 82.69%

Matches script output.

Verification passed.

---

## Findings

Current Grade:

82.69%

Required Final Exam Score:

For 85% overall:

89.29%

For 90% overall:

103.57%

Not achievable

For 95% overall:

117.86%

Not achievable

---

## Challenges

Some grades were intentionally left blank.

The script correctly excluded missing grades rather than treating them as zero.

This demonstrates appropriate handling of incomplete academic records.

---

## Learning

AI can automate academic calculations efficiently.

However, results should always be verified manually before relying on them for important decisions.
