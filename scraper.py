import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# --- Google Sheets Setup ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("google-creds.json", scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open("Maricopa Charges")
sheet = spreadsheet.sheet1

# --- Generate case numbers & URLs ---
year = 2024
prefix = f"CR{year}-"
start = 0
end = 100
case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
urls = [f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case}' for case in case_numbers]

# Results will be a list of rows, starting with the header row
results = []

# --- Scrape only MURDER cases and extract Party Names ---
for case_number, url in zip(case_numbers, urls):
    try:
        req = requests.get(url)
        soup = BeautifulSoup(req.content, "html.parser")

        # --- Check for MURDER charge ---
        murder_charge = None
        charge_table = soup.find("div", id="tblDocket12")
        if charge_table:
            rows = charge_table.find_all("div", class_='row g-0')
            for row in rows:
                divs = row.find_all("div")
                for i in range(len(divs)):
                    if "Description" in divs[i].get_text(strip=True):
                        if i + 1 < len(divs):
                            description = divs[i + 1].get_text(strip=True)
                            if "MURDER" in description.upper():
                                murder_charge = description
                                break
                if murder_charge:
                    break

        if not murder_charge:
            continue  # Skip cases without a murder charge

        # --- Extract Party Names (Defendants) ---
        party_names = []
        parties_table = soup.find("div", id="tblParties")
        if parties_table:
            party_rows = parties_table.find_all("div", class_='row g-0')
            for row in party_rows:
                divs = row.find_all("div")
                if any("DEFENDANT" in div.get_text(strip=True).upper() for div in divs):
                    for div in divs:
                        text = div.get_text(strip=True)
                        if text and not any(word in text.upper() for word in ["DEFENDANT", "ATTORNEY", "PROSECUTOR"]):
                            party_names.append(text)
                            break  # Only one name per party row

        if not party_names:
            continue  # Skip if no defendant names are found

        # Build dynamic header if it's the first row
        max_party_cols = max(len(party_names), 1)
        headers = ["Case Number", "URL", "Murder Charge Found"] + [f"Party Name {i+1}" if i > 0 else "Party Name" for i in range(max_party_cols)]
        if not results:
            results.append(headers)

        # Build the row
        row = [case_number, url, murder_charge] + party_names
        results.append(row)

    except Exception as e:
        print(f"Error processing {case_number}: {e}")

# --- Write to Google Sheet ---
sheet.clear()
sheet.append_rows(results)
print("Upload complete.")
