import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import sys

# --- Get range from CLI args ---
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

results = [["Case Number", "URL", "Murder Charge Found", "Party Name"]]

# --- Scrape ---
for case_number, url in zip(case_numbers, urls):
    try:
        req = requests.get(url)
        soup = BeautifulSoup(req.content, "html.parser")

        # Step 1: Get all murder-related charges
        murder_charges = []
        table = soup.find("div", id="tblDocket12")
        if table:
            rows = table.find_all("div", class_='row g-0')
            for row in rows:
                divs = row.find_all("div")
                for i in range(len(divs)):
                    if "Description" in divs[i].get_text(strip=True):
                        if i + 1 < len(divs):
                            description = divs[i + 1].get_text(strip=True)
                            if "MURDER" in description.upper():
                                murder_charges.append(description)

        # Step 2: Pull from Disposition Section
        name_charge_pairs = []
        disposition_header = soup.find("div", string="Disposition Information")
        if disposition_header:
            current_row = disposition_header.find_next_sibling()
            while current_row and current_row.name == "div" and "row" in current_row.get("class", []):
                divs = current_row.find_all("div")
                party_name = None
                charge = None

                for i in range(len(divs)):
                    label = divs[i].get_text(strip=True).upper()
                    if "PARTY NAME" in label and i + 1 < len(divs):
                        party_name = divs[i + 1].get_text(strip=True)
                    elif "DESCRIPTION" in label and i + 1 < len(divs):
                        desc_text = divs[i + 1].get_text(strip=True)
                        if "MURDER" in desc_text.upper():
                            charge = desc_text

                if party_name and charge:
                    name_charge_pairs.append((party_name, charge))

                current_row = current_row.find_next_sibling()

        if name_charge_pairs:
            for name, charge in name_charge_pairs:
                results.append([case_number, url, charge, name])
        elif murder_charges:
            for charge in murder_charges:
                results.append([case_number, url, charge, "No matching party in Disposition Info"])

    except Exception as e:
        print(f"Error processing {case_number}: {e}")

# --- Append to Google Sheet ---
sheet.append_rows(results[1:])  # skip header row for append
print(f"Finished batch {start}-{end}")
