"""
organize_files.py
-------------------
Reads a list of filenames and sorts them into categories based on their
file extension (Images, Documents, Videos, Music, Archives, Other),
then reports how many files fall into each category.

Input file: sample_files.csv
Column:     Filename

Only pandas and the Python standard library are used.
"""

import os
import pandas as pd

CSV_FILE = "sample_files.csv"

# --- Extension -> Category map ---------------------------------------
# Extensions are stored lowercase and without the leading dot, since
# that's how we'll normalize each filename's extension before lookup.
CATEGORY_EXTENSIONS = {
    "Images": ["jpg", "jpeg", "png", "gif"],
    "Documents": ["pdf", "docx", "txt", "pptx", "xlsx"],
    "Videos": ["mp4", "avi", "mov"],
    "Music": ["mp3", "wav"],
    "Archives": ["zip", "rar"],
}

# Build a reverse lookup (extension -> category) once, up front, so
# categorizing each file is a quick dictionary lookup rather than
# looping through every category for every file.
EXTENSION_TO_CATEGORY = {
    ext: category
    for category, extensions in CATEGORY_EXTENSIONS.items()
    for ext in extensions
}

# The fixed display order requested for the output sections.
CATEGORY_ORDER = ["Images", "Documents", "Videos", "Music", "Archives", "Other"]


# ---------------------------------------------------------------------------
# STEP 1: LOAD
# ---------------------------------------------------------------------------

def load_data(filepath):
    """Read the raw filename list from CSV."""
    return pd.read_csv(filepath)


# ---------------------------------------------------------------------------
# STEP 2: CLEAN + HANDLE MISSING VALUES
# ---------------------------------------------------------------------------

def clean_data(df):
    """
    Handle missing filenames gracefully:
      - A row with a blank/NaN Filename can't be categorized by
        extension at all (there's no name to read an extension from).
        Rather than crashing or silently dropping the row, we keep it
        visible, label it clearly, and route it straight into "Other"
        so every input row is still accounted for in the totals.
      - Filenames are also stripped of stray leading/trailing whitespace,
        since "report.pdf " and "report.pdf" should be treated the same.
    """
    df = df.copy()

    # Treat blank strings the same as NaN so both are caught below.
    df["Filename"] = df["Filename"].astype(str).str.strip()
    df.loc[df["Filename"].isin(["", "nan", "None"]), "Filename"] = pd.NA

    missing_count = df["Filename"].isna().sum()
    if missing_count:
        print(f"[Note] {missing_count} row(s) had a missing/blank Filename - "
              f"these are kept and filed under 'Other' since there is no "
              f"name to read a file extension from.\n")

    # Replace missing names with a clear placeholder so they still show
    # up in the output instead of disappearing from the data entirely.
    df["Filename"] = df["Filename"].fillna("(missing filename)")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# STEP 3: EXTRACT EXTENSION + CATEGORIZE
# ---------------------------------------------------------------------------

def get_extension(filename):
    """
    Pull the file extension off a filename, lowercased and without the
    leading dot, using the standard library's os.path.splitext so this
    works correctly even for names with multiple dots (e.g.
    "archive.tar.gz" -> "gz", "my.report.final.docx" -> "docx").
    Returns "" if there is no extension at all (e.g. "README" or our
    own "(missing filename)" placeholder).
    """
    _, ext = os.path.splitext(filename)
    return ext.lstrip(".").lower()


def categorize_file(filename):
    """
    Look up a file's category from its extension. Any extension not in
    our supported list (including no extension at all, or a missing
    filename) falls into "Other" - nothing is ever rejected outright.
    """
    ext = get_extension(filename)
    return EXTENSION_TO_CATEGORY.get(ext, "Other")


def categorize_files(df):
    df = df.copy()
    df["Extension"] = df["Filename"].apply(get_extension)
    df["Category"] = df["Filename"].apply(categorize_file)
    return df


# ---------------------------------------------------------------------------
# STEP 4: COUNTS
# ---------------------------------------------------------------------------

def calculate_counts(df):
    """
    Number of files per category, plus the grand total. reindex() makes
    sure every category appears in the result (with a count of 0) even
    if no files happened to fall into it, so the SUMMARY section is
    always complete.
    """
    counts = df["Category"].value_counts().reindex(CATEGORY_ORDER, fill_value=0)
    total_files = len(df)
    return counts, total_files


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_summary(counts, total_files):
    print_header("SUMMARY")
    for category in CATEGORY_ORDER:
        print(f"{category:<10}: {counts[category]} file(s)")
    print("-" * 60)
    print(f"{'Total':<10}: {total_files} file(s)")


def print_category_section(title, df, category_name):
    print_header(title)
    rows = df[df["Category"] == category_name]
    if rows.empty:
        print("None.")
        return
    view = rows[["Filename", "Extension"]].copy()
    view["Extension"] = view["Extension"].replace("", "(none)")
    print(view.to_string(index=False))


def print_verification(counts, total_files):
    """
    A quick sanity check: every file belongs to exactly one category, so
    the six category counts added together must equal the total number
    of files read from the CSV. If they don't match, something in the
    categorization logic skipped or double-counted a row.
    """
    print_header("VERIFICATION")
    category_sum = int(counts.sum())
    print(f"Sum of all category counts : {category_sum}")
    print(f"Total files read from CSV  : {total_files}")
    if category_sum == total_files:
        print("RESULT: Match - every file was categorized exactly once.")
    else:
        print("RESULT: MISMATCH - the category counts do not add up to the "
              "total file count. Re-check the categorization logic.")


def print_explanation():
    print_header("EXPLANATION")
    print("""
1. Reading & Cleaning
   Filenames are loaded from sample_files.csv. Any row with a missing or
   blank Filename is kept (not dropped) so every input row is still
   represented in the results - it's relabeled "(missing filename)" and
   automatically routed to "Other", since a file extension can't be read
   from a name that doesn't exist.

2. Reading the Extension
   For each filename, the portion after the LAST dot is taken as the
   extension (e.g. "vacation.photo.jpg" -> "jpg"), lowercased so that
   "PDF", "Pdf", and "pdf" are all treated identically. A filename with
   no dot at all (e.g. "README") has no extension and is treated as
   unrecognized.

3. Categorizing
   Each extension is looked up against the supported list:
     Images    -> jpg, jpeg, png, gif
     Documents -> pdf, docx, txt, pptx, xlsx
     Videos    -> mp4, avi, mov
     Music     -> mp3, wav
     Archives  -> zip, rar
   Any extension that isn't on this list - including no extension, an
   unfamiliar one like ".exe", or a missing filename - falls into
   "Other" rather than being skipped or causing an error.

4. Counting
   The number of files in each category is simply a count of how many
   rows landed there, and the Total is the count of all rows read from
   the file (after cleaning).

5. Verification
   Since every single file is assigned to exactly one category, adding
   up all six category counts should always equal the total number of
   files. This script checks that explicitly: if the two numbers don't
   match, it's a sign that a file was either missed or counted twice,
   and the result should not be trusted until that's resolved.
""")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    raw_df = load_data(CSV_FILE)
    df = clean_data(raw_df)
    df = categorize_files(df)

    counts, total_files = calculate_counts(df)

    print_summary(counts, total_files)
    for category in CATEGORY_ORDER:
        print_category_section(category.upper(), df, category)
    print_verification(counts, total_files)
    print_explanation()


if __name__ == "__main__":
    main()
