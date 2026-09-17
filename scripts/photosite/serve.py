"""A local development server: serves dist/, rebuilds when content changes.

Usage from build.py:

    serve(rebuild=build_once, dist=DIST, watch=[CONTENT, TEMPLATES, STATIC])

The watcher is deliberately simple. Every half second it walks the watched
folders and compares file modification times with the previous walk. That
is fast enough for a few hundred files and needs no third-party package.
"""

import http.server
import os
import sys
import threading
import time
import traceback
from pathlib import Path


def snapshot(folders):
    """{path: mtime} for every file under the given folders."""
    seen = {}
    for folder in folders:
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if name.startswith("."):
                    continue
                path = os.path.join(root, name)
                try:
                    seen[path] = os.stat(path).st_mtime
                except FileNotFoundError:
                    pass
    return seen


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from dist/ and stay quiet unless something goes wrong."""

    def log_message(self, format, *args):  # noqa: A002 (name fixed by the base class)
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(format, *args)

    def end_headers(self):
        # Never let the browser cache during development.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve(rebuild, dist, watch, port=8000, extra_routes=None, restart_on=()):
    """Run the server until Ctrl-C. `rebuild` is called on every change.

    Python does not reload modules that are already imported, so a change to
    anything under a `restart_on` folder (the build scripts themselves)
    restarts this whole process instead of rebuilding in place.
    """
    dist = Path(dist)
    handler = type("Handler", (QuietHandler,), {})
    handler.extra_routes = extra_routes or {}

    def find_route(self):
        """Exact path match first; otherwise the longest registered prefix
        that ends in '/' (so '/_curate/img/' serves everything below it)."""
        path = self.path.split("?")[0]
        if path in self.extra_routes:
            return self.extra_routes[path]
        prefixes = [k for k in self.extra_routes if k.endswith("/") and path.startswith(k) and k != path]
        return self.extra_routes[max(prefixes, key=len)] if prefixes else None

    def do_GET(self):
        route = self.find_route()
        if route:
            return route(self)
        return QuietHandler.do_GET(self)

    def do_POST(self):
        route = self.find_route()
        if route:
            return route(self)
        self.send_error(404)

    handler.find_route = find_route

    handler.do_GET = do_GET
    handler.do_POST = do_POST

    def make_handler(*args, **kwargs):
        return handler(*args, directory=str(dist), **kwargs)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), make_handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Serving {dist} at http://127.0.0.1:{port}/  (Ctrl-C to stop)")

    restart_dirs = [str(Path(d).resolve()) for d in restart_on]
    before = snapshot(list(watch) + list(restart_on))
    try:
        while True:
            time.sleep(0.5)
            now = snapshot(list(watch) + list(restart_on))
            if now != before:
                changed = [p for p in now if now[p] != before.get(p)] + [p for p in before if p not in now]
                if any(os.path.abspath(c).startswith(tuple(restart_dirs)) for c in changed):
                    print(f"\nBuild script changed ({os.path.relpath(changed[0])}); restarting")
                    server.shutdown()
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                print(f"\nChange detected ({os.path.relpath(changed[0])}{', ...' if len(changed) > 1 else ''}); rebuilding")
                before = now        # anything written during the rebuild is picked up next tick
                try:
                    rebuild()
                except Exception:   # keep serving even if the build fails
                    traceback.print_exc()
    except KeyboardInterrupt:
        print("\nStopping.")
        server.shutdown()
