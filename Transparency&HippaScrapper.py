import time
import json
import os
import shutil
import gzip
from selenium import webdriver
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://transparency-in-coverage.uhc.com/"

def extract_elements(data, tag):
    elements = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == tag:
                elements.append(value)
            else:
                elements.extend(extract_elements(value, tag))
    elif isinstance(data, list):
        for item in data:
            elements.extend(extract_elements(item, tag))
    return elements

chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument(r"user-data-dir=C:\Users\muham\AppData\Local\Google\Chrome\User Data")
chrome_options.add_argument(r"profile-directory=Profile 7")

driver_path = r'C:\Users\muham\OneDrive\Desktop\chromedriver-win64\chromedriver.exe'
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(URL)

time.sleep(40)
print("GOING TO FIND LIST IN 5 SECONDS")
time.sleep(5)
json_links = driver.find_elements(By.CSS_SELECTOR, "ul.ant-list-items li.ant-list-item a")
locations = []

for index in range(min(100, len(json_links))):
    file_name = json_links[index].text
    json_links[index].click()

    download_path_default = os.path.join(os.path.expanduser('~'), 'Downloads', file_name)
    download_path_JSON1 = os.path.join(os.path.expanduser('~'), 'Downloads', 'JSON1', file_name)

    wait_time = 0
    while not os.path.exists(download_path_default) and wait_time < 10:
        time.sleep(1)
        wait_time += 1

    # Move the file from Downloads to JSON1
    shutil.move(download_path_default, download_path_JSON1)

    with open(download_path_JSON1, "r") as file:
        data = json.load(file)
        current_locations = extract_elements(data, "location")
        # Append data to the locations list
        locations.extend(current_locations)

# Print the number of locations extracted and the content
print(f"Number of locations: {len(locations)}")
print(f"Locations: {locations}")

driver.quit()  # Close the current driver instance
driver = webdriver.Chrome(service=service, options=chrome_options)  # Reopen with updated download path

# Open each location link and download the associated JSON file
download_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
for location in locations:
    # Extract the file name from the URL
    file_name = os.path.basename(urlparse(location).path)

    # Construct the path using the new file name
    download_path_default_JSON2 = os.path.join(os.path.expanduser('~'), 'Downloads', file_name)
    download_path_JSON2 = os.path.join(os.path.expanduser('~'), 'Downloads', 'JSON2', file_name)

    driver.execute_script(f"window.open('{location}','_blank')")
    time.sleep(10)  # Pause for the download to initiate

    is_downloading = True
    download_checks = 0  # Counter to avoid infinite loops
    
    while is_downloading and download_checks < 60:  # Check for up to 20 minutes (assuming 2 seconds per check)
        time.sleep(2)  # Wait for a bit before checking again
        download_checks += 1

        # If the file with the intended name is found, break out of the loop
        if os.path.exists(download_path_default_JSON2):
            is_downloading = False
            break
        
        # Else, continue checking for the .crdownload files
        crdownload_files = [f for f in os.listdir(download_folder) if f.endswith('.crdownload')]

        if crdownload_files:
            # Taking the first .crdownload file found (assuming one download at a time)
            download_path_default = os.path.join(download_folder, crdownload_files[0])
            current_size = os.path.getsize(download_path_default)
            print(f"Current download size: {current_size / (1024 * 1024)} MB")  # Print the size in MB
            
            if current_size > 100 * 1024 * 1024:  # File size greater than 100 MB
                driver.quit()  # Close the browser, ending the download
                print("Stopped the download due to size limit!")
                # Start a new browser for the next link
                driver = webdriver.Chrome(service=service, options=chrome_options)
                break
        else:
            # If the .crdownload file is not found, print a message (this will keep us updated in case something unexpected happens)
            print("No .crdownload file found yet. Still checking...")

    # If a .gz file exists (download completed successfully), then decompress it
    gz_files = [f for f in os.listdir(download_folder) if f.endswith('.gz')]
    if gz_files:
        gz_path = os.path.join(download_folder, gz_files[0])
        json_path = os.path.join(download_folder, 'JSON2', gz_files[0].replace('.gz', ''))
        # Decompress the .gz file
        with gzip.open(gz_path, 'rb') as f_in:
            with open(json_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Delete the original .gz file after extraction
        os.remove(gz_path)

driver.quit()

all_npis = []

# Directory with the decompressed JSON files
json_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'JSON2')

# List all files in the directory
json_files = [f for f in os.listdir(json_folder) if f.endswith('.json')]

for json_file in json_files:
    with open(os.path.join(json_folder, json_file), 'r') as file:
        data = json.load(file)
        npis = extract_elements(data, "npi")
        for npi in npis:
            if isinstance(npi, list):  # Check if it's a list
                all_npis.extend(npi)   # If yes, extend
            else:
                all_npis.append(npi)   # Otherwise, append

# Convert to set and back to list to remove duplicates
unique_npis = list(set(all_npis))

print(unique_npis)
print(len(unique_npis))
time.sleep(10)
print("INITIATING HIPAA THING IN 10 SECONDS")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

data_list = []  # This will store all the extracted data
request_counter = 0  # Counter for the number of requests made to the HIPAA website

for npi in unique_npis:  # Directly using unique_npis from the first part
    url = f"https://www.hipaaspace.com/medical_billing/coding/national_provider_identifier/codes/npi_{npi}.aspx"
    request_counter += 1
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        try:
            # Extracting organization name
            organization_name_elem = soup.find("strong", text="Organization Name").find_next("strong")
            if not organization_name_elem:
                raise ValueError("Failed to extract Organization Name.")
            organization_name = organization_name_elem.text

            # Extracting mailing address
            mailing_address_elem = soup.find("h4", text="Provider Mailing Address").find_next("p").strong
            if not mailing_address_elem:
                raise ValueError("Failed to extract Mailing Address.")
            mailing_address = ' '.join([text for text in mailing_address_elem.stripped_strings])

            # Extracting mailing phone
            mailing_phone_elem = soup.find("h4", text="Mailing Location Phone/Fax").find_next("td", text="Phone").find_next("a")
            if not mailing_phone_elem:
                raise ValueError("Failed to extract Mailing Phone.")
            mailing_phone = mailing_phone_elem.text.strip()

            # Extracting practice location address
            practice_location_address_elem = soup.find("h4", text="Provider Practice Location").find_next("p").strong
            if not practice_location_address_elem:
                raise ValueError("Failed to extract Practice Location Address.")
            practice_location_address = ' '.join([text for text in practice_location_address_elem.stripped_strings])

            # Extracting practice phone
            practice_phone_elem = soup.find("h4", text="Practice Location Phone/Fax").find_next("td", text="Phone").find_next("a")
            if not practice_phone_elem:
                raise ValueError("Failed to extract Practice Phone.")
            practice_phone = practice_phone_elem.text.strip()

            data_list.append({
                'NPI NUMBER': npi,
                'Organization Name': organization_name,
                'Practice Location Address': practice_location_address,
                'Practice Phone': practice_phone,
                'Mailing Address': mailing_address,
                'Mailing Phone': mailing_phone
            })

            # Printing extracted data
            print(f"NPI NUMBER: {npi}")
            print(f"Organization Name: {organization_name}")
            print(f"Practice Location Address: {practice_location_address}")
            print(f"Practice Phone: {practice_phone}")
            print(f"Mailing Address: {mailing_address}")
            print(f"Mailing Phone: {mailing_phone}")
            print("-----")

            if request_counter >= 30:
            # Save the current data to CSV
                df_temp = pd.DataFrame(data_list)
                df_temp.to_csv("output_data_temp.csv", index=False)

                # Reset the counter
                request_counter = 0

                # Pause for 60 seconds
                print("Taking a 60-second break after 100 requests...")
                time.sleep(60)

        except ValueError as ve:
            print(f"Couldn't extract data for NPI: {npi}. Error: {ve}")
            # Save the problematic HTML for inspection
            with open(f"npi_{npi}_error.html", "w", encoding="utf-8") as f:
                f.write(response.text)
        except Exception as e:
            print(f"Unexpected error occurred for NPI: {npi}. Error: {e}")

    else:
        print(f"Failed to fetch the webpage for NPI: {npi}. Status Code: {response.status_code}")
    
    
# Convert data_list into a DataFrame
df = pd.DataFrame(data_list)

# Save DataFrame to an Excel file
df.to_csv("output_data.csv", index=False)
