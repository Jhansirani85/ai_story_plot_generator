import json
import requests

# Load dataset links
with open("datasets.json") as f:
    data = json.load(f)

all_prompts = []

# Fetch data
for url in data["story_prompts"]:
    response = requests.get(url)
    
    if response.status_code == 200:
        file_data = response.json()   # if JSON file
        all_prompts.extend(file_data)
    else:
        print("Failed to fetch:", url)

print(all_prompts)