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

        # Step 2: Extract defendant name based on "Role: DEFENDANT"
        defendant_names = []
        party_section = soup.find("div", id="parties")
        if party_section:
            rows = party_section.find_all("div", class_="row g-0")
            for i in range(1, len(rows)):
                label_div = rows[i].find("div", class_="col-6 col-lg-2")
                value_div = rows[i].find("div", class_="col-6 col-lg-10")
                if label_div and value_div and label_div.get_text(strip=True).upper() == "ROLE:":
                    if value_div.get_text(strip=True).upper() == "DEFENDANT":
                        # Look one row above for the Name
                        name_row = rows[i - 1]
                        name_label = name_row.find("div", class_="col-6 col-lg-2")
                        name_value = name_row.find("div", class_="col-6 col-lg-10")
                        if name_label and name_value and name_label.get_text(strip=True).upper() == "NAME:":
                            defendant_names.append(name_value.get_text(strip=True))

        # Step 3: Combine murder charges with each defendant name
        if murder_charges:
            if defendant_names:
                for charge in murder_charges:
                    for name in defendant_names:
                        results.append([case_number, url, charge, name])
            else:
                for charge in murder_charges:
                    results.append([case_number, url, charge, "No defendant name found"])

    except Exception as e:
        print(f"Error processing {case_number}: {e}")

# --- Write to Google Sheet ---
sheet.clear()
sheet.append_rows(results)
print("Upload complete.")
