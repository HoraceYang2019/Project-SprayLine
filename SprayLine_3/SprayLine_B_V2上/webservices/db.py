"""Local DB adapter for Shao-Yu service integration tests.

本檔案不是正式 API Server，也不是要取代余宇承負責的 Database / DB API。
它只是讓少榆端的 Future / Monitoring / EventRule / Troubleshooting service
在本機或整合測試時，可以暫時連到 DB 驗證流程。

正式整合時，可將這裡替換成余宇承提供的 DB API client。
"""

import os
import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.getenv("SPRAYLINE_DB_HOST", "localhost"),
        port=int(os.getenv("SPRAYLINE_DB_PORT", "5432")),
        dbname=os.getenv("SPRAYLINE_DB_NAME", "sprayline"),
        user=os.getenv("SPRAYLINE_DB_USER", "postgres"),
        password=os.getenv("SPRAYLINE_DB_PASSWORD", "postgres"),
    )
