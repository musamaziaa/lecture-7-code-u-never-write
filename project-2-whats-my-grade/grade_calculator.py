"""
grade_calculator.py
--------------------
Computes a student's current grade from a weighted grading scheme, and
works out what score is needed on the (not-yet-taken) Final Exam to reach
target overall grades of 85%, 90%, and 95%.

Grading scheme:
    Assignments  = 20%   (averaged across all assignment entries)
    Quizzes      = 20%   (averaged across all quiz entries)
    Midterm      = 25%   (single score)
    Final Exam   = 35%   (not yet taken - this is what we solve for)

Input file: grades.csv
Columns:    Category, Score, Max
"""

import pandas as pd

CSV_FILE = "grades.csv"

# --- Grading weights (the four numbers should add up to 1.0 / 100%) -------
WEIGHT_ASSIGNMENTS = 0.20
WEIGHT_QUIZZES = 0.20
WEIGHT_MIDTERM = 0.25
WEIGHT_FINAL = 0.35

TARGET_GRADES = [85, 90, 95]  # the "what do I need on the final" targets


# ---------------------------------------------------------------------------
# STEP 1: LOAD
# ---------------------------------------------------------------------------

def load_data(filepath):
    """Read the raw grade entries from CSV."""
    return pd.read_csv(filepath)


# ---------------------------------------------------------------------------
# STEP 2: CLEAN + HANDLE MISSING VALUES
# ---------------------------------------------------------------------------

def clean_data(df):
    """
    Handle missing values gracefully:
      - A row with a missing/blank Score means that piece of work hasn't
        been graded yet (this is exactly the case for the Final Exam, or
        an assignment that hasn't been marked). We don't treat a missing
        grade as a zero - we set the row aside and exclude it from the
        averages, but keep the user informed about what was excluded.
      - A missing or zero Max can't be turned into a percentage, so those
        rows are excluded the same way.
      - Category text is trimmed and title-cased so "quiz", "Quiz ",
        "QUIZ" etc. are all recognised as the same category.
    """
    df = df.copy()
    df["Category"] = df["Category"].astype(str).str.strip().str.title()

    # Coerce to numeric; anything non-numeric (blank, text, etc.) becomes NaN.
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce")
    df["Max"] = pd.to_numeric(df["Max"], errors="coerce")

    usable = df["Score"].notna() & df["Max"].notna() & (df["Max"] != 0)
    skipped = df[~usable]
    if not skipped.empty:
        print(f"[Note] {len(skipped)} row(s) skipped - missing/ungraded "
              f"(this is expected for the Final Exam):")
        print(skipped.to_string(index=False))
        print()

    df = df[usable].copy()
    # Convert every usable row to a percentage so Assignments/Quizzes of
    # different point values (e.g. 9/10 vs 18/20) can be compared fairly.
    df["Percent"] = (df["Score"] / df["Max"]) * 100
    return df


# ---------------------------------------------------------------------------
# STEP 3: CATEGORY CALCULATIONS
# ---------------------------------------------------------------------------

def category_average(df, category_name):
    """
    Average percentage for a category (e.g. all 'Assignment' rows).
    Each item is converted to a percentage first, then the percentages
    are averaged - so every assignment/quiz counts equally regardless of
    how many points it was worth. Returns None if no usable rows exist.
    """
    rows = df[df["Category"] == category_name]
    if rows.empty:
        return None
    return rows["Percent"].mean()


def single_score(df, category_name):
    """For a category that should only have one entry (e.g. Midterm)."""
    rows = df[df["Category"] == category_name]
    if rows.empty:
        return None
    if len(rows) > 1:
        print(f"[Note] Multiple '{category_name}' rows found - averaging them.")
        return rows["Percent"].mean()
    return rows["Percent"].iloc[0]


# ---------------------------------------------------------------------------
# STEP 4: CURRENT GRADE
# ---------------------------------------------------------------------------

def calculate_current_grade(assignment_avg, quiz_avg, midterm_pct):
    """
    "Current grade" reflects how the student is doing on everything
    graded SO FAR, normalized to its own 100%. The Final Exam hasn't
    happened yet, so only the weights of completed categories are used,
    and those weights are rescaled to add up to 100% on their own. This
    avoids the misleading effect of comparing 65%-worth of work against
    a full 100% scale.

    Returns:
        current_grade      - the normalized 0-100 "grade so far"
        weighted_sum_so_far - the raw weighted total (out of 100, using
                              the REAL scheme weights, not rescaled) -
                              this raw value is what the required-final-
                              score formula below needs.
    """
    components = []
    if assignment_avg is not None:
        components.append((assignment_avg, WEIGHT_ASSIGNMENTS))
    if quiz_avg is not None:
        components.append((quiz_avg, WEIGHT_QUIZZES))
    if midterm_pct is not None:
        components.append((midterm_pct, WEIGHT_MIDTERM))

    if not components:
        return None, 0.0

    weighted_sum_so_far = sum(pct * w for pct, w in components)
    weight_completed = sum(w for _, w in components)
    # NOTE: pct values are already on a 0-100 scale, and weighted_sum_so_far
    # is "percentage-points" (e.g. 85% x 0.20 = 17 points). Dividing by the
    # completed weight directly rescales it back to a 0-100 grade - no
    # extra x100 needed here (that would double-scale it).
    current_grade = weighted_sum_so_far / weight_completed

    return current_grade, weighted_sum_so_far


