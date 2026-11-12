from typing import Optional
import psycopg2.extras


def get_troubleshooting_matrix(conn, asset_type: Optional[str] = None, state: Optional[str] = None) -> dict:
    """Return state → cause/countermeasure mapping.

    DB versionB still uses issue_catalog / issue_id internally, but the
    service/API exposes the concept as state to match the monitoring flow:
    sensor value → state → alert_event → troubleshooting.
    """
    sql = """
      SELECT cc.component_id,
             cc.display_name AS component_name,
             ic.issue_id AS state,
             ic.display_name AS state_name,
             ic.description AS state_description,
             ic.severity,
             sc.solution_id AS countermeasure_id,
             sc.description AS countermeasure,
             sc.downtime_estimate_min,
             sc.skill_required,
             m.relevance_rank,
             m.effectiveness_pct
      FROM component_issue_solution_map m
      JOIN component_catalog cc ON m.component_id = cc.component_id
      JOIN issue_catalog ic ON m.issue_id = ic.issue_id
      JOIN solution_catalog sc ON m.solution_id = sc.solution_id
      WHERE (%(asset_type)s IS NULL OR cc.component_id = %(asset_type)s)
        AND (%(state)s IS NULL OR ic.issue_id = %(state)s)
      ORDER BY cc.component_id, ic.severity DESC, m.relevance_rank;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, {"asset_type": asset_type, "state": state})
        rows = [dict(r) for r in cur.fetchall()]
    return {"total": len(rows), "rows": rows}


def get_state_recommendations(conn, state: str, station: Optional[str] = None) -> dict:
    """Return recommendations for a single state."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT issue_id AS state,
                   display_name AS state_name,
                   description AS state_description,
                   severity
            FROM issue_catalog
            WHERE issue_id = %s
            """,
            (state,),
        )
        state_row = dict(cur.fetchone() or {})
        cur.execute(
            """
            SELECT sc.solution_id AS countermeasure_id,
                   sc.description AS countermeasure,
                   sc.downtime_estimate_min,
                   sc.skill_required,
                   m.relevance_rank,
                   m.effectiveness_pct,
                   cc.component_id,
                   cc.display_name AS component_name
            FROM component_issue_solution_map m
            JOIN solution_catalog sc ON m.solution_id = sc.solution_id
            JOIN component_catalog cc ON m.component_id = cc.component_id
            WHERE m.issue_id = %s
            ORDER BY m.relevance_rank
            """,
            (state,),
        )
        recommendations = [dict(r) for r in cur.fetchall()]
    return {"state": state_row, "station": station, "recommendations": recommendations}


# Backward-compatible aliases for older notebooks or clients.
def get_issue_recommendations(conn, issue_type: str, station: Optional[str] = None) -> dict:
    return get_state_recommendations(conn, issue_type, station)
