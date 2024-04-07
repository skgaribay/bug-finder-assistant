import os, sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('api_key')
asst_id = os.getenv('assistant_id')
client = OpenAI(api_key=api_key)

thread = client.beta.threads.create()

while(True):
    query = input("[QUERY] ")
    if(query == "bye"):
        sys.exit()
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query
    )
    
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
        latest = msg_data[0]
        print("[ASSISTANT] ", latest.content[0].text.value)
    else:
        print(run.status)