import sys, os, requests, json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime

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
            "jql": "project in (KNT, KM) and type = Bug",
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
        
        print(len(response_data['issues']))
        offset += 100
        if(len(response_data['issues']) == 0):
            break
        
        extract_fields(response_data, extracted_data)
        
    jsonWriter(extracted_data)
    
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


def main():
    get_latest_bugs()

if __name__ == "__main__":
    main()