# ---------------------------------------------------------------------------
# STEP 5: REQUIRED FINAL EXAM SCORE
# ---------------------------------------------------------------------------

def required_final_score(weighted_sum_so_far, target):
    """
    Works out the percentage needed on the Final Exam to reach an overall
    TARGET grade, using the FULL grading scheme (not the normalized
    "current grade" above):

        Overall = (Assignments% x 20%) + (Quizzes% x 20%)
                  + (Midterm% x 25%) + (FinalExam% x 35%)

    weighted_sum_so_far is the first three terms already added together
    (points already locked in, out of 100). Solving the equation above
    for FinalExam% gives:

        FinalExam% = (target - weighted_sum_so_far) / 35%
    """
    return (target - weighted_sum_so_far) / WEIGHT_FINAL


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def fmt(x):
    return f"{x:.2f}%" if x is not None else "No data"


def print_grade_summary(assignment_avg, quiz_avg, midterm_pct, current_grade):
    print_header("GRADE SUMMARY")
    print(f"Assignment Average : {fmt(assignment_avg)}   (weight 20%)")
    print(f"Quiz Average        : {fmt(quiz_avg)}   (weight 20%)")
    print(f"Midterm             : {fmt(midterm_pct)}   (weight 25%)")
    print(f"Final Exam          : Not yet taken   (weight 35%)")
    print("-" * 60)
    print(f"Current Grade       : {fmt(current_grade)}   "
          f"(completed work only, rescaled to 100%)")


def print_required_scores(assignment_avg, quiz_avg, midterm_pct, weighted_sum_so_far):
    print_header("REQUIRED FINAL EXAM SCORE")

    if assignment_avg is None or quiz_avg is None or midterm_pct is None:
        print("Cannot calculate required Final Exam scores yet - "
              "Assignments, Quizzes, and the Midterm must all be graded first.")
        return

    for target in TARGET_GRADES:
        needed = required_final_score(weighted_sum_so_far, target)
        if needed > 100:
            note = "not achievable - exceeds 100%"
        elif needed <= 0:
            note = "already secured, even with 0% on the final"
        else:
            note = ""
        line = f"For {target}% overall -> need {needed:.2f}% on the Final Exam"
        if note:
            line += f"   [{note}]"
        print(line)


def print_explanation():
    print_header("EXPLANATION")
    print("""
1. Reading & Cleaning
   Grades are loaded from grades.csv. Any row with a missing/blank Score
   (such as the Final Exam, which hasn't been taken yet, or an
   assignment that hasn't been marked) is set aside rather than treated
   as a zero - a missing grade and a failing grade are not the same
   thing. Category names are trimmed and consistently capitalized so
   small spelling/casing differences don't create duplicate categories.

2. Assignment & Quiz Averages
   Each individual Assignment/Quiz row is first converted to a
   percentage (Score / Max x 100), and THEN those percentages are
   averaged. This means every assignment or quiz counts equally toward
   the average, even if one was out of 10 points and another was out of
   50.

3. Midterm
   The Midterm is a single graded item, so its percentage is used
   directly - no averaging needed (unless more than one Midterm row is
   found, in which case those are averaged too, with a note printed).

4. Current Grade
   The Final Exam (worth 35%) hasn't happened yet, so it can't be
   included in a "current" grade. Instead, the three completed
   categories (20% + 20% + 25% = 65% of the full scheme) are reweighted
   so they add up to 100% on their own. This shows how the student is
   performing on everything graded so far, on a normal 0-100 scale,
   instead of being artificially capped at 65%.

5. Required Final Exam Score
   This part uses the FULL grading formula, with the Final Exam's real
   35% weight included:

       Overall = (Assignments% x 20%) + (Quizzes% x 20%)
                 + (Midterm% x 25%) + (FinalExam% x 35%)

   The first three terms are already known from steps 2-3. Plugging in
   each target overall grade (85%, 90%, 95%) and solving the equation
   for FinalExam% tells the student exactly what score they need on the
   final to land on that target. A result above 100% means the target is
   mathematically out of reach; a result at or below 0% means the
   target is already locked in regardless of the final exam score.
""")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    raw_df = load_data(CSV_FILE)
    df = clean_data(raw_df)

    assignment_avg = category_average(df, "Assignment")
    quiz_avg = category_average(df, "Quiz")
    midterm_pct = single_score(df, "Midterm")

    current_grade, weighted_sum_so_far = calculate_current_grade(
        assignment_avg, quiz_avg, midterm_pct
    )

    print_grade_summary(assignment_avg, quiz_avg, midterm_pct, current_grade)
    print_required_scores(assignment_avg, quiz_avg, midterm_pct, weighted_sum_so_far)
    print_explanation()


if __name__ == "__main__":
    main()
