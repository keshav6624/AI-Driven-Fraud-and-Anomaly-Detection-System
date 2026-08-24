"""NL2SQL Assistant — natural language interface to query MPLADS data.

Uses rule-based intent classification + SQL template generation.
No external LLM dependency — works offline for hackathon reliability.

Supported intents:
  - count/state/filter: aggregate queries
  - risk/anomaly: ML-driven queries
  - search/find: member lookup
  - compare: peer comparisons
  - summary: dashboard-style summaries
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text


@dataclass
class AssistantResponse:
    answer: str
    sql: str
    intent: str
    result_count: int
    data: list[dict] | None = None
    visualization_hint: str | None = None


# Intent patterns
INTENT_PATTERNS = [
    # Count patterns
    (r"how many (mp|member|parliament)", "count_members"),
    (r"total (number of|count)", "count_members"),
    (r"count.*member", "count_members"),
    # Risk patterns
    (r"(high|risk|critical).*risk", "risk_filter"),
    (r"anomal(y|ies|ous)", "anomaly_list"),
    (r"flagged|suspicious", "anomaly_list"),
    # State patterns — check before search since "find MP from X" is state query
    (r"(find|search|show|get|who|which).*from\s+", "state_query"),
    (r"(state|region|constituency)", "state_query"),
    # Search patterns
    (r"(find|search|show|get).*mp|member", "search_member"),
    (r"(who|which mp)", "search_member"),
    # Compare patterns
    (r"compar(e|ison|ing)", "compare"),
    (r"versus|vs\.?|against", "compare"),
    # Summary patterns
    (r"(summary|overview|dashboard|summarize)", "summary"),
    (r"(top|highest|most|lowest|least)", "rankings"),
    # Duplicate patterns
    (r"duplic(a|ate|tion)", "duplicates"),
    # Amount patterns
    (r"(allocated|allocation|amount|fund)", "amount_query"),
    (r"₹|crore|cr|lakh|rs\.?", "amount_query"),
]

STATE_ABBREVS = {
    "ap": "ANDHRA PRADESH", "ar": "ARUNACHAL PRADESH", "as": "ASSAM",
    "br": "BIHAR", "cg": "CHHATTISGARH", "ga": "GOA", "gj": "GUJARAT",
    "hr": "HARYANA", "hp": "HIMACHAL PRADESH", "jh": "JHARKHAND",
    "ka": "KARNATAKA", "kl": "KERALA", "mp": "MADHYA PRADESH",
    "mh": "MAHARASHTRA", "mn": "MANIPUR", "ml": "MEGHALAYA",
    "mz": "MIZORAM", "nl": "NAGALAND", "od": "ODISHA", "pb": "PUNJAB",
    "rj": "RAJASTHAN", "sk": "SIKKIM", "tn": "TAMIL NADU",
    "tg": "TELANGANA", "tr": "TRIPURA", "up": "UTTAR PRADESH",
    "uk": "UTTARAKHAND", "wb": "WEST BENGAL", "dl": "DELHI",
    "jk": "JAMMU AND KASHMIR", "la": "LADAKH", "py": "PUDUCHERRY",
    "ch": "CHANDIGARH", "dn": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "ld": "LAKSHADWEEP", "an": "ANDAMAN AND NICOBAR ISLANDS",
}


def _extract_state(query: str) -> str | None:
    q = query.upper()
    # Check abbreviations
    for abbr, full in STATE_ABBREVS.items():
        if re.search(rf'\b{abbr}\b', q):
            return full
    # Check full names (case-insensitive)
    q_lower = query.lower()
    for full in STATE_ABBREVS.values():
        if full.lower() in q_lower:
            return full
    return None


def _extract_name(query: str) -> str | None:
    # Try to extract a name after common patterns
    patterns = [
        r"(?:find|search|show|get|who is|details? for)\s+(?:mp|member|the mp)?\s*[:\-]?\s*(.+?)(?:\s+from|\s+in|\s+for|\s*$)",
        r"(?:mp|member)\s+[:\-]?\s*(.+?)(?:\s+from|\s+in|\s+for|\s*$)",
    ]
    for p in patterns:
        m = re.search(p, query, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) > 2:
                return name
    return None


def _classify_intent(query: str) -> str:
    q = query.lower()
    for pattern, intent in INTENT_PATTERNS:
        if re.search(pattern, q):
            return intent
    return "general_query"


def _build_sql(intent: str, query: str, state: str | None, name: str | None) -> str:
    # Convert state to title case for DB matching
    state_tc = state.title() if state else None
    if intent == "count_members":
        if state_tc:
            return f"""SELECT COUNT(*) as count FROM members m
                       JOIN states s ON m.state_id = s.state_id
                       WHERE s.name = '{state_tc}'"""
        return "SELECT COUNT(*) as count FROM members"

    elif intent == "risk_filter":
        level = "HIGH"
        if "critical" in query.lower():
            level = "CRITICAL"
        elif "medium" in query.lower():
            level = "MEDIUM"
        return f"""SELECT m.mp_name, s.name as state, c.name as constituency,
                   r.risk_score, r.risk_level
                   FROM members m
                   JOIN states s ON m.state_id = s.state_id
                   JOIN constituencies c ON m.constituency_id = c.constituency_id
                   JOIN risk_scores r ON m.member_id = r.member_id
                   WHERE r.risk_level = '{level}'
                   ORDER BY r.risk_score DESC
                   LIMIT 20"""

    elif intent == "anomaly_list":
        return """SELECT m.mp_name, s.name as state, c.name as constituency,
                  a.ensemble_score, a.anomaly_votes, a.is_anomaly
                  FROM members m
                  JOIN states s ON m.state_id = s.state_id
                  JOIN constituencies c ON m.constituency_id = c.constituency_id
                  JOIN member_anomalies a ON m.member_id = a.member_id
                  WHERE a.is_anomaly = 1
                  ORDER BY a.ensemble_score DESC
                  LIMIT 20"""

    elif intent == "search_member":
        search_name = name or query
        # Remove common words
        for word in ["find", "search", "show", "get", "who", "is", "the", "mp", "member", "from", "in"]:
            search_name = re.sub(rf'\b{word}\b', '', search_name, flags=re.IGNORECASE)
        search_name = search_name.strip()
        if not search_name:
            search_name = query
        return f"""SELECT m.mp_name, s.name as state, c.name as constituency,
                   e.allocated_amount, r.risk_score, r.risk_level, a.is_anomaly
                   FROM members m
                   JOIN states s ON m.state_id = s.state_id
                   JOIN constituencies c ON m.constituency_id = c.constituency_id
                   LEFT JOIN entitlements e ON m.member_id = e.member_id
                   LEFT JOIN risk_scores r ON m.member_id = r.member_id
                   LEFT JOIN member_anomalies a ON m.member_id = a.member_id
                   WHERE m.mp_name LIKE '%{search_name.upper()}%'
                   OR m.mp_name_clean LIKE '%{search_name.lower()}%'
                   ORDER BY m.mp_name
                   LIMIT 10"""

    elif intent == "state_query":
        if state_tc:
            return f"""SELECT m.mp_name, c.name as constituency, e.allocated_amount,
                       r.risk_score, r.risk_level
                       FROM members m
                       JOIN states s ON m.state_id = s.state_id
                       JOIN constituencies c ON m.constituency_id = c.constituency_id
                       LEFT JOIN entitlements e ON m.member_id = e.member_id
                       LEFT JOIN risk_scores r ON m.member_id = r.member_id
                       WHERE s.name = '{state_tc}'
                       ORDER BY r.risk_score DESC
                       LIMIT 20"""
        return """SELECT s.name, COUNT(*) as member_count,
                  SUM(e.allocated_amount) as total_allocated
                  FROM states s
                  JOIN members m ON s.state_id = m.state_id
                  JOIN entitlements e ON m.member_id = e.member_id
                  GROUP BY s.name
                  ORDER BY total_allocated DESC
                  LIMIT 36"""

    elif intent == "rankings":
        if "top" in query.lower() or "highest" in query.lower():
            return """SELECT m.mp_name, s.name as state, e.allocated_amount,
                     r.risk_score
                     FROM members m
                     JOIN states s ON m.state_id = s.state_id
                     JOIN entitlements e ON m.member_id = e.member_id
                     JOIN risk_scores r ON m.member_id = r.member_id
                     ORDER BY e.allocated_amount DESC
                     LIMIT 10"""
        return """SELECT m.mp_name, s.name as state, e.allocated_amount,
                 r.risk_score
                 FROM members m
                 JOIN states s ON m.state_id = s.state_id
                 JOIN entitlements e ON m.member_id = e.member_id
                 JOIN risk_scores r ON m.member_id = r.member_id
                 ORDER BY e.allocated_amount ASC
                 LIMIT 10"""

    elif intent == "duplicates":
        return """SELECT mp_name_a, mp_name_b, state_a, state_b,
                 overall_similarity, potential_duplicate, duplicate_reason
                 FROM duplicate_pairs_view
                 WHERE potential_duplicate = 1
                 ORDER BY overall_similarity DESC
                 LIMIT 10"""

    elif intent == "summary":
        return """SELECT
                  (SELECT COUNT(*) FROM members) as total_members,
                  (SELECT SUM(allocated_amount) FROM entitlements) as total_allocated,
                  (SELECT COUNT(*) FROM member_anomalies WHERE is_anomaly = 1) as anomalies,
                  (SELECT risk_level || ': ' || COUNT(*) FROM risk_scores GROUP BY risk_level) as risk_breakdown"""

    elif intent == "compare":
        return """SELECT s.name, COUNT(*) as members,
                  AVG(e.allocated_amount) as avg_allocation,
                  AVG(r.risk_score) as avg_risk
                  FROM states s
                  JOIN members m ON s.state_id = m.state_id
                  JOIN entitlements e ON m.member_id = e.member_id
                  JOIN risk_scores r ON m.member_id = r.member_id
                  GROUP BY s.name
                  ORDER BY avg_risk DESC
                  LIMIT 15"""

    elif intent == "amount_query":
        if state_tc:
            return f"""SELECT m.mp_name, e.allocated_amount, s.name as state
                      FROM members m
                      JOIN entitlements e ON m.member_id = e.member_id
                      JOIN states s ON m.state_id = s.state_id
                      WHERE s.name = '{state_tc}'
                      AND e.allocated_amount IS NOT NULL
                      ORDER BY e.allocated_amount DESC
                      LIMIT 10"""
        return """SELECT m.mp_name, s.name as state, e.allocated_amount
                 FROM members m
                 JOIN entitlements e ON m.member_id = e.member_id
                 JOIN states s ON m.state_id = s.state_id
                 WHERE e.allocated_amount IS NOT NULL
                 ORDER BY e.allocated_amount DESC
                 LIMIT 10"""

    # Default: general info
    return """SELECT m.mp_name, s.name as state, c.name as constituency,
             e.allocated_amount, r.risk_level
             FROM members m
             JOIN states s ON m.state_id = s.state_id
             JOIN constituencies c ON m.constituency_id = c.constituency_id
             LEFT JOIN entitlements e ON m.member_id = e.member_id
             LEFT JOIN risk_scores r ON m.member_id = r.member_id
             ORDER BY m.member_id
             LIMIT 10"""


def _format_answer(intent: str, rows: list[dict], query: str) -> str:
    if not rows:
        return "No results found for your query."

    if intent == "count_members":
        count = rows[0].get("count", 0)
        state = _extract_state(query)
        state_tc = state.title() if state else None
        if state_tc:
            return f"There are **{count}** Members of Parliament from **{state_tc}** in the current dataset."
        return f"There are **{count}** Members of Parliament in the current dataset."

    if intent == "risk_filter":
        level = "HIGH"
        if "critical" in query.lower():
            level = "CRITICAL"
        names = [f"- {r['mp_name']} ({r['state']}) — Risk: {r['risk_score']}" for r in rows[:10]]
        return f"Found **{len(rows)}** MPs with **{level}** risk level:\n" + "\n".join(names)

    if intent == "anomaly_list":
        names = [f"- {r['mp_name']} ({r['state']}) — Score: {r['ensemble_score']}" for r in rows[:10]]
        return f"Found **{len(rows)}** anomalous allocations:\n" + "\n".join(names)

    if intent == "search_member":
        if len(rows) == 1:
            r = rows[0]
            return (f"**{r['mp_name']}** — {r['constituency']}, {r['state']}\n"
                    f"Allocation: ₹{r.get('allocated_amount', 'N/A')}\n"
                    f"Risk: {r.get('risk_level', 'N/A')} ({r.get('risk_score', 'N/A')})")
        names = [f"- {r['mp_name']} ({r['state']})" for r in rows]
        return f"Found **{len(rows)}** matching MPs:\n" + "\n".join(names)

    if intent == "summary":
        r = rows[0]
        return (f"**MPLADS Dashboard Summary**\n"
                f"- Total MPs: {r.get('total_members', 'N/A')}\n"
                f"- Total Allocated: ₹{r.get('total_allocated', 0):,.0f}\n"
                f"- Anomalies Detected: {r.get('anomalies', 'N/A')}")

    if intent == "rankings":
        names = [f"{i+1}. {r['mp_name']} ({r['state']}) — ₹{r.get('allocated_amount', 0)/1e7:.2f} Cr"
                 for i, r in enumerate(rows[:10])]
        return "**Top Allocations:**\n" + "\n".join(names)

    # Generic
    if len(rows) <= 5:
        lines = []
        for r in rows:
            parts = [f"{k}: {v}" for k, v in r.items() if v is not None]
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)
    return f"Found {len(rows)} results. Showing first {min(5, len(rows))}."


def query(db: Session, user_query: str, user_id: int | None = None) -> AssistantResponse:
    """Process a natural language query against the MPLADS database."""
    intent = _classify_intent(user_query)
    state = _extract_state(user_query)
    name = _extract_name(user_query)

    sql = _build_sql(intent, user_query, state, name)

    try:
        result = db.execute(text(sql))
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        # Convert non-serializable types
        for row in rows:
            for k, v in row.items():
                if hasattr(v, '__class__') and v.__class__.__name__ == 'Decimal':
                    row[k] = float(v)
    except Exception as e:
        return AssistantResponse(
            answer=f"Error executing query: {str(e)}",
            sql=sql,
            intent=intent,
            result_count=0,
        )

    answer = _format_answer(intent, rows, user_query)

    # Determine visualization hint
    viz = None
    if intent in ("state_query", "compare"):
        viz = "bar_chart"
    elif intent in ("risk_filter", "anomaly_list"):
        viz = "table"
    elif intent == "summary":
        viz = "dashboard"

    # Log the query
    if user_id:
        try:
            from backend.app.models.orm import AssistantQueryLog
            log = AssistantQueryLog(
                user_id=user_id,
                question=user_query,
                intent=intent,
                sql_text=sql,
                result_count=len(rows),
            )
            db.add(log)
            db.commit()
        except Exception:
            pass

    return AssistantResponse(
        answer=answer,
        sql=sql,
        intent=intent,
        result_count=len(rows),
        data=rows[:20] if rows else None,
        visualization_hint=viz,
    )
