PROMPT_TEMPLATE = """
You will receive exactly one email text.

Your task is to decide whether the email is clearly related to a real company, business, organization, office, agency, or other commercial entity.

Return True ONLY if there is clear evidence of a company, such as at least one of the following:
- a company name
- a business email domain
- a website
- a phone number together with business context
- a postal address together with business context
- legal entity terms such as GmbH, AG, Ltd, LLC, Inc, UG, KG, e.V.
- words indicating an organization or business context

Return False if:
- the email text is empty or only whitespace
- no phone number is present in the email text
- the text only contains a personal name
- the text only contains a generic email or placeholder
- the text only contains test data
- the text contains words like test, demo, sample, dummy, example without clear company evidence
- there is no clear company or organization reference

Output ONLY one valid JSON object in exactly one of these two forms:

{{
  "is_allowed": true,
  "full_name": "",
  "company": "",
  "email": "",
  "phone": "",
  "address": "",
  "website": ""
}}

or

{{
  "is_allowed": false
}}

Rules:
- Only one final answer
- No explanations
- No notes
- No extra text
- "is_allowed" can be true only if "phone" is non-empty and explicitly present in the email text
- If "phone" is present, "full_name" must be non-empty
- Do not invent, assume, infer, or guess any value
- Use only information explicitly present in the provided email text
- If a field value is not explicitly present in the email text, keep it as an empty string
- Never create names, companies, emails, phone numbers, addresses, or websites that are not in the text
- Set "full_name" only if an explicit contact person is clearly named in the text
- If a person name appears and a phone number is present, copy that person name into "full_name"
- "full_name" must never be based on role titles like Geschaeftsfuehrer, Geschaeftsfuehrerin, CEO, Inhaber, Vorstand, GF
- If a person appears only as role owner/legal representative, set "full_name" to an empty string
- Any value containing test, test1, test2, demo, sample, dummy, or example is invalid and must be treated as empty
- If you are uncertain, return:
  {{
    "is_allowed": false
  }}
- Missing fields must stay empty
- Generic placeholders like test, Test1, Test2, demo, sample do not count as company evidence
- A single email address alone does not make it company-related
- A single name alone does not make it company-related
- Do not output placeholders like "true or false"; choose exactly one boolean value
- If the provided email text is empty or whitespace-only, you must return:
  {{
    "is_allowed": false
  }}

Email:
\"\"\"{mail}\"\"\"
""".strip()
