"""Serve local Label Studio images with permissive CORS headers.

This helper is intended for operator annotation sessions where Label Studio
loads image URLs from ``http://localhost:<port>/<fixture_id>.jpg``.
"""

from __future__ import annotations

import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler that allows browser-based Label Studio image fetches."""

    def end_headers(self) -> None:
        """Attach CORS headers to every response.

        Returns:
            None.
        """

        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        """Return a CORS preflight response.

        Returns:
            None.
        """

        self.send_response(204)
        self.end_headers()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        Parsed command-line arguments.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, help="Directory to serve.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8090, help="Bind port.")
    return parser.parse_args()


def main() -> int:
    """Run the CORS static image server.

    Returns:
        Process exit code.

    Raises:
        FileNotFoundError: If the requested directory does not exist.
        NotADirectoryError: If the requested path is not a directory.
    """

    args = parse_args()
    directory = Path(args.directory).expanduser().resolve()
    if not directory.exists():
        raise FileNotFoundError(directory)
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    os.chdir(directory)
    server = ThreadingHTTPServer((args.host, args.port), CORSRequestHandler)
    print(f"serving {directory} at http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
