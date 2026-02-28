import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

print("Loading .env...")
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4.1-mini")

print("API key loaded?", "YES" if api_key else "NO")
print("Model:", model)

if not api_key:
    print("ERROR: OPENAI_API_KEY not found in environment.")
    sys.exit(1)

print("Creating OpenAI client...")
client = OpenAI(api_key=api_key)

text = """
This is a test document. It suggests moving the donation call-to-action higher in the newsletter,
adding a short bullet list of impact metrics, and removing redundant footer links.
"""

print("Sending request to OpenAI...")

try:
    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": (
                    "Summarize this document in 2-4 sentences focusing on what it is suggesting:\n\n"
                    + text
                ),
            }
        ],
        max_output_tokens=200,
    )

    print("Request completed successfully.")
    print("\n=== SUMMARY ===")
    print(resp.output_text)

except Exception as e:
    print("ERROR during API call:")
    print(type(e).__name__, str(e))
