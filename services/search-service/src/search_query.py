"""Построение Elasticsearch-запроса для поиска видео."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def escape_wildcard(value: str) -> str:
    """Экранирование спецсимволов wildcard/query_string."""
    return re.sub(r"([\\*?\"])", r"\\\1", value.strip())


def build_search_query(
    q: str,
    *,
    user_id: Optional[str] = None,
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Поиск по названию (в т.ч. подстрока), описанию, тегам, субтитрам.
    Только status=ready; учёт приватности.
    """
    q_clean = (q or "").strip()
    if not q_clean:
        return {"bool": {"filter": [{"term": {"status": "ready"}}], "must_not": [{"match_all": {}}]}}

    filters: List[Dict[str, Any]] = [{"term": {"status": "ready"}}]

    if tags:
        filters.append({"terms": {"tags": [t.strip() for t in tags.split(",") if t.strip()]}})

    if user_id:
        filters.append(
            {
                "bool": {
                    "should": [
                        {"term": {"is_private": False}},
                        {"term": {"user_id.keyword": user_id}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )
    else:
        filters.append({"term": {"is_private": False}})

    should: List[Dict[str, Any]] = [
        {
            "multi_match": {
                "query": q_clean,
                "fields": ["title^5", "description^2", "tags^3", "subtitles"],
                "type": "best_fields",
                "operator": "or",
                "fuzziness": "AUTO",
            }
        },
        {
            "match_phrase_prefix": {
                "title": {"query": q_clean, "boost": 4},
            }
        },
        {
            "simple_query_string": {
                "query": q_clean,
                "fields": ["title^4", "description", "tags"],
                "default_operator": "or",
                "analyze_wildcard": True,
            }
        },
    ]

    if len(q_clean) >= 2:
        escaped = escape_wildcard(q_clean).lower()
        should.append(
            {
                "wildcard": {
                    "title.keyword": {
                        "value": f"*{escaped}*",
                        "case_insensitive": True,
                        "boost": 6,
                    }
                }
            }
        )
        for word in q_clean.split():
            w = word.strip()
            if len(w) >= 2:
                ew = escape_wildcard(w).lower()
                should.append(
                    {
                        "wildcard": {
                            "title.keyword": {
                                "value": f"*{ew}*",
                                "case_insensitive": True,
                                "boost": 3,
                            }
                        }
                    }
                )

    return {
        "bool": {
            "filter": filters,
            "should": should,
            "minimum_should_match": 1,
        }
    }
