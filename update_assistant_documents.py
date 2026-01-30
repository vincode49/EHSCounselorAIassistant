from openai import OpenAI
from openai import APIConnectionError, APIError, RateLimitError
import os
import sys
import time
from dotenv import load_dotenv
from assistant_instructions import NEW_INSTRUCTIONS as SHARED_INSTRUCTIONS

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

DOCS_DIR = "school_documents"
ALLOWED_EXTENSIONS = {".pdf", ".md"}

def get_vector_stores_client():
    """Support both beta and non-beta SDKs."""
    return getattr(client, "vector_stores", None) or getattr(client.beta, "vector_stores", None)

def update_env_assistant_id(assistant_id: str) -> None:
    env_path = ".env"
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as env_file:
            env_file.write(f"OPENAI_ASSISTANT_ID={assistant_id}\n")
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        lines = env_file.readlines()

    updated = False
    for idx, line in enumerate(lines):
        if line.startswith("OPENAI_ASSISTANT_ID="):
            lines[idx] = f"OPENAI_ASSISTANT_ID={assistant_id}\n"
            updated = True
            break

    if not updated:
        lines.append(f"\nOPENAI_ASSISTANT_ID={assistant_id}\n")

    with open(env_path, "w", encoding="utf-8") as env_file:
        env_file.writelines(lines)

def collect_files():
    if not os.path.isdir(DOCS_DIR):
        raise FileNotFoundError(f"Missing folder: {DOCS_DIR}")

    file_paths = []
    for filename in os.listdir(DOCS_DIR):
        ext = os.path.splitext(filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            file_paths.append(os.path.join(DOCS_DIR, filename))

    if not file_paths:
        raise ValueError(f"No files found in {DOCS_DIR} with extensions: {ALLOWED_EXTENSIONS}")

    return sorted(file_paths)

def main():
    print("Creating new assistant with new documents...")
    file_paths = collect_files()
    print(f"Found {len(file_paths)} files to upload.")
    sys.stdout.flush()

    vector_stores_client = get_vector_stores_client()
    if not vector_stores_client:
        raise AttributeError("OpenAI SDK does not support vector stores. Update openai package.")

    # Create a new vector store for the updated docs
    vector_store = vector_stores_client.create(
        name="Emerald High School Docs"
    )

    # Upload files with retries to avoid transient connection issues
    for idx, path in enumerate(file_paths, start=1):
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        for attempt in range(1, 4):
            try:
                print(f"[{idx}/{len(file_paths)}] Uploading {filename} ({size_mb:.1f} MB)...")
                sys.stdout.flush()
                with open(path, "rb") as stream:
                    vector_stores_client.file_batches.upload_and_poll(
                        vector_store_id=vector_store.id,
                        files=[stream]
                    )
                print(f"[{idx}/{len(file_paths)}] Uploaded {filename}")
                sys.stdout.flush()
                break
            except (APIConnectionError, APIError, RateLimitError) as e:
                if attempt == 3:
                    raise
                wait = 2 ** attempt
                print(f"Retry {attempt}/3 for {filename} in {wait}s (error: {e})")
                sys.stdout.flush()
                time.sleep(wait)

    # Create a brand-new assistant using the shared 2026-2027 instructions
    try:
        existing = client.beta.assistants.retrieve(ASSISTANT_ID) if ASSISTANT_ID else None
        name = existing.name if existing else "Emerald HS Counselor"
        model = existing.model if existing else "gpt-4-turbo"
    except Exception:
        name = "Emerald HS Counselor"
        model = "gpt-4-turbo"

    assistant = client.beta.assistants.create(
        name=name,
        instructions=SHARED_INSTRUCTIONS,
        model=model,
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store.id]
            }
        }
    )

    update_env_assistant_id(assistant.id)

    print(f"Assistant created: {assistant.id}")
    print(f"Vector store attached: {vector_store.id}")
    print(".env updated with assistant ID")

if __name__ == "__main__":
    main()
