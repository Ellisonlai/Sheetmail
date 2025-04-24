# cli.py — SheetMail 批次寄信 CLI
import argparse

from sheetmail import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SheetMail CLI")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只列印動作，不實際寄信／寫回 Google Sheet",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
