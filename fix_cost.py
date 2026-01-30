from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

# Update existing assistant to use cheaper model
client.beta.assistants.update(
    assistant_id=ASSISTANT_ID,
    model="gpt-4o-mini"  # 15x cheaper than gpt-4o
)

print("✅ Updated assistant to use gpt-4o-mini (much cheaper!)")
print("Cost should drop from $0.05 to ~$0.003-0.01 per message")