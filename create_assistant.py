from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

print("Creating Assistant with file search (v2 API)...")

INSTRUCTIONS = """You are an AI counseling assistant for Emerald High School students. Help with course selection, college counseling, graduation requirements, clubs, and sports. Be friendly, supportive, and reference specific information from the uploaded school documents."""

# Upload files and create vector store
print("\nUploading files to vector store...")
pdf_folder = "school_documents"
file_paths = [os.path.join(pdf_folder, f) for f in os.listdir(pdf_folder) if f.endswith('.pdf')]

file_streams = [open(path, "rb") for path in file_paths]

# Create vector store with files
vector_store = client.beta.vector_stores.create(
    name="Emerald High School Docs"
)

# Upload files in batch
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vector_store.id,
    files=file_streams
)

# Close file streams
for stream in file_streams:
    stream.close()

print(f"✓ Uploaded {len(file_paths)} files to vector store {vector_store.id}")

# Create assistant with file search
assistant = client.beta.assistants.create(
    name="Emerald HS Counselor",
    instructions=INSTRUCTIONS,
    model="gpt-4-turbo",
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [vector_store.id]
        }
    }
)

print(f"\n✅ Assistant created: {assistant.id}")

# Save to .env
with open('.env', 'a', encoding='utf-8') as f:
    f.write(f"\nOPENAI_ASSISTANT_ID={assistant.id}\n")

print("✓ Saved to .env")
print("🎉 Setup complete!")
