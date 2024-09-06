import logging
import time
import csv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Path to your chromedriver
chromedriver_path = '/Users/bsridharpatnaik/Downloads/chromedriver-mac-arm64/chromedriver'

# Files
csv_file = 'main_page_data.csv'
detail_csv_file = 'details_page_data.csv'
resume_file = 'resume_row.txt'


# Initialize the WebDriver
def initialize_browser():
    service = Service(chromedriver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    logger.info("Initializing the webdriver...")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def set_dropdown_to_1000(driver):
    """Set the dropdown value to display 1000 rows in the DOM."""
    logger.info("Modifying the dropdown to display 1000 rows...")
    driver.execute_script(
        "document.querySelector('select[name=\"ContentPlaceHolder1_gv_ProjectList_length\"]').innerHTML += '<option value=\"1000\">1000</option>';")
    dropdown = Select(driver.find_element(By.NAME, "ContentPlaceHolder1_gv_ProjectList_length"))
    dropdown.select_by_value("1000")
    time.sleep(5)  # Wait for the page to refresh and load all rows


def save_resume_position(row):
    """Save the last processed row number."""
    with open(resume_file, 'w') as f:
        f.write(str(row))
    logger.info(f"Saved resume position: Row {row}")


def load_resume_position():
    """Load the last processed row number."""
    if os.path.exists(resume_file):
        with open(resume_file, 'r') as f:
            return int(f.read().strip())
    return 0


def find_row_by_project(driver, project_name, registration_number):
    """Search for a row by project name and registration number."""
    logger.info(
        f"Searching for project '{project_name}' with registration number '{registration_number}' on the page...")

    # Loop through rows to find the correct project
    rows = driver.find_elements(By.CSS_SELECTOR, "#ContentPlaceHolder1_gv_ProjectList tbody tr")
    for row_index, row in enumerate(rows):
        cells = row.find_elements(By.TAG_NAME, 'td')
        current_project_name = cells[1].text.strip()
        current_registration_number = cells[2].text.strip()

        if current_project_name == project_name and current_registration_number == registration_number:
            logger.info(f"Project found on row {row_index + 1}")
            return row_index, row

    logger.error(
        f"Project '{project_name}' with registration number '{registration_number}' not found on the current page.")
    return None, None


def scrape_detail_page_for_row(driver, row, row_index):
    """Scrape additional data from the details page for a specific row."""
    try:
        # Find all cells in the current row
        cells = row.find_elements(By.TAG_NAME, 'td')

        # Assuming "Details" link is in the 14th column (index 13 in Python)
        details_cell = cells[13]  # 14th column

        # Check if there's a link inside the "Details" cell
        details_link = details_cell.find_element(By.TAG_NAME, 'a')

        if details_link:
            logger.info(f"Clicking on the details link for row {row_index + 1}...")
            details_link.click()

            # Wait for the details page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ApplicantType"))
            )

            # Scrape data from the details page
            project_status = driver.find_element(By.ID, "ContentPlaceHolder1_ApplicantType").get_attribute("value")
            project_address = driver.find_element(By.ID, "ContentPlaceHolder1_AadharNumber").text.strip()
            state = driver.find_element(By.CSS_SELECTOR,
                                        "#ContentPlaceHolder1_State_Name option[selected='selected']").text.strip()
            district_detail = driver.find_element(By.CSS_SELECTOR,
                                                  "#ContentPlaceHolder1_District_Name option[selected='selected']").text.strip()
            tehsil_detail = driver.find_element(By.CSS_SELECTOR,
                                                "#ContentPlaceHolder1_Tehsil_Name option[selected='selected']").text.strip()

            # Fetch email and mobile using JavaScript or with an explicit wait
            try:
                email_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txt_pemail"))
                )
                email = email_element.get_attribute("value")
            except Exception as e:
                logger.warning(f"Email field not found or could not be fetched: {str(e)}")
                email = "N/A"

            try:
                mobile_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txt_pmobile"))
                )
                mobile = mobile_element.get_attribute("value")
            except Exception as e:
                logger.warning(f"Mobile field not found or could not be fetched: {str(e)}")
                mobile = "N/A"

            return [project_status, project_address, state, district_detail, tehsil_detail, email, mobile]

        else:
            logger.error(f"No 'Details' link found in row {row_index + 1}")
            raise Exception("Details link not found")

    except Exception as e:
        logger.error(f"Error occurred while processing row {row_index + 1}: {e}")
        raise


def process_details_from_csv():
    """Process each row from the CSV and fetch details from the details page."""
    driver = initialize_browser()
    url = "https://rera.cgstate.gov.in/Approved_project_List.aspx"
    driver.get(url)

    logger.info("Waiting for 1 minute for user interaction (select dropdown, enter security code)...")
    time.sleep(5)

    set_dropdown_to_1000(driver)

    resume_row = load_resume_position()

    # Open the main page data CSV
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)
        header = rows[0]
        rows = rows[1:]  # Skip the header row

        # Write additional columns to the CSV if not present
        if len(header) == 11:
            header.extend(
                ['Project Status', 'Project Address', 'State', 'District (Detail)', 'Tehsil (Detail)', 'Email',
                 'Mobile'])
            with open(detail_csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)

        for row_index, row_data in enumerate(rows):
            if row_index < resume_row:
                continue  # Skip already processed rows

            project_name, registration_number = row_data[0], row_data[1]

            # Find the row on the current page
            row_index_on_page, row = find_row_by_project(driver, project_name, registration_number)

            if row is not None:
                try:
                    details_data = scrape_detail_page_for_row(driver, row)
                    full_row = row_data + details_data  # Append the details data to the row

                    # Write the full row with details to the CSV
                    with open(detail_csv_file, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(full_row)

                    logger.info(f"Details for project '{project_name}' saved to {detail_csv_file}")
                    save_resume_position(row_index + 1)  # Save resume position after each successful scrape

                    # Return to the main page
                    logger.info("Returning to the main page...")
                    driver.back()
                    time.sleep(5)

                    # Reset the dropdown to 1000 after returning
                    set_dropdown_to_1000(driver)

                except Exception:
                    logger.error(f"Error occurred at row {row_index + 1}. Restarting the browser...")
                    driver.quit()
                    process_details_from_csv()  # Restart browser and resume from the same row
                    break  # Exit to allow restart after failure
            else:
                logger.error(f"Row for project '{project_name}' not found, skipping...")

    driver.quit()


if __name__ == "__main__":
    # Process details from the CSV file and append to the same file
    process_details_from_csv()
