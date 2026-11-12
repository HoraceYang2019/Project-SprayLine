#!/usr/bin/env python3
"""Simple local static server for Spray Line Manager UI.

Usage:
  python3 server.py
  python3 server.py --host 0.0.0.0 --port 3000
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import posixpath
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


class SprayManagerRequestHandler(SimpleHTTPRequestHandler):
    """Serve files from the project folder with safe path handling."""

    server_version = "SprayManagerPythonServer/1.0"

    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def translate_path(self, path: str) -> str:
        """Map URL paths to files under the configured static root only."""
        parsed_path = urlparse(path).path
        clean_path = posixpath.normpath(unquote(parsed_path))
        parts = [part for part in clean_path.split("/") if part and part not in (os.curdir, os.pardir)]

        root = Path(self.directory).resolve()
        target = root.joinpath(*parts).resolve()

        if not str(target).startswith(str(root)):
            return str(root / "index.html")

        if target.is_dir():
            return str(target / "index.html")

        if parsed_path == "/":
            return str(root / "index.html")

        return str(target)

    def guess_type(self, path: str) -> str:
        content_type, _ = mimetypes.guess_type(path)
        if content_type:
            if content_type.startswith("text/") or content_type in {
                "application/javascript",
                "application/json",
                "image/svg+xml",
            }:
                return f"{content_type}; charset=utf-8"
            return content_type

        suffix = Path(path).suffix.lower()
        fallback_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        return fallback_types.get(suffix, "application/octet-stream")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - inherited name
        print(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Spray Line Manager UI static server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Use 0.0.0.0 for LAN access.")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind.")
    parser.add_argument(
        "--directory",
        default=str(Path(__file__).resolve().parent),
        help="Static file directory. Defaults to the folder containing server.py.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.directory).resolve()

    if not root.exists():
        raise SystemExit(f"Static directory does not exist: {root}")

    handler = lambda *handler_args, **handler_kwargs: SprayManagerRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(root),
        **handler_kwargs,
    )

    server = ThreadingHTTPServer((args.host, args.port), handler)
    url_host = "127.0.0.1" if args.host in ("0.0.0.0", "") else args.host
    print(f"Dashboard is running at http://{url_host}:{args.port}")
    print(f"Serving files from: {root}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
