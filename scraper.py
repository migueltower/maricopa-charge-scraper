import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("google-creds.json", scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open("Maricopa Charges")  # Sheet must exist and be shared
sheet = spreadsheet.sheet1

year = 2024
prefix = f"CR{year}-"
start = 0
end = 100
case_numbers = [f"{prefix}{str(i).zfill(6)}" for i in range(start, end + 1)]
urls = [f'https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber={case}' for case in case_numbers]
results = [["Case Number", "URL", "First Charge"]]

for case_number, url in zip(case_numbers, urls):
    try:
        req = requests.get(url)
        soup = BeautifulSoup(req.content, "html.parser")
        table = soup.find("div", id="tblDocket12")
        first_charge = None

        if table:
            rows = table.find_all("div", class_='row g-0')
            for row in rows:
                divs = row.find_all("div")
                for i in range(len(divs)):
                    if "Description" in divs[i].get_text(strip=True):
                        description = divs[i + 1].get_text(strip=True)
                        if not first_charge:
                            first_charge = description
                        if "MURDER" in description.upper():
                            first_charge = description
                            break
                else:
                    continue
                break
        results.append([case_number, url, first_charge or "No charge found"])
    except Exception as e:
        results.append([case_number, url, f"Error: {e}"])

sheet.clear()
sheet.append_rows(results)
print("Upload complete.")
