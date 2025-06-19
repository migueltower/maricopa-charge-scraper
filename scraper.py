import sys
import asyncio
from playwright.async_api import async_playwright
import gspread
from google.oauth2.service_account import Credentials

# --- Batch range input ---
start = int(sys.argv[1])
end = int(sys.argv[2])

# --- Google Sheets setup ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("google-creds.json", scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open("Maricopa Charges")
sheet = spreadsheet.sheet1

# --- Async Playwright scraper ---
async def scrape():
    results = []
    year = 2024
    prefix = f"CR{year}-"
    case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for case_number in case_numbers:
            url = f"https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case_number}"
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(1500)  # let the JS render briefly

                # Check if tblDocket12 exists
                if not await page.locator("#tblDocket12").count():
                    print(f"⚠️ No tblDocket12 found for {case_number}")
                    continue

                # Pull all rows under tblDocket12
                rows = await page.locator("#tblDocket12 .row.g-0").all()
                for row in rows:
                    text = await row.inner_text()
                    if "MURDER" in text.upper():
                        clean_text = text.strip().replace("\n", " | ")
                        print(f"Case {case_number} → Found description: {clean_text}")
                        results.append([case_number, url, clean_text])
                        break

            except Exception as e:
                print(f"❌ Error on {case_number}: {e}")

        await browser.close()

    print(f"\n✅ Results found in batch {start}-{end}: {len(results)}")
    print(f"🔎 First result: {results[0] if results else 'No results'}")

    if results:
        existing = sheet.get_all_values()
        if not existing:
            sheet.append_row(["Case Number", "URL", "Murder Charge Found"])
        sheet.append_rows(results)
    print(f"✅ Upload complete for batch {start}-{end}")

asyncio.run(scrape())
