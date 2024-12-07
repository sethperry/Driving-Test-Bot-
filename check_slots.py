from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import requests
import os

# Get sensitive information from environment variables
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
LICENCE_NUMBER = os.environ.get("LICENCE_NUMBER")
CONTACT_NAME = os.environ.get("CONTACT_NAME")
CONTACT_PHONE = os.environ.get("CONTACT_PHONE")

def send_telegram_notification(slot_time):
    message_text = f"Earlier slot available within 14 days: {slot_time.strftime('%A, %d %B %Y %I:%M %p')}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": CHAT_ID,
        "text": message_text
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        print("Telegram notification sent successfully.")
    else:
        print("Failed to send Telegram notification. Status code:", response.status_code)

options = Options()
# Enable headless mode for Chrome
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Use webdriver-manager to handle ChromeDriver setup
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Set a default wait time (in seconds)
wait = WebDriverWait(driver, 10)

try:
    # Step 1: Terms and Conditions Page
    driver.get("https://www.service.transport.qld.gov.au/tmrauthentication/public/TermsAndConditions.xhtml?serviceName=SbsExternal&qgovLoginSelected=N&entryPage=/application/CleanBookingDE.xhtml&exitPage=/public/Farewell.xhtml&executionContext=qt&dswid=-9331")

    # Step 2: Accept the Terms
    accept_button = wait.until(EC.element_to_be_clickable((By.ID, "termsAndConditions:TermsAndConditionsForm:acceptButton")))
    accept_button.click()

    # Step 3: Fill Out Licence Details
    licence_input = wait.until(EC.presence_of_element_located((By.ID, "CleanBookingDEForm:dlNumber")))
    licence_input.send_keys(LICENCE_NUMBER)

    contact_name_input = driver.find_element(By.ID, "CleanBookingDEForm:contactName")
    contact_name_input.send_keys(CONTACT_NAME)

    contact_phone_input = driver.find_element(By.ID, "CleanBookingDEForm:contactPhone")
    contact_phone_input.send_keys(CONTACT_PHONE)

    # Step 4: Select the Test Type
    product_type_label = wait.until(EC.element_to_be_clickable((By.ID, "CleanBookingDEForm:productType_label")))
    product_type_label.click()

    product_type_option = wait.until(EC.element_to_be_clickable((By.ID, "CleanBookingDEForm:productType_1")))
    product_type_option.click()

    # Step 5: Click Continue to move to the next page
    continue_button = wait.until(EC.element_to_be_clickable((By.ID, "CleanBookingDEForm:actionFieldList:confirmButtonField:confirmButton")))
    continue_button.click()

    print("Form submitted. Current Page URL:", driver.current_url)

    # Step 6: On the next page, click the additional accept/continue button
    next_accept_button = wait.until(EC.element_to_be_clickable((By.ID, "BookingConfirmationForm:actionFieldList:confirmButtonField:confirmButton")))
    next_accept_button.click()

    print("Second accept clicked. Current Page URL:", driver.current_url)

    # LocationSelection page
    regions_to_check = ["BookingSearchForm:region_13", "BookingSearchForm:region_15"]

    # Date format of the slot time, adjust if needed
    date_format = "%A, %d %B %Y %I:%M %p"  # e.g. "Wednesday, 29 January 2025 2:50 PM"

    for i, region_id in enumerate(regions_to_check):
        # Open the dropdown
        region_label = wait.until(EC.element_to_be_clickable((By.ID, "BookingSearchForm:region_label")))
        region_label.click()

        # Select the desired region
        desired_option = wait.until(EC.element_to_be_clickable((By.ID, region_id)))
        desired_option.click()

        # Click the Continue button after region selection
        continue_button = wait.until(EC.element_to_be_clickable((By.ID, "BookingSearchForm:actionFieldList:confirmButtonField:confirmButton")))
        continue_button.click()

        print(f"Checked region {region_id}. Current Page URL:", driver.current_url)

        # Wait for the slot table on the SlotSelection.xhtml page
        slot_table = wait.until(EC.presence_of_element_located((By.ID, "slotSelectionForm:slotTable")))

        # Find all slot rows
        slots = driver.find_elements(By.CSS_SELECTOR, "#slotSelectionForm\\:slotTable tr.ui-datatable-selectable")

        earliest_slot_time = None

        for slot in slots:
            # Extract the date/time text from the second cell
            label = slot.find_element(By.CSS_SELECTOR, "td:nth-child(2) label")
            slot_time_str = label.text.strip()

            # Parse the slot time
            try:
                slot_time = datetime.strptime(slot_time_str, date_format)
            except ValueError:
                # If parsing fails, skip this slot
                continue

            # Track the earliest slot
            if earliest_slot_time is None or slot_time < earliest_slot_time:
                earliest_slot_time = slot_time

        if earliest_slot_time:
            cutoff_date = datetime.now() + timedelta(days=14)
            if earliest_slot_time < cutoff_date:
                print(f"Found a slot within 14 days for region {region_id}: {earliest_slot_time}")
                # Send Telegram notification
                send_telegram_notification(earliest_slot_time)
            else:
                print(f"The earliest slot for region {region_id} is {earliest_slot_time}, not within 14 days.")
        else:
            print(f"No available slots found for region {region_id}.")

        # If there are more regions to check, click "Change location selection"
        # to go back to the location selection page.
        if i < len(regions_to_check) - 1:
            change_location_button = wait.until(EC.element_to_be_clickable((By.ID, "slotSelectionForm:actionFieldList:j_id_6o:j_id_6p")))
            change_location_button.click()
            print("Returned to LocationSelection page to check next region.")

finally:
    driver.quit()
