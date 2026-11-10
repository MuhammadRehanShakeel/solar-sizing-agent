"""
capture_screenshots.py - Takes the README / LinkedIn screenshots of the RUNNING app.

Needs:
  1. the app running          (start_project.bat)
  2. demo customers + a demo staff account:
         backend\\venv\\Scripts\\python.exe scripts\\demo_data.py
     (it writes DEMO_ACCOUNT.txt, which is git-ignored, so no real password is used)

Run: scripts\\windows\\capture_screenshots.bat   ->  pictures are saved in docs/screenshots/
Uses the Edge or Chrome already installed on the PC (nothing big to download).

The chat pictures use your real Groq key, so those take ~1 minute. If the AI is busy the script
skips them and still saves everything else.
"""
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")
APP = "http://localhost:5175"
DESKTOP = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}


def read_account():
    path = os.path.join(ROOT, "DEMO_ACCOUNT.txt")
    if not os.path.isfile(path):
        return None, None
    values = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, _, value = line.strip().partition("=")
                values[key.strip()] = value.strip()
    return values.get("admin_email"), values.get("admin_password")


def launch(p):
    for channel in ("msedge", "chrome"):
        try:
            return p.chromium.launch(channel=channel)
        except Exception:
            continue
    return p.chromium.launch()


def shot(page, name, full_page=False, wait=1500):
    try:
        page.wait_for_timeout(wait)
        page.screenshot(path=os.path.join(OUT, name), full_page=full_page)
        print("saved", name)
    except Exception as e:
        print("skipped", name, "-", e)


def shot_part(page, selector, name, wait=800):
    """A picture of ONE block of the page (e.g. just the WAPDA table) - good for the README."""
    try:
        page.wait_for_timeout(wait)
        page.locator(selector).first.screenshot(path=os.path.join(OUT, name))
        print("saved", name)
    except Exception as e:
        print("skipped", name, "-", e)


def fill_calculator(page):
    """The customer's real case: 437 units in Rawalpindi, light goes once a week 9 am - 2 pm."""
    page.goto(f"{APP}/calculator")
    page.wait_for_timeout(1200)
    page.get_by_label("Monthly units").fill("437")
    page.get_by_role("button", name="Some days a week").click()
    page.wait_for_timeout(400)
    page.get_by_role("button", name="Calculate my options").click()
    try:
        page.wait_for_selector("text=The three systems side by side", timeout=120000)
    except Exception:
        alert = page.locator(".MuiAlert-message")
        reason = alert.first.inner_text().strip() if alert.count() else "no answer from the backend in 2 minutes"
        page.screenshot(path=os.path.join(ROOT, "screenshot_problem.png"))
        raise RuntimeError(f"calculator did not finish: {reason}")
    page.wait_for_timeout(2500)


def check_ai_answered(page):
    if page.locator(".MuiAlert-standardError").count():
        raise RuntimeError(page.locator(".MuiAlert-standardError").first.inner_text().strip())


def chat_pictures(page):
    page.goto(f"{APP}/advisor")
    page.wait_for_timeout(2000)
    shot(page, "04_advisor_empty.png")
    page.get_by_text("Bill 25,000 aata hai", exact=False).click()
    page.wait_for_selector("text=Working it out", timeout=15000)
    page.wait_for_selector("text=Working it out", state="detached", timeout=120000)
    page.wait_for_timeout(1200)
    check_ai_answered(page)
    box = page.get_by_label("Message")
    box.fill("Fan 4, LED light 6, fridge 1 chalne chahiye")
    page.get_by_role("button", name="Send").click()
    page.wait_for_selector("text=Working it out", timeout=15000)
    page.wait_for_selector("text=Working it out", state="detached", timeout=120000)
    check_ai_answered(page)
    if not page.locator("text=The three systems side by side").count():        # the AI asked one more question
        box.fill("Jo sab se behtar ho wo calculate kar dein")
        page.get_by_role("button", name="Send").click()
        page.wait_for_selector("text=Working it out", timeout=15000)
        page.wait_for_selector("text=Working it out", state="detached", timeout=120000)
        check_ai_answered(page)
    shot(page, "05_advisor_answer.png", wait=2500)


def staff_pictures(browser, email, password):
    if not email:
        print("skipped staff pictures - run scripts\\demo_data.py first (it writes DEMO_ACCOUNT.txt)")
        return
    page = browser.new_page(viewport=DESKTOP)
    page.goto(f"{APP}/staff/login")
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", password)
    page.click("button[type=submit]")
    page.wait_for_url(f"{APP}/staff", timeout=20000)
    shot(page, "11_staff_dashboard.png", full_page=True, wait=3000)
    for path, name in [("leads", "12_staff_leads.png"), ("surveys", "13_staff_surveys.png"),
                       ("chats", "14_staff_chats.png"), ("prices", "15_staff_prices.png")]:
        page.goto(f"{APP}/staff/{path}")
        shot(page, name, wait=2500)
    page.close()


def main():
    os.makedirs(OUT, exist_ok=True)
    email, password = read_account()
    with sync_playwright() as p:
        browser = launch(p)

        # ---------- the public website ----------
        page = browser.new_page(viewport=DESKTOP)
        page.goto(f"{APP}/")
        shot(page, "01_home.png", full_page=True, wait=2500)
        shot_part(page, "[data-shot=daystrip]", "02_day_strip.png")
        page.get_by_role("button", name="اردو").click()
        shot(page, "03_home_urdu.png", wait=1500)
        page.get_by_role("button", name="EN", exact=True).click()

        try:
            chat_pictures(page)
        except Exception as e:
            print("skipped the chat pictures (AI busy?) -", e)

        try:
            fill_calculator(page)
            shot(page, "06_calculator.png", full_page=True)
            shot_part(page, "[data-shot=wapda]", "07_wapda_choices.png")
            shot_part(page, "[data-shot=outage]", "08_load_shedding.png")
        except Exception as e:
            print("skipped the calculator pictures -", e)

        page.goto(f"{APP}/backup")
        shot(page, "09_backup_planner.png", wait=3000)
        page.goto(f"{APP}/survey")
        shot(page, "10_site_survey.png", wait=1500)
        page.close()

        try:
            staff_pictures(browser, email, password)
        except Exception as e:
            print("skipped the staff pictures -", e)

        # ---------- phone ----------
        phone = browser.new_page(viewport=PHONE, device_scale_factor=2, is_mobile=True, has_touch=True)
        phone.goto(f"{APP}/")
        shot(phone, "16_phone_home.png", wait=2500)
        phone.goto(f"{APP}/advisor")
        shot(phone, "17_phone_advisor.png", wait=2500)
        try:
            fill_calculator(phone)
            shot(phone, "18_phone_quote.png", full_page=True)
        except Exception as e:
            print("skipped 18_phone_quote.png -", e)
        phone.close()

        browser.close()
    print("\nDone. Pictures are in docs\\screenshots")


if __name__ == "__main__":
    sys.exit(main())
