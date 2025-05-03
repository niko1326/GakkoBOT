import time
import os
import hashlib
import requests
import traceback
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

URL_LOGIN = "https://gakko.pjwstk.edu.pl/"
URL_TARGET = "https://gakko.pjwstk.edu.pl/edux/8656/grades"
CHECK_INTERVAL = 900  # 15 minutes

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Failed to send Telegram notification:", e)

def get_page_content():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Go to login page
        page.goto(URL_LOGIN)

        # Wait for username field to appear
        page.wait_for_selector("#userNameInput")

        # Fill login fields
        page.fill("#userNameInput", USERNAME)
        page.fill("#passwordInput", PASSWORD)

        # Click "Sign in" by evaluating JavaScript that triggers login
        page.evaluate("AppendUPN(); Login.submitLoginRequest();")

        # Wait for redirection to complete (you may want to increase this)
        page.wait_for_timeout(5000)

        # Go to the grades page
        page.goto(URL_TARGET)
        page.wait_for_timeout(3000)

        # Get full HTML content
        content = page.content()

        browser.close()
        return content

def hash_content(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def main():
    try:
        with open("last_hash.txt", "r") as f:
            last_hash = f.read()
    except FileNotFoundError:
        last_hash = ""

    while True:
        try:
            content = get_page_content()
            current_hash = hash_content(content)

            if not last_hash:
                send_telegram_notification("✅ Initial content fetched. Monitoring started.")
                with open("last_hash.txt", "w") as f:
                    f.write(current_hash)
                last_hash = current_hash

            elif current_hash != last_hash:
                send_telegram_notification("🔔 Page content has changed!")
                with open("last_hash.txt", "w") as f:
                    f.write(current_hash)
                last_hash = current_hash
            else:
                print("✅ No change detected.")

        except Exception:
            error_message = f"⚠️ Error:\n{traceback.format_exc()}"
            send_telegram_notification(error_message)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()