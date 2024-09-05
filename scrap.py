import logging
import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Path to your chromedriver
chromedriver_path = '/Users/bsridharpatnaik/Downloads/chromedriver-mac-arm64/chromedriver'

# Parameters
start_page = 10  # Starting page number (e.g., 5)
no_of_pages = 2  # Number of pages to scrape (e.g., 10)

# Calculate end page
end_page = start_page + no_of_pages - 1

# Parametrized output file name
output_file = f'Durg_{start_page}_to_{end_page}.csv'

# Initialize the webdriver using Service and Options for Headless Chrome
service = Service(chromedriver_path)
options = webdriver.ChromeOptions()
options.add_argument("--window-size=1920,1080")  # Set window size to ensure everything is rendered properly

logger.info("Initializing the webdriver...")
driver = webdriver.Chrome(service=service, options=options)

# CSV file setup
columns = [
    'Project Name', 'Registration Number', 'Authorized Name', 'Promoter Name', 'Project Type', 'District',
    'Tehsil', 'Approved Date', 'Proposed End Date', 'Extended Proposed End Date', 'Website',
    'Project Status', 'Detail Authorized Name', 'Project Address', 'State', 'District (Detail)',
    'Tehsil (Detail)', 'Email', 'Mobile'
]

# Write the header to the CSV file
with open(output_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(columns)


def retry_fetch_data(driver, row_index, page_count, start_page):
    """
    Retry fetching the data either by refreshing the details page or by re-clicking the 'Details' link.
    """
    try:
        current_url = driver.current_url
        if "Promoter_Reg_Only_View_Application_new.aspx" in current_url:
            # Refresh details page
            logger.info(f"Retrying data fetch for row {row_index + 1} on page {start_page + page_count}...")
            driver.refresh()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ApplicantType"))
            )
        else:
            # Refresh main page and retry clicking 'Details' link
            logger.info(f"Retrying click on 'Details' link for row {row_index + 1} on page {start_page + page_count}...")
            driver.refresh()
            for i in range(start_page + page_count - 1):
                next_button = driver.find_element(By.LINK_TEXT, 'Next')
                next_button.click()
                time.sleep(5)  # Wait for the page to load

            details_link = driver.find_element(By.ID, f"ContentPlaceHolder1_gv_ProjectList_lnk_View_{row_index}")
            details_link.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ApplicantType"))
            )
    except Exception as e:
        logger.error(f"Retry failed for row {row_index + 1} on page {start_page + page_count}. Error: {str(e)}")
        sys.exit(1)  # Terminate after retry failure


try:
    # Open the URL
    url = "https://rera.cgstate.gov.in/Approved_project_List.aspx"
    logger.info(f"Opening the URL: {url}")
    driver.get(url)

    # Wait for 1 minute to allow the user to select the dropdown and enter the security code
    logger.info("Waiting for 1 minute to allow user interaction...")
    time.sleep(60)

    # Wait until the table is present
    logger.info("Waiting for the table to be present on the page...")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_gv_ProjectList"))
    )

    # Skip to the start page by clicking "Next" the required number of times
    logger.info(f"Skipping to start page {start_page}...")
    current_page = 1
    while current_page < start_page:
        next_button = driver.find_element(By.LINK_TEXT, 'Next')
        next_button.click()
        time.sleep(5)  # Wait time to ensure the next page loads
        current_page += 1

    # Scrape the data from start_page to end_page
    page_count = 0
    while page_count < no_of_pages:
        logger.info(f"Scraping data from page {start_page + page_count}...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all rows in the table
        rows = soup.find("table", {"id": "ContentPlaceHolder1_gv_ProjectList"}).find("tbody").find_all("tr")

        for row_index, row in enumerate(rows):
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

            # Attempt to find and click the 'Details' link
            try:
                details_link = cells[13].find("a")
                if details_link:
                    logger.info(f"Clicking 'Details' link for row {row_index + 1} on page {start_page + page_count}...")
                    driver.find_element(By.ID, details_link['id']).click()

                    # Wait for the details page to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ApplicantType"))
                    )

                    # Extract details from the details page
                    project_status = driver.find_element(By.ID, "ContentPlaceHolder1_ApplicantType").get_attribute("value")
                    detail_authorized_name = authorized_name
                    project_address = driver.find_element(By.ID, "ContentPlaceHolder1_AadharNumber").text.strip()
                    state = driver.find_element(By.CSS_SELECTOR, "#ContentPlaceHolder1_State_Name option[selected='selected']").text.strip()
                    district_detail = driver.find_element(By.CSS_SELECTOR, "#ContentPlaceHolder1_District_Name option[selected='selected']").text.strip()
                    tehsil_detail = driver.find_element(By.CSS_SELECTOR, "#ContentPlaceHolder1_Tehsil_Name option[selected='selected']").text.strip()
                    email = driver.find_element(By.ID, "ContentPlaceHolder1_txt_pemail").get_attribute("value")
                    mobile = driver.find_element(By.ID, "ContentPlaceHolder1_txt_pmobile").get_attribute("value")

                    # Append to the data list
                    data_row = [
                        project_name, registration_number, authorized_name, promoter_name, project_type, district,
                        tehsil, approved_date, proposed_end_date, extended_end_date, website, project_status,
                        detail_authorized_name, project_address, state, district_detail, tehsil_detail, email, mobile
                    ]

                    # Write the row to the CSV file
                    with open(output_file, mode='a', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow(data_row)

                    logger.info(f"Data for row {row_index + 1} on page {start_page + page_count} written to CSV.")

                    # Go back to the previous page
                    logger.info("Returning to the previous page...")
                    driver.back()

                    # Manually navigate to the correct page again
                    logger.info(f"Navigating back to page {start_page + page_count} after returning from details page...")
                    for i in range(start_page + page_count - 1):
                        next_button = driver.find_element(By.LINK_TEXT, 'Next')
                        next_button.click()
                        time.sleep(5)  # Wait time to ensure the page loads

                else:
                    logger.warning(f"No 'Details' link found for row {row_index + 1} on page {start_page + page_count}. Skipping...")
            except Exception as e:
                logger.error(f"Error clicking 'Details' link for row {row_index + 1} on page {start_page + page_count}: {str(e)}")
                logger.info(f"Retrying the process for row {row_index + 1} on page {start_page + page_count}...")
                retry_fetch_data(driver, row_index, page_count, start_page)

        # Check if there is a next page and the limit hasn't been reached
        if page_count < no_of_pages - 1:
            try:
                next_button = driver.find_element(By.LINK_TEXT, 'Next')
                logger.info(f"Navigating to page {start_page + page_count + 1}...")
                next_button.click()
                time.sleep(5)  # Updated wait time to 5 seconds
            except Exception as e:
                logger.info(f"No more pages to scrape or error occurred while clicking Next. Exiting loop at page {start_page + page_count}")
                sys.exit(1)  # Exit when an error occurs
        page_count += 1

finally:
    # Close the browser
    logger.info("Closing the browser...")
    driver.quit()

logger.info("Scraping completed.")
