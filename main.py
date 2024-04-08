import sys, os, requests, json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def request_jira(jql, offset):

    url = os.getenv('search_url')

    user = os.getenv('jiraUser')
    pw = os.getenv('jiraToken')
    auth = HTTPBasicAuth(user, pw)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
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
            "jql": jql,
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

    return response

def check_issues():
    #check only, returns number of bugs created and updated since last fetch
    
    last_fetch_str = read_last_fetch()
    last_fetch_dt = datetime.fromisoformat(last_fetch_str)
    last_fetch = last_fetch_dt.strftime("%Y-%m-%d %H:%M")
    jql_created = "project in (KNT, KM) and type = Bug and created > \"" + last_fetch + "\""
    jql_status = "project in (KNT, KM) and type = Bug and status changed after \"" + last_fetch + "\""
    
    offset = 0

    #get bugs created since last fetch
    response = request_jira(jql_created, 0)
    response_data = json.loads(response.text)
    created_count = response_data['total']
    print(f"Since {last_fetch}")
    print(f"Bugs Created: {created_count}")

    #get bugs updated(status) since last fetch
    response = request_jira(jql_status, 0)
    response_data = json.loads(response.text)
    print(f"Status Updated: {response_data['total']}")

    print("Would you like to update the datafile?")
    while(True):
        ans = input("(y/n) ")
        match ans.lower():
            case "y":
                update_datafile()
                break
            case "n":
                break
            case _:
                continue
    
def update_datafile():
    offset = 0
    jql = "project in (KNT, KM) and type = Bug"
    
    extracted_data = []
    
    print("Getting Issues...", end="", flush=True)
    while(True):
        response = request_jira(jql, offset)
        response_data = json.loads(response.text)
        
        offset += 100
        #print(len(response_data['issues']))
        print("||", end="", flush=True)
        if(len(response_data['issues']) == 0):
            break
        
        extract_fields(response_data, extracted_data)
    print("done.")

    #upload to openAI

    jsonWriter(extracted_data)
    
def last_fetch_format():
    last_fetch_str = read_last_fetch()
    last_fetch_dt = datetime.fromisoformat(last_fetch_str)
    last_fetch = last_fetch_dt.strftime("%Y-%m-%d %H:%M")
    
    return last_fetch
    
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
    #for time based auto updates. Not used for now
    last_fetch = read_last_fetch()
    last_fetch_dt = datetime.fromisoformat(last_fetch)
    cur_time = datetime.now()
    
    time_diff = cur_time - last_fetch_dt
    thresh = timedelta(minutes=30)
    
    if time_diff > thresh:
        return True
    else:
        return False
    
def ask_assistant(query):
    print("[Assistant] ", query)
    
def main():
    print("What bugs are you looking for?      (type: 'bye' to exit)\n")
    while(True):
        
        prompt = input("[QUERY] ")
        match prompt.lower():
            case "help":
                print("'help'\t\t- show menu\n'bye'\t\t- exit\n'update'\t-update the jira isues datafile without checking for changes\n'check'\t\t- check for changes to the jira issues")
            case "bye":
                sys.exit()
            case "update":
                update_datafile()
            case "check":
                check_issues()
            case _:
                ask_assistant(prompt)

if __name__ == "__main__":
    main()
