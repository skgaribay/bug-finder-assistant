import sys, os, requests, json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def get_latest_bugs():
    url = os.getenv('search_url')
    user = os.getenv('jiraUser')
    pw = os.getenv('jiraToken')
    
    offset = 0
    
    auth = HTTPBasicAuth(user, pw)
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    extracted_data = []
    
    while(True):
        payload = json.dumps( {
            "expand": [
            "names",
            "issutypes"
            ],
            "fields": [
                "key",
                "summary",
                "status",
                "assignee",
                "reporter",
                "created",
                "labels",
                "description"
            ],
            "fieldsByKeys": False,
            "jql": "project in (KNT, KM) and type = Bug and created > -30m",
            "maxResults": 100,
            "startAt": offset
            } )
        
        response = requests.request(
            "POST",
            url,
            data=payload,
            headers=headers,
            auth=auth
            )
        #print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
        response_data = json.loads(response.text)
        
        offset += 100
        if(len(response_data['issues']) == 0):
            break
        
        extract_fields(response_data, extracted_data)
    if(extracted_data == []):
        return False
    else:
        jsonWriter(extracted_data)
        return True
    
def extract_fields(response, extracted_data):
    """Extract desired fields from each item in the response."""
    for item in response['issues']: 
        assignee_name = None
        assignee = item.get("fields", {}).get("assignee")
        if assignee:
            assignee_name = assignee.get("displayName")
        extracted_item = {
            "key": item.get("key"),
            "summary": item.get("fields", {}).get("summary"),
            "created": item.get("fields", {}).get("created"),
            "description": item.get("fields", {}).get("description"),
            "reporter": item.get("fields", {}).get("reporter", {}).get("displayName"),
            "assignee": assignee_name,  # Assign the display name or None
            "labels": item.get("fields", {}).get("labels", []),
            "status": item.get("fields", {}).get("status", {}).get("name")
        }
        extracted_data.append(extracted_item)
    #return extracted_data

def jsonWriter(data):
    try:
        with open('bugdata.json', 'r+') as file:
            # Load existing data
            existing_data = json.load(file)
            # Append new data
            existing_data.extend(data)
            # Set the file pointer to the beginning
            file.seek(0)
            # Write the updated data back to the file
            json.dump(existing_data, file, indent=4)
    except FileNotFoundError:
        # If the file doesn't exist, create it and write the data
        with open('bugdata.json', 'w') as file:
            json.dump(data, file, indent=4)
    
def get_issue():
    print("get_issue")
    
def write_last_fetch():
    """Write the current timestamp to the JSON file."""
    data = {"lastFetch": datetime.now().isoformat()}
    with open('last_fetch.json', 'w') as f:
        json.dump(data, f)

def read_last_fetch():
    """Read the lastFetched timestamp from the JSON file."""
    try:
        with open('last_fetch.json', 'r') as f:
            data = json.load(f)
        return data.get('lastFetch')
    except FileNotFoundError:
        # Return None if the file doesn't exist
        return None
    
def should_update():
    last_fetch = read_last_fetch()
    last_fetch_dt = datetime.fromisoformat(last_fetch)
    cur_time = datetime.now()
    
    time_diff = cur_time - last_fetch_dt
    thresh = timedelta(minutes=30)
    
    if time_diff > thresh:
        return True
    else:
        return False
    
def file_update():
    get_latest_bugs()
    write_last_fetch()
    
    
def main():
    print("What bugs are you looking for?      (type: 'bye' to exit)\n")
    while(True):
        prompt = input("[QUERY] ")
        if(prompt.lower() == "bye"):
            sys.exit()
        if(should_update()):
            print("Updating datafile...")
            file_update()
        
        print("[Assistant] ", prompt)

if __name__ == "__main__":
    main()
