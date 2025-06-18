import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import sys

# --- Command line input for batch range ---
start = int(sys.argv[1])
end = int(sys.argv[2])

# --- Google Sheets Setup ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("google-creds.json", scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open("Maricopa Charges")
sheet = spreadsheet.sheet1

# --- Fake browser headers to load full site content ---
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0.0.0 Safari/537.36"
    )
}

# --- Generate case numbers & URLs ---
year = 2024
prefix = f"CR{year}-"
case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
urls = [f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case}' for case in case_numbers]

results = []

# --- Scrape both docket and disposition-based MURDER charges ---
for case_number, url in zip(case_numbers, urls):
    try:
        req = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(req.content, "html.parser")

        murder_found = False
        murder_description = None

        table = soup.find("div", id="tblDocket12")
        if not table:
            print(f"⚠️ No tblDocket12 found for {case_number}")
            continue

        # Try docket-style layout
        rows = table.find_all("div", class_="row g-0")
        for row in rows:
            divs = row.find_all("div")
            for i in range(len(divs)):
                if "Description" in divs[i].get_text(strip=True):
                    if i + 1 < len(divs):
                        description = divs[i + 1].get_text(strip=True)
                        print(f"Case {case_number} → Found description: {description}")
                        if "MURDER" in description.upper():
                            murder_description = description
                            murder_found = True
                            break
            if murder_found:
                break

        # Fallback: Try disposition-style layout
        if not murder_found:
            for row in rows:
                divs = row.find_all("div")
                for i in range(len(divs)):
                    label = divs[i].get_text(strip=True).upper()
                    if "DESCRIPTION" in label and i + 1 < len(divs):
                        description = divs[i + 1].get_text(strip=True)
                        print(f"Case {case_number} → Found disposition-style description: {description}")
                        if "MURDER" in description.upper():
                            murder_description = description
                            murder_found = True
                            break
                if murder_found:
                    break

        if murder_found:
            results.append([case_number, url, murder_description])

    except Exception as e:
        print(f"❌ Error processing {case_number}: {e}")

# --- Diagnostics ---
print(f"\n✅ Results found in batch {start}-{end}: {len(results)}")
print(f"🔎 First result: {results[0] if results else 'No results'}")

# --- Append results to Google Sheet ---
if results:
    existing_data = sheet.get_all_values()
    if not existing_data:
        sheet.append_row(["Case Number", "URL", "Murder Charge Found"])
    sheet.append_rows(results)

print(f"✅ Upload complete for batch {start}-{end}")
