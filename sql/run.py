"""Run the SQL analytics queries against the AQI database and print the results.

Uses only the Python standard library. The database is opened read-only, and the
shared views are TEMP views, so data/aqi.db is never modified.

Examples (from the repo root):
    python sql/run.py                       # run all 15 queries
    python sql/run.py --only 3 6 8          # run selected queries
    python sql/run.py --markdown --only 3   # print results as Markdown tables
    python sql/run.py --csv-dir out/        # also save every result as CSV
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent
DEFAULT_DB = SQL_DIR.parent / "data" / "aqi.db"
MIN_SQLITE = (3, 25, 0)          # window functions


def query_files() -> list[Path]:
    """The numbered query files (01_..., 02_...), excluding the 00_setup views."""
    return sorted(p for p in SQL_DIR.glob("[0-9][0-9]_*.sql") if not p.name.startswith("00_"))


def title_of(path: Path) -> str:
    """First comment line of a query file, e.g. 'Q03  Station leaderboard ...'."""
    first = path.read_text(encoding="utf-8").splitlines()[0]
    return first.lstrip("- ").strip()


def connect(db_path: Path) -> sqlite3.Connection:
    if sqlite3.sqlite_version_info < MIN_SQLITE:
        sys.exit(f"SQLite {sqlite3.sqlite_version} is too old; window functions need 3.25 or newer.")
    if not db_path.exists():
        sys.exit(f"Database not found: {db_path}. Run python src/backfill.py first.")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.executescript((SQL_DIR / "00_setup.sql").read_text(encoding="utf-8"))
    return con


def run_query(con: sqlite3.Connection, path: Path) -> tuple[list[str], list[tuple]]:
    cur = con.execute(path.read_text(encoding="utf-8"))
    columns = [d[0] for d in cur.description]
    return columns, cur.fetchall()


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def format_plain(columns: list[str], rows: list[tuple]) -> str:
    cells = [[as_text(v) for v in row] for row in rows]
    widths = [max(len(c), *(len(r[i]) for r in cells)) if cells else len(c) for i, c in enumerate(columns)]
    line = lambda parts: "  ".join(p.ljust(w) for p, w in zip(parts, widths)).rstrip()
    out = [line(columns), line(["-" * w for w in widths])]
    out += [line(r) for r in cells]
    return "\n".join(out)


def format_markdown(columns: list[str], rows: list[tuple]) -> str:
    out = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        out.append("| " + " | ".join(as_text(v).replace("|", "/") for v in row) + " |")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AQI SQL analytics queries.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="path to aqi.db (default: data/aqi.db)")
    parser.add_argument("--only", type=int, nargs="+", metavar="N", help="run only these query numbers, e.g. 3 6 8")
    parser.add_argument("--markdown", action="store_true", help="print results as Markdown tables")
    parser.add_argument("--csv-dir", type=Path, help="also write each result to <dir>/<query>.csv")
    args = parser.parse_args()

    files = query_files()
    if args.only:
        wanted = {f"{n:02d}" for n in args.only}
        files = [p for p in files if p.name[:2] in wanted]
        if not files:
            sys.exit("No query matches --only.")

    con = connect(args.db)
    if args.csv_dir:
        args.csv_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        columns, rows = run_query(con, path)
        heading = title_of(path)
        print(f"\n### {heading}\n" if args.markdown else f"\n=== {heading} ===")
        print(format_markdown(columns, rows) if args.markdown else format_plain(columns, rows))
        if args.csv_dir:
            with open(args.csv_dir / f"{path.stem}.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
    con.close()


if __name__ == "__main__":
    main()
