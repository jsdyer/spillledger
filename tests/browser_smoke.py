"""Exercise the published records explorer at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "spillledger")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_BIN"))
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/spillledger/")
                page.wait_for_function("document.querySelector('#edition').textContent.includes('UTC')")
                assert "549,581.18" in page.locator("#claims").inner_text()
                page.locator("#province").select_option("Nova Scotia")
                page.locator("#search").fill("no such vessel 777")
                assert not page.locator("#detail").is_visible()
                page.locator("#search").fill("Farley Shelburne")
                assert page.locator("#claims .claim").count()==2
                assert "Town of Shelburne" in page.locator("#claims").inner_text()
                assert "ongoing" in page.locator("#recovery").inner_text()
                assert "#page=66" in page.locator("#original a").get_attribute("href")
                with page.expect_download() as capture:
                    page.locator("#csv").click()
                download = capture.value
                assert download.suggested_filename.endswith(".csv")
                assert len(Path(download.path()).read_text().splitlines()) >= 2
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                # The saved case and its native explorer restore the same incident.
                page.locator("#saved-record a").click()
                assert "farley-mowat-2015-06-24-shelburne-nova-scotia/" in page.url
                assert "Town of Shelburne" in page.locator("main").inner_text()
                page.get_by_role("link", name="Open this incident in the explorer", exact=True).first.click()
                page.wait_for_function("document.querySelector('#name').textContent.includes('Farley Mowat')")
                assert "Farley Mowat" in page.locator("#incident option:checked").inner_text()
                assert page.locator("#claims .claim").count() == 2
                for width in (390, 1280):
                    native = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 844})
                    saved = native.new_page()
                    base = f"http://127.0.0.1:{server.server_port}/spillledger/"
                    saved.goto(base)
                    saved.get_by_role("link", name="Browse incident records", exact=True).click()
                    saved.get_by_role("link", name="Amounts recovered", exact=True).click()
                    saved.get_by_role("link", name="Cormorant · Bridgewater · 2015-02-27", exact=True).click()
                    assert "$375,000.00 recovered on 2022-01-06" in saved.locator("main").inner_text()
                    assert saved.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                    native.close()
                assert not errors, errors
                browser.close()
            print("Browser checks passed: source records, filters, CSV download and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
