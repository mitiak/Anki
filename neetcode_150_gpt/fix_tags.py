import csv
import re
import sys
from pathlib import Path

def normalize_tag_cell(cell: str) -> str:
    """
    Transform only the tags field:
      - split tags by commas (treat commas as separators)
      - lowercase all tags
      - replace internal spaces with underscores (multi-word -> underscores)
      - deduplicate while preserving order
      - join back using SINGLE SPACES (Anki-style)
    NOTE: We do NOT touch semicolons here; semicolons are the CSV delimiter, not part of the field.
    """
    if cell is None:
        return ""
    s = str(cell)

    # Split primarily on commas; if no comma present, also allow whitespace-separated tags
    parts = [p for p in re.split(r"\s*,\s*", s) if p != ""]
    if not parts:
        parts = [p for p in re.split(r"\s+", s.strip()) if p != ""]

    cleaned = []
    for p in parts:
        # collapse any internal whitespace, then convert to lowercase and underscores
        p = re.sub(r"\s+", " ", p.strip())
        if not p:
            continue
        p = p.lower().replace(" ", "_")
        cleaned.append(p)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for t in cleaned:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    # Anki expects space-separated tags
    return " ".join(deduped)

def process_csv_file(path: Path) -> Path:
    """
    Read a semicolon-separated CSV, modify only the Tags column, and write <name>_fixed.csv.
    All other fields are written back as-is. The CSV delimiter remains ';'.
    """
    out_path = path.with_name(path.stem + "_fixed.csv")

    # Open with csv module using delimiter=';' to preserve your separator.
    with path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.reader(f_in, delimiter=";", quotechar='"', skipinitialspace=False)
        rows = list(reader)

    if not rows:
        # Empty file -> just copy structure
        with out_path.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            pass
        return out_path

    header = rows[0]
    # Find Tags column (case-insensitive)
    tags_idx = None
    for i, col in enumerate(header):
        if col.strip().lower() == "tags":
            tags_idx = i
            break

    # If no Tags column, write back unchanged
    if tags_idx is None:
        with out_path.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerows(rows)
        return out_path

    # Modify only the Tags column on data rows
    fixed_rows = [header]
    for r in rows[1:]:
        # Ensure row has enough columns (ragged rows safety)
        if tags_idx < len(r):
            original = r[tags_idx]
            r = list(r)  # copy to mutate this row only
            r[tags_idx] = normalize_tag_cell(original)
        fixed_rows.append(r)

    # Write with the same semicolon delimiter; only Tags column is changed.
    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerows(fixed_rows)

    return out_path

def process_folder(folder: str):
    root = Path(folder)
    if not root.exists() or not root.is_dir():
        print(f"Error: '{folder}' is not a folder")
        sys.exit(1)

    report = []
    for csv_path in sorted(root.glob("*.csv")):
        try:
            out_path = process_csv_file(csv_path)
            report.append((csv_path.name, "ok", out_path.name))
        except Exception as e:
            report.append((csv_path.name, f"error: {e}", ""))

    print("Processing report:")
    for row in report:
        print(row)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_anki_tags_semicolon_only_tags.py <folder_path>")
        sys.exit(1)
    process_folder(sys.argv[1])
