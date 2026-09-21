"""
Capture the Control Center views used as submission screenshots.

Serves the built application from control-center/dist on localhost, opens it in
the installed Microsoft Edge through Playwright, and saves 1920x1080 viewport
captures to evidence/app-screenshots/. These are genuine captures of the local,
offline application. They are not Foundry captures and are never stored with
them.

Needs: `npm run build` in control-center first, and `pip install playwright`.
No browser download is needed, the installed Edge is used. No network call
leaves the machine.

Run: python scripts/capture_control_center.py
"""
import functools
import http.server
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "control-center", "dist")
OUT = os.path.join(ROOT, "evidence", "app-screenshots")
PORT = 5187

# (file id, navigation label, optional text to click, optional text to scroll to)
CAPTURES = (
    ("APP01", "Dashboard", None, None),
    ("APP02", "Customer Assistant", None, None),
    ("APP04", "Evidence Explorer", None, None),
    ("APP09", "System Status", None, None),
    ("APP09b", "System Status", None, "Real Foundry runs of SYN-CASE-4003"),
    ("APP10", "Runtime Evidence", None, None),
)


def serve() -> http.server.ThreadingHTTPServer:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIST)
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> int:
    if not os.path.exists(os.path.join(DIST, "index.html")):
        print("control-center/dist is missing. Run: cd control-center && npm run build")
        return 1
    from playwright.sync_api import sync_playwright

    os.makedirs(OUT, exist_ok=True)
    server = serve()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto("http://127.0.0.1:%d/" % PORT)
            page.wait_for_load_state("networkidle")
            for file_id, label, click_text, scroll_text in CAPTURES:
                page.get_by_role("button", name=label).first.click()
                page.wait_for_timeout(400)
                page.evaluate("window.scrollTo(0, 0)")
                if click_text:
                    page.get_by_text(click_text).first.click()
                if scroll_text:
                    page.get_by_text(scroll_text).first.evaluate("el => el.scrollIntoView({block: 'start'})")
                page.wait_for_timeout(300)
                dest = os.path.join(OUT, file_id + ".png")
                page.screenshot(path=dest, full_page=False)
                print("captured %s  %s" % (file_id, label))
            browser.close()
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
