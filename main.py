import sys, os, requests, json, re
from openai import OpenAI
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

api_key = os.getenv('api_key')
asst_id = os.getenv('assistant_id')
org_id = os.getenv('org_id')
client = OpenAI(
    api_key=api_key,
    organization=org_id,
    )

thread = client.beta.threads.create()

def get_keys(input):
    # Define the regex pattern to match "KNT-xxxx" and "KM-xxxx"
    pattern = r'\b(KNT|KM)-(\d+)\b'

    # Use findall() to extract all matches
    keys = re.findall(pattern, input)
    keylist = []
    for obj in keys:
        keylist.append(obj[0] + "-" + obj[1])
    
    return keylist

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
    #check only, returns number of bugs created and updated since last update
    
    last_update_str = read_last_update()
    last_update_dt = datetime.fromisoformat(last_update_str)
    last_update = last_update_dt.strftime("%Y-%m-%d %H:%M")
    jql_created = "project in (KNT, KM) and type = Bug and created > \"" + last_update + "\" ORDER BY created DESC"
    jql_status = "project in (KNT, KM) and type = Bug and status changed after \"" + last_update + "\" ORDER BY created DESC"
    
    offset = 0

    #get bugs created since last update
    response = request_jira(jql_created, 0)
    response_data = json.loads(response.text)
    created_count = response_data['total']
    print(f"[SYS] Since {last_update}")
    print(f"\tBugs Created: {created_count}")

    #get bugs updated(status) since last update
    response = request_jira(jql_status, 0)
    response_data = json.loads(response.text)
    print(f"\tStatus Updated: {response_data['total']}")

    print("[SYS] Would you like to update the datafile?")
    while(True):
        ans = input("\t(y/n) ")
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
    jql = "project in (KNT, KM) and type = Bug ORDER BY created DESC"
    
    extracted_data = []
    
    print("[SYS] Getting Issues...[", end="", flush=True)
    while(True):
        response = request_jira(jql, offset)
        response_data = json.loads(response.text)
        
        offset += 100
        #print(len(response_data['issues']))
        print("-", end="", flush=True)
        if(len(response_data['issues']) == 0):
            break
        
        extract_fields(response_data, extracted_data)
    print("]done.")

    #upload to openAI

    fpath = jsonWriter(extracted_data)
    
    update_asst_file(fpath)
    
def update_asst_file(fpath):
    print("[SYS] Uploading datafile to assistant...", end="", flush=True)
    file = client.files.create(
        file=open(fpath, "rb"),
        purpose="assistants"
    )
    
    fid = file.id
    
    client.beta.assistants.update(
        asst_id,
        file_ids=[fid],
    )
    
    print("done")
    
    write_last_update()
        
def last_update_format():
    last_update_str = read_last_update()
    last_update_dt = datetime.fromisoformat(last_update_str)
    last_update = last_update_dt.strftime("%Y-%m-%d %H:%M")
    
    return last_update
    
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
    now_st = str(datetime.now().strftime('%Y-%m-%dT%H-%M-%S'))
    
    datafiles_path = os.path.join(os.getcwd(), "datafiles")
    if not os.path.exists(datafiles_path):
        os.makedirs(datafiles_path)
        
    fname = "bugdata_" + now_st + ".json"
    fpath = os.path.join(datafiles_path, fname)
    
    try:
        with open(fpath, 'r+') as file:
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
        with open(fpath, 'w') as file:
            json.dump(data, file, indent=4)
            
    return fpath
    
def get_links(keys):
    browse = os.getenv('browse_url')
    linklist = []
    for item in keys:
        linklist.append(browse + item)
    
    inline_links = []
    for item1, item2 in zip(linklist, keys):
        inline_links.append("\033]8;;{}\033\\{}\033]8;;\033\\".format(item1, item2))

    keys_and_links = []
    for item1, item2 in zip(keys, inline_links):
        keys_and_links.append((item1, item2))
    
    return keys_and_links

def write_last_update():
    """Write the current timestamp to the JSON file."""
    data = {"lastUpdate": datetime.now().isoformat()}
    with open('last_update.json', 'w') as f:
        json.dump(data, f)

def read_last_update():
    """Read the lastUpdateed timestamp from the JSON file."""
    try:
        with open('last_update.json', 'r') as f:
            data = json.load(f)
        return data.get('lastUpdate')
    except FileNotFoundError:
        # Return None if the file doesn't exist
        return None
    
def should_update():
    #for time based auto updates. Not used for now
    last_update = read_last_update()
    last_update_dt = datetime.fromisoformat(last_update)
    cur_time = datetime.now()
    
    time_diff = cur_time - last_update_dt
    thresh = timedelta(minutes=30)
    
    if time_diff > thresh:
        return True
    else:
        return False
    
def clickable(str, pairs):
    for item in pairs:
        str = str.replace(item[0], item[1])
    
    return str
    
def ask_assistant(query):
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query
    )
    #print(message)
    
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=asst_id,
        instructions="You are to return all the relevant issues up to a maximum of 5. Returned issues must be in the following format only: <key> | <summary>"
    )
    
    if run.status == 'completed': 
        msg_response = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        msg_data = msg_response.data
        #print(msg_response)
        latest = msg_data[0].content[0].text.value
        keys = get_keys(latest)
        if keys:
            keypairs = get_links(keys)
            wlinks = clickable(latest, keypairs)
            print("[ASSISTANT] ", wlinks)
        else:
            print("[ASSISTANT] ", latest)
            
    else:
        print(run.status)
    
def main():
    os.system('cls')
    print("What bugs are you looking for?      (type: 'help' for commands)\n")
    while(True):
        
        prompt = input("[QUERY] ")
        match prompt.lower():
            case "help":
                print("\t'help'\t\t- show menu\n\t'bye'\t\t- exit\n\t'update'\t-update the jira isues datafile without checking for changes\n\t'check'\t\t- check for changes to the jira issues")
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
