"""Minimal 1-request verification script to test your Exa API key safely.

Usage:
  python3 scripts/verify_exa_key.py
  (or pass key as argument: python3 scripts/verify_exa_key.py exa_api_key_here)

Guarantees:
  - Exactly 1 API call is made.
  - Minimal payload (num_results=1).
  - Verifies key validity and shows live Exa response format without recurring charges.
"""
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass


def test_single_call(api_key: str):
    print("=" * 65)
    print(" EXA API KEY VERIFICATION (SINGLE 1-CALL SMOKE TEST)")
    print("=" * 65)
    print(f"API Key prefix: {api_key[:8]}... (length: {len(api_key)})")

    try:
        from exa_py import Exa
    except ImportError:
        print("Error: 'exa-py' is not installed. Install it with: pip install exa-py")
        sys.exit(1)

    print("\nSending 1 minimal query to Exa...")
    query = "ISO 3685 tool-life testing with single-point turning tools"
    print(f"Query: '{query}'")

    try:
        exa = Exa(api_key=api_key)
        # Canonical Exa search with token-efficient highlights
        response = exa.search(
            query=query,
            type="auto",
            contents={"highlights": True},
            num_results=1,
        )

        results = getattr(response, "results", [])
        if not results:
            print("\n[!] API key accepted, but 0 results returned.")
            return

        top = results[0]
        print("\n[SUCCESS] Exa API responded successfully!")
        print("-" * 65)
        print(f" Title     : {getattr(top, 'title', 'N/A')}")
        print(f" URL       : {getattr(top, 'url', 'N/A')}")
        print(f" Score     : {getattr(top, 'score', 'N/A')}")
        highlights = getattr(top, "highlights", [])
        if highlights:
            print(f" Highlight : {highlights[0]}")
        print("-" * 65)
        print("Total API calls made: 1. Your key is verified and operational.")

    except Exception as exc:
        print(f"\n[FAILED] Exa API request failed: {exc}")
        sys.exit(1)


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else os.getenv("EXA_API_KEY")
    if not key or key == "your_exa_api_key_here":
        print("Usage:")
        print("  1. Add EXA_API_KEY=your_key to a .env file in project root")
        print("  2. Or pass key directly: python3 scripts/verify_exa_key.py <YOUR_KEY>")
        sys.exit(1)

    test_single_call(key)


if __name__ == "__main__":
    main()

