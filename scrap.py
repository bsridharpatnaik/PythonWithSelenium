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
from bs4 import BeautifulSoup
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Path to your chromedriver
chromedriver_path = '/Users/bsridharpatnaik/Downloads/chromedriver-mac-arm64/chromedriver'

# Parameters
start_page = 5  # Starting page number
no_of_pages = 1  # Number of pages to scrape
start_row = 0  # Starting row number within a page

# File to save the last processed row and page
resume_file = 'resume_position.txt'

# Calculate end page
end_page = start_page + no_of_pages - 1

# Parametrized output file name
output_file = f'Raipur_{start_page}_to_{end_page}.csv'


# Initialize the WebDriver
def initialize_browser():
    service = Service(chromedriver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    logger.info("Initializing the webdriver...")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def select_display_100_rows(driver):
    """
    To handle UI bug, first select '10', then select '100' rows to display.
    """
    try:
        logger.info("Selecting '10 rows per page' first to handle UI bug...")
        dropdown = Select(driver.find_element(By.NAME, "ContentPlaceHolder1_gv_ProjectList_length"))
        dropdown.select_by_value("10")  # Select the option with value "10"
        time.sleep(2)  # Wait for the page to refresh and display 10 rows

        logger.info("Now selecting '100 rows per page' from the dropdown...")
        dropdown.select_by_value("100")  # Select the option with value "100"
        time.sleep(5)  # Wait for the page to refresh and display 100 rows
    except Exception as e:
        logger.error(f"Error selecting '100 rows per page': {str(e)}")


def navigate_to_page(driver, start_page, current_page):
    """
    Navigate to a specific page if not already on that page.
    """
    logger.info(f"Navigating to page {start_page}...")
    while current_page < start_page:
        next_button = driver.find_element(By.LINK_TEXT, 'Next')
        next_button.click()
        time.sleep(5)  # Wait for the page to load
        current_page += 1
    return current_page


def save_resume_position(page, row):
    """Save the last processed page and row to a file for resuming."""
    with open(resume_file, 'w') as f:
        f.write(f"{page},{row}")
    logger.info(f"Saved resume position: Page {page}, Row {row}")


def load_resume_position():
    """Load the last processed page and row from the file."""
    if os.path.exists(resume_file):
        with open(resume_file, 'r') as f:
            page, row = f.read().strip().split(',')
            return int(page), int(row)
    return start_page, start_row


def restart_browser_and_resume(row_index, page_count, current_page, retry_row):
    global driver
    logger.info("Closing the browser and restarting...")
    driver.quit()

    # Re-initialize the browser
    driver = initialize_browser()
    url = "https://rera.cgstate.gov.in/Approved_project_List.aspx"
    driver.get(url)

    logger.info("Waiting for user interaction to select dropdown and enter security code...")
    time.sleep(60)  # Wait for user interaction

    # Navigate back to the correct page and select 100 rows
    logger.info(f"Retrying navigation to page {start_page + page_count}...")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_gv_ProjectList"))
    )
    select_display_100_rows(driver)
    navigate_to_page(driver, start_page + page_count, current_page)

    return driver, retry_row


def scrape_data(driver, row_index, page_count):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    rows = soup.find("table", {"id": "ContentPlaceHolder1_gv_ProjectList"}).find("tbody").find_all("tr")
    row = rows[row_index]
    cells = row.find_all("td")

    project_name = cells[1].text.strip()
    registration_number = cells[2].text.strip()
    authorized_name = cells[3].text.strip()
    promoter_name = cells[4].text.strip()
    project_type = cells[5].text.strip()
    district = cells[6].text.strip()
    tehsil = cells[7].text.strip()
    approved_date = cells[8].text.strip()
    proposed_end_date = cells[9].text.strip()
    extended_end_date = cells[10].text.strip()
    website = cells[11].find("a")["href"] if cells[11].find("a") else ""

    return {
        "project_name": project_name,
        "registration_number": registration_number,
        "authorized_name": authorized_name,
        "promoter_name": promoter_name,
        "project_type": project_type,
        "district": district,
        "tehsil": tehsil,
        "approved_date": approved_date,
        "proposed_end_date": proposed_end_date,
        "extended_end_date": extended_end_date,
        "website": website
    }


