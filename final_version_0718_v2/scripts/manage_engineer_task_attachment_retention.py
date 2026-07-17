"""Preview and explicitly manage completed-task attachment retention."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "database"))

from db_connection import _fetch, get_connection  # noqa: E402


def candidates(conn, status="active"):
    return _fetch(conn, """SELECT attachment.attachment_id,attachment.task_id,
      attachment.relative_path,attachment.attachment_status,task.completed_at
      FROM engineer_task_attachment attachment JOIN engineer_task task USING(task_id)
      WHERE attachment.attachment_status=%s AND task.completed_at IS NOT NULL
      AND task.completed_at <= NOW()-INTERVAL '3 years' ORDER BY task.completed_at""", (status,))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preview", action="store_true", help="List candidates only (default)")
    group.add_argument("--mark-due", action="store_true", help="Mark active candidates retention_due")
    group.add_argument("--delete-confirmed", action="store_true", help="Delete retention_due files after explicit confirmation")
    args = parser.parse_args()
    root = Path(os.environ.get("ENGINEER_TASK_ATTACHMENT_ROOT", "")).resolve()
    conn = get_connection()
    try:
        rows = candidates(conn, "retention_due" if args.delete_confirmed else "active")
        print(f"mode={'delete-confirmed' if args.delete_confirmed else 'mark-due' if args.mark_due else 'preview'} candidates={len(rows)}")
        for row in rows:
            print(row["attachment_id"], row["task_id"], row["relative_path"])
        if not (args.mark_due or args.delete_confirmed):
            return
        if args.mark_due:
            for row in rows:
                _fetch(conn, """UPDATE engineer_task_attachment SET attachment_status='retention_due',retention_due_at=NOW()
                  WHERE attachment_id=%s AND attachment_status='active' RETURNING attachment_id""", (str(row["attachment_id"]),))
                _fetch(conn, """INSERT INTO engineer_task_event(task_id,event_type,actor_type,message,event_data)
                  VALUES(%s,'attachment_marked_retention_due','retention','Attachment reached retention due date',jsonb_build_object('attachmentId',%s::text)) RETURNING event_id""",
                  (str(row["task_id"]), str(row["attachment_id"])))
        else:
            if not os.environ.get("ENGINEER_TASK_ATTACHMENT_ROOT"):
                raise RuntimeError("ENGINEER_TASK_ATTACHMENT_ROOT is required")
            for row in rows:
                path = (root / row["relative_path"]).resolve()
                if root not in path.parents:
                    raise RuntimeError(f"Unsafe attachment path: {path}")
                path.unlink(missing_ok=True)
                _fetch(conn, """UPDATE engineer_task_attachment SET attachment_status='deleted',deleted_at=NOW(),deleted_by='retention-script'
                  WHERE attachment_id=%s AND attachment_status='retention_due' RETURNING attachment_id""", (str(row["attachment_id"]),))
                _fetch(conn, """INSERT INTO engineer_task_event(task_id,event_type,actor_type,message,event_data)
                  VALUES(%s,'attachment_deleted_by_retention','retention','Attachment file deleted after confirmation',jsonb_build_object('attachmentId',%s::text)) RETURNING event_id""",
                  (str(row["task_id"]), str(row["attachment_id"])))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
