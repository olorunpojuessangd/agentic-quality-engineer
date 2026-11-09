"""Exa retrieval layer for machining standards and root-cause literature.

Defaults to zero-cost offline cached fixtures (data/fixtures/exa_cache.json).
Only makes live requests when explicitly enabled via live=True or EXA_LIVE=true.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = ROOT_DIR / "data" / "fixtures" / "exa_cache.json"


class ExaRetriever:
    """Retrieves authoritative external engineering domain knowledge via Exa."""

    def __init__(self, api_key: Optional[str] = None, live: Optional[bool] = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY", "")
        if live is None:
            self.live = os.getenv("EXA_LIVE", "false").strip().lower() in ("true", "1", "yes")
        else:
            self.live = live

        self._cached_data = self._load_cache()
        self._live_client = None

        if self.live:
            if not self.api_key:
                raise ValueError(
                    "EXA_LIVE is enabled but no EXA_API_KEY was provided in the environment or constructor."
                )
            try:
                from exa_py import Exa
                self._live_client = Exa(api_key=self.api_key)
            except ImportError:
                pass

    def _load_cache(self) -> Dict[str, Any]:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def retrieve_for_defect(
        self,
        feature: str,
        hypothesis_key: str,
        defect_description: str,
    ) -> Dict[str, Any]:
        """Retrieve external standards and domain explanation for a given defect hypothesis.

        Parameters:
            feature: The geometric feature (e.g. 'bore_diameter', 'flatness', 'hole_position')
            hypothesis_key: e.g. 'tool_wear', 'thermal', 'fixture_misalignment', 'isolated_outlier'
            defect_description: Human-readable description from the defect report

        Returns:
            Dictionary containing query, results (title, url, text, highlights, standard_reference),
            and retrieval_source ('offline_cache' or 'live_exa_api').
        """
        # Safe default: offline fixture cache (zero cost, deterministic)
        if not self.live or not self._live_client:
            cached = self._cached_data.get(hypothesis_key)
            if cached:
                return {
                    "source": "offline_cache",
                    "cost_cents": 0.0,
                    "query": cached.get("query", ""),
                    "results": cached.get("results", []),
                }
            # Fallback if unknown key
            return {
                "source": "offline_cache",
                "cost_cents": 0.0,
                "query": f"CNC machining {feature} {hypothesis_key} quality root cause",
                "results": [],
            }

        # Guardrailed Live API query (only invoked when live=True)
        query = self._build_query(feature, hypothesis_key, defect_description)
        try:
            response = self._live_client.search_and_contents(
                query=query,
                num_results=2,
                text={"max_characters": 1000},
                highlights={"num_sentences": 2},
            )
            parsed_results = []
            for item in getattr(response, "results", []):
                parsed_results.append({
                    "title": getattr(item, "title", "Untitled Document"),
                    "url": getattr(item, "url", ""),
                    "published_date": getattr(item, "published_date", None),
                    "author": getattr(item, "author", None),
                    "score": getattr(item, "score", None),
                    "text": getattr(item, "text", "")[:1000],
                    "highlights": getattr(item, "highlights", []),
                    "standard_reference": f"Exa Neural Search: {query}",
                })
            return {
                "source": "live_exa_api",
                "query": query,
                "results": parsed_results,
            }
        except Exception as exc:
            # Fall back gracefully to cache on any network/API error
            cached = self._cached_data.get(hypothesis_key, {})
            return {
                "source": "live_fallback_to_cache",
                "error": str(exc),
                "query": query,
                "results": cached.get("results", []),
            }

    @staticmethod
    def _build_query(feature: str, hypothesis_key: str, description: str) -> str:
        """Construct domain-specific search query for Exa's neural search engine."""
        query_map = {
            "tool_wear": "CNC boring bar tool wear bore diameter undersize internal turning tolerance",
            "thermal": "CNC milling coolant temperature thermal expansion part flatness warp tolerance",
            "fixture_misalignment": "CNC fixture reinstallation alignment datum shift true position hole location error",
            "isolated_outlier": "CNC isolated single part dimensional outlier inspection CMM",
        }
        return query_map.get(hypothesis_key, f"CNC machining defect {feature} {description}")
