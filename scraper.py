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

# --- Generate case numbers & URLs ---
year = 2024
prefix = f"CR{year}-"
case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
urls = [f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case}' for case in case_numbers]

results = []

# --- Scrape only MURDER charges ---
for case_number, url in zip(case_numbers, urls):
    try:
        req = requests.get(url)
        soup = BeautifulSoup(req.content, "html.parser")
        table = soup.find("div", id="tblDocket12")
        murder_charge = None

        if table:
            rows = table.find_all("div", class_='row g-0')
            for row in rows:
                divs = row.find_all("div")
                for i in range(len(divs)):
                    if "Description" in divs[i].get_text(strip=True):
                        if i + 1 < len(divs):  # Avoid index error
                            description = divs[i + 1].get_text(strip=True)
                            if "MURDER" in description.upper():
                                murder_charge = description
                                break
                if murder_charge:
                    break

        if murder_charge:
            results.append([case_number, url, murder_charge])

    except Exception as e:
        print(f"Error processing {case_number}: {e}")

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