# Initialize the CSV file with headers
with open(output_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow([
        'Project Name', 'Registration Number', 'Authorized Name', 'Promoter Name', 'Project Type', 'District',
        'Tehsil', 'Approved Date', 'Proposed End Date', 'Extended Proposed End Date', 'Website',
        'Project Status', 'Detail Authorized Name', 'Project Address', 'State', 'District (Detail)',
        'Tehsil (Detail)', 'Email', 'Mobile'
    ])

# Load resume position if exists
start_page, start_row = load_resume_position()

# Start scraping
try:
    driver = initialize_browser()

    url = "https://rera.cgstate.gov.in/Approved_project_List.aspx"
    logger.info(f"Opening the URL: {url}")
    driver.get(url)

    logger.info("Waiting for 1 minute for user interaction...")
    time.sleep(60)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_gv_ProjectList"))
    )

    # Select '100' from the dropdown to display 100 rows per page
    select_display_100_rows(driver)

    current_page = 1
    current_page = navigate_to_page(driver, start_page, current_page)

    page_count = 0
    retry_row = None  # Track the row to retry if the error occurs

    while page_count < no_of_pages:
        logger.info(f"Scraping data from page {start_page + page_count}...")

        row_start = retry_row if retry_row is not None else start_row  # Start from the retry row or resume row

        for row_index in range(row_start, len(driver.find_elements(By.CSS_SELECTOR,
                                                                   "#ContentPlaceHolder1_gv_ProjectList tbody tr"))):
            try:
                data = scrape_data(driver, row_index, page_count)
                # Use XPath to find the details link based on the row position rather than ID
                details_link = driver.find_element(By.XPATH,
                                                   f"//*[@id='ContentPlaceHolder1_gv_ProjectList']/tbody/tr[{row_index + 1}]/td[14]/a")
                logger.info(f"Clicking 'Details' link for row {row_index + 1} on page {start_page + page_count}...")
                details_link.click()

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ApplicantType"))
                )

                project_status = driver.find_element(By.ID, "ContentPlaceHolder1_ApplicantType").get_attribute("value")
                project_address = driver.find_element(By.ID, "ContentPlaceHolder1_AadharNumber").text.strip()
                state = driver.find_element(By.CSS_SELECTOR,
                                            "#ContentPlaceHolder1_State_Name option[selected='selected']").text.strip()
                district_detail = driver.find_element(By.CSS_SELECTOR,
                                                      "#ContentPlaceHolder1_District_Name option[selected='selected']").text.strip()
                tehsil_detail = driver.find_element(By.CSS_SELECTOR,
                                                    "#ContentPlaceHolder1_Tehsil_Name option[selected='selected']").text.strip()
                email = driver.find_element(By.ID, "ContentPlaceHolder1_txt_pemail").get_attribute("value")
                mobile = driver.find_element(By.ID, "ContentPlaceHolder1_txt_pmobile").get_attribute("value")

                data_row = [
                    data['project_name'], data['registration_number'], data['authorized_name'], data['promoter_name'],
                    data['project_type'], data['district'],
                    data['tehsil'], data['approved_date'], data['proposed_end_date'], data['extended_end_date'],
                    data['website'],
                    project_status, data['authorized_name'], project_address, state, district_detail, tehsil_detail,
                    email, mobile
                ]

                with open(output_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(data_row)

                logger.info(f"Data for row {row_index + 1} on page {start_page + page_count} written to CSV.")
                driver.back()

                # Re-select '100' rows after returning to the list page, but handle the bug
                select_display_100_rows(driver)

                if start_page + page_count > 1:
                    navigate_to_page(driver, start_page + page_count, start_page + page_count - 1)

                retry_row = None  # Clear retry flag once successful

            except Exception as e:
                logger.error(
                    f"Error clicking 'Details' link for row {row_index + 1} on page {start_page + page_count}: {str(e)}")
                retry_row = row_index  # Store the row to retry after restart
                driver, retry_row = restart_browser_and_resume(row_index, page_count, start_page + page_count,
                                                               retry_row)
                break  # Exit the loop and restart after browser relaunch

        page_count += 1

finally:
    logger.info("Closing the browser...")
    driver.quit()

logger.info("Scraping completed.")
