"""
Script to map OpenAI file IDs to local PDF filenames.
Run this to create a mapping file for download links.
"""
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

# Get assistant to find vector store
assistant = client.beta.assistants.retrieve(ASSISTANT_ID)
vector_store_ids = assistant.tool_resources.file_search.vector_store_ids if hasattr(assistant.tool_resources, 'file_search') and assistant.tool_resources.file_search else []

file_id_to_filename = {}

if vector_store_ids:
    vector_store_id = vector_store_ids[0]
    # List files in vector store
    files = client.beta.vector_stores.files.list(vector_store_id=vector_store_id)
    
    # Get file details
    for file_obj in files.data:
        file_id = file_obj.id
        file_detail = client.files.retrieve(file_id)
        filename = file_detail.filename
        file_id_to_filename[file_id] = filename

# Save mapping
with open('file_id_mapping.json', 'w') as f:
    json.dump(file_id_to_filename, f, indent=2)

print(f"Mapped {len(file_id_to_filename)} files:")
for file_id, filename in file_id_to_filename.items():
    print(f"  {file_id}: {filename}")

