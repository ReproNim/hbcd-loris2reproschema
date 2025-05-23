import requests
import json
import csv
import sys
import os
from datetime import datetime

def fetch_data_dictionary(username, password, output_dir):
    # Base URL for the API
    base_url = "https://prod.hbcd.msi.umn.edu"
    
    # Step 1: Authenticate and get token
    login_url = f"{base_url}/api/v0.0.3/login"
    credentials = {
        "username": username,
        "password": password
    }
    
    # Make the authentication request
    try:
        login_response = requests.post(
            login_url,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            data=json.dumps(credentials)
        )
        
        # Check if authentication was successful
        if login_response.status_code == 200:
            # Extract the token from the response
            token = login_response.json().get('token')
            
            # Step 2: Use the token to request the data dictionary
            dict_url = f"{base_url}/datadict/datadictionary"
            dict_response = requests.get(
                dict_url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            
            # Check if data dictionary request was successful
            if dict_response.status_code == 200:
                # Get the JSON data
                data_dict = dict_response.json()
                
                # Create output directory if it doesn't exist
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # Generate CSV filename with date stamp
                date_stamp = datetime.now().strftime("%Y-%m-%d")
                csv_file = os.path.join(output_dir, f'hbcd_data_dictionary_{date_stamp}.csv')
                
                save_as_csv(data_dict, csv_file)
                print(f"Data dictionary successfully retrieved and saved to {csv_file}")
            else:
                print(f"Failed to retrieve data dictionary. Status code: {dict_response.status_code}")
                print(f"Response: {dict_response.text}")
        else:
            print(f"Authentication failed. Status code: {login_response.status_code}")
            print(f"Response: {login_response.text}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False
    
    return True

def save_as_csv(data_dict, csv_file):
    """
    Convert the JSON data dictionary to CSV format
    """
    if isinstance(data_dict, list):
        items = data_dict
    elif isinstance(data_dict, dict) and 'items' in data_dict:
        items = data_dict['items']
    else:
        items = [data_dict]
    
    if not items:
        print("Warning: No data elements found in the response")
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['No data elements found'])
        return
    
    all_fields = set()
    for item in items:
        if isinstance(item, dict): # Ensure item is a dictionary before calling .keys()
            all_fields.update(item.keys())
        else:
            # Handle cases where an item might not be a dictionary (e.g., if the API returns unexpected data)
            print(f"Warning: Skipping non-dictionary item: {item}") 
    
    headers = sorted(list(all_fields))
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for item in items:
            if isinstance(item, dict): # Ensure item is a dictionary before writing
                 writer.writerow(item)

def main():
    # Define the output directory for CSV files
    output_directory = "loris_data_dictionaries"

    # Get credentials from environment variables
    username = os.getenv("HBCD_USERNAME")
    password = os.getenv("HBCD_PASSWORD")

    if not username or not password:
        print("Error: HBCD_USERNAME and HBCD_PASSWORD environment variables must be set.")
        sys.exit(1)
        
    # Call the function with credentials and output directory
    success = fetch_data_dictionary(username, password, output_directory)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 