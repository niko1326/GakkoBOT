import time
import os
import hashlib
import requests
import traceback
import re
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

def clean_content(html):
    # Remove dynamic timestamps like "02.04.2025 10:11"
    return re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", html)

def get_page_content():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Login
        page.goto(URL_LOGIN)
        page.wait_for_selector("#userNameInput")
        page.fill("#userNameInput", USERNAME)
        page.fill("#passwordInput", PASSWORD)
        page.evaluate("AppendUPN(); Login.submitLoginRequest();")
        page.wait_for_timeout(5000)

        # Navigate to grades
        page.goto(URL_TARGET)
        page.wait_for_timeout(3000)

        # Grab all grade blocks
        grade_blocks = page.locator(".kt-widget--user-profile-3")
        all_html = ""
        count = grade_blocks.count()
        for i in range(count):
            all_html += grade_blocks.nth(i).inner_html()

        browser.close()
        return clean_content(all_html)

def hash_content(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

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
                send_telegram_notification("🔔 A new grade may have been added!")
                with open("last_hash.txt", "w") as f:
                    f.write(current_hash)
                last_hash = current_hash
            else:
                print("✅ No new grade detected.")

        except Exception:
            error_message = f"⚠️ Error:\n{traceback.format_exc()}"
            send_telegram_notification(error_message)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()