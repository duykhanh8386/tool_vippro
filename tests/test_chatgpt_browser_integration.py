"""Opt-in real Chrome checks against a local fixture, never a real account.

Set TV_PUBLISHING_BROWSER_TESTS=1 and CHROMEDRIVER to the driver executable.
"""
import base64
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from src.publishing_browser import ChatGPTImageBrowser
from src.task_runtime import bind_run_context, create_run_context


IMAGE = "data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="1280" height="720" fill="blue"/></svg>'
).decode()
PAGE = r"""<!doctype html><title>Just a moment...</title>
<main hidden>
  <button aria-label="Open profile menu">Account</button>
  <form>
    <input type="file" aria-label="Take a photo" accept="image/*" capture="environment" hidden>
    <input type="file" aria-label="Attach photos" accept="image/*" hidden>
    <div contenteditable="true" role="textbox" aria-label="Ask ChatGPT"></div>
    <button aria-label="Add files and more" type="button">+</button>
    <button type="submit" aria-label="Send message" disabled>Send</button>
  </form>
  <section id="messages"></section>
</main>
<script>
window.submissions = []; window.uploads = []; window.cameraUploads = 0; window.clicks = 0;
document.addEventListener('click', () => window.clicks++);
const form = document.querySelector('form'), editor = document.querySelector('[role=textbox]');
const send = document.querySelector('[type=submit]');
const generated = '__IMAGE__';
function updateSend() { send.disabled = !editor.innerText.trim() || !window.uploads.length; }
document.querySelector('[capture]').onchange = () => window.cameraUploads++;
document.querySelector('[aria-label="Attach photos"]').onchange = event => {
    window.uploads.push(event.target.files[0].name);
    const image = document.createElement('img'); image.src = generated; form.append(image);
    updateSend();
};
editor.addEventListener('input', updateSend);
form.onsubmit = event => {
    event.preventDefault(); window.submissions.push(editor.innerText);
    history.pushState({}, '', '/c/local-fixture');
    document.querySelector('#messages').innerHTML =
        '<article data-message-author-role="assistant">Image created<img src="' + generated + '"></article>';
    editor.innerText = ''; updateSend();
};
window.finishManualLogin = () => { document.title = 'ChatGPT'; document.querySelector('main').hidden = false; };
</script>""".replace("__IMAGE__", IMAGE)


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class LocalChatDriver:
    """Translate navigation only; all DOM interaction uses the real browser."""
    def __init__(self, driver, origin):
        self.driver, self.origin = driver, origin

    def __getattr__(self, name):
        return getattr(self.driver, name)

    @property
    def current_url(self):
        url = self.driver.current_url
        if url.startswith(self.origin):
            return "https://chatgpt.com" + url[len(self.origin):]
        return url

    def get(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "chatgpt.com":
            raise AssertionError("Fixture cannot navigate to an external service")
        self.driver.get(self.origin + parsed.path)


@unittest.skipUnless(os.environ.get("TV_PUBLISHING_BROWSER_TESTS") == "1", "opt-in local Chrome test")
class ChatGPTComposerBrowserTests(unittest.TestCase):
    def test_manual_login_resumes_upload_prompt_and_download_with_modern_composer(self):
        root = Path(__file__).resolve().parents[1] / "build"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="chatgpt-composer-test-", dir=root) as folder:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1200,900")
            options.add_argument("--user-data-dir=" + str(Path(folder) / "profile"))
            driver = webdriver.Chrome(service=Service(os.environ["CHROMEDRIVER"]), options=options)
            server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            browser = ChatGPTImageBrowser()
            browser.driver = LocalChatDriver(driver, f"http://127.0.0.1:{server.server_port}")
            browser.driver.get("https://chatgpt.com/")
            reference = Path(folder) / "reference.jpg"
            reference.write_bytes(b"local reference fixture")
            output = Path(folder) / "generated.svg"
            run = create_run_context("local-composer-test")
            waiting, manual_done = threading.Event(), threading.Event()
            errors, receipts, states = [], [], []

            def state_changed(state, message):
                states.append(state)
                if state == "verification":
                    waiting.set()
                    if not manual_done.wait(15):
                        raise AssertionError("Test did not complete manual login")

            def work():
                try:
                    with bind_run_context(run):
                        browser.generate(reference, "Draw a blue thumbnail", {"title": "Local song", "description": "Local description"}, output,
                                         on_state=state_changed, on_conversation=receipts.append)
                except Exception as exc:
                    errors.append(exc)

            worker = threading.Thread(target=work, daemon=True)
            try:
                worker.start()
                self.assertTrue(waiting.wait(15), "Worker did not wait for manual verification")
                self.assertEqual(driver.execute_script("return window.submissions.length + window.clicks"), 0)
                handles = driver.window_handles
                # Only a local fixture changes state; no real challenge exists.
                driver.execute_script("window.finishManualLogin()")
                manual_done.set()
                worker.join(30)
                self.assertFalse(worker.is_alive(), "Worker did not resume automatically")
                if errors:
                    raise errors[0]
                self.assertIn("ready", states)
                self.assertEqual(driver.window_handles, handles)
                self.assertTrue(output.read_bytes().startswith(b"<svg"))
                self.assertEqual(receipts, ["https://chatgpt.com/c/local-fixture"])
                result = driver.execute_script("return {prompts:window.submissions,files:window.uploads,camera:window.cameraUploads}")
                self.assertEqual(result["files"], ["reference.jpg"])
                self.assertEqual(result["camera"], 0)
                self.assertEqual(len(result["prompts"]), 1)
                self.assertIn("Draw a blue thumbnail", result["prompts"][0])
                self.assertIn("Title video: Local song", result["prompts"][0])
                # Resuming a saved receipt reads the image without a second send.
                browser.generate(reference, "Draw a blue thumbnail", {"title": "Local song", "description": "Local description"}, output,
                                 conversation_url=receipts[0])
                self.assertEqual(driver.execute_script("return window.submissions.length"), 1)
            finally:
                manual_done.set()
                run.request_stop()
                worker.join(10)
                browser.close()
                run.cleanup()
                server.shutdown()
                server.server_close()
                server_thread.join(5)


if __name__ == "__main__":
    unittest.main()
