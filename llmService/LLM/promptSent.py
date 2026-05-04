_PROMPT_SENT = """
You will receive the content/context of an email.

Your task:
Generate a short, precise storage name for this email.

Rules:
- Output only valid JSON.
- Do not output plain text.
- Do not output a JSON array.
- Do not output a JSON set.
- The JSON object must contain exactly one key: target_file_name.
- Maximum target_file_name length: 60 characters.
- Do not include any project name, company-internal code name, or folder name.
- Focus only on the most relevant information: what the email states, requests, confirms, rejects, asks, or announces.
- Make it understandable without reading the full email.
- ONLY professional German with appropriate business terminology.
- No period at the end.

Required format:
{{"target_file_name": "kurzer dateiname"}}

Email context:
{EMAIL_CONTEXT}
""".strip()


_PROMPT_SHORTEN_SENT_FILENAME = """
Shorten the following German storage name to maximum 60 characters.

Rules:
- Output only valid JSON.
- The JSON object must contain exactly one key: target_file_name.
- Keep the original meaning.
- Use professional German.
- No period at the end.
- Maximum target_file_name length: 60 characters.

Required format:
{{"target_file_name": "kurzer dateiname"}}

Storage name:
{TARGET_FILE_NAME}
""".strip()
