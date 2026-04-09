_OUTPUT_SCHEMA = """
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
""".strip()

_COMMON_RULES = """
Rules:
- Only one final answer
- No explanations
- No notes
- No extra text
- "is_allowed" can be true only if "phone" is non-empty and explicitly present in the provided text
- If "phone" is present, "full_name" must be non-empty
- Do not invent, assume, infer, or guess any value
- Use only information explicitly present in the provided text
- If a field value is not explicitly present in the provided text, keep it as an empty string
- Never create names, companies, emails, phone numbers, addresses, or websites that are not in the text
- Set "full_name" only if an explicit contact person is clearly named in the text
- "full_name" must never be based on role titles like Geschaeftsfuehrer, Geschaeftsfuehrerin, CEO, Inhaber, Vorstand, GF
- If a person appears only as role owner/legal representative, set "full_name" to an empty string
- Treat German honorifics/titles as titles, not given names: Herr, Frau, Prof, Dr, Ing, Ingenieur
- If "full_name" includes those titles, keep only the real person name (first name + surname) in "full_name"
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
""".strip()

_PROMPT_CONTEXT_TEMPLATE_RAW = """
You will receive exactly one email context text (body without signature).

Your task is to decide whether this context is clearly related to a real company, business, organization, office, agency, or other commercial entity, and to extract explicit contact fields.

Return True ONLY if there is clear company evidence and a phone number.

Return False if:
- the text is empty or only whitespace
- no phone number is present in the text
- the text only contains a personal name
- the text only contains a generic email or placeholder
- the text only contains test data
- there is no clear company or organization reference

{output_schema}

{common_rules}

Context:
\"\"\"{mail}\"\"\"
""".strip()

_PROMPT_SIGNATURE_TEMPLATE_RAW = """
You will receive exactly one email signature block.

Your task is to decide whether this signature block contains explicit business contact data and to extract it.

Return True ONLY if:
- a phone number is explicitly present in the signature
- and at least one clear business/contact signal exists (company, business email, website, address, legal entity marker, or business role context)

Return False if:
- the signature is empty or only whitespace
- no phone number is present
- only a personal name is present without business evidence
- only placeholder/test content is present

{output_schema}

{common_rules}

Signature:
\"\"\"{mail}\"\"\"
""".strip()

PROMPT_CONTEXT_TEMPLATE = _PROMPT_CONTEXT_TEMPLATE_RAW.format(
    output_schema=_OUTPUT_SCHEMA,
    common_rules=_COMMON_RULES,
    mail="{mail}",
)
PROMPT_SIGNATURE_TEMPLATE = _PROMPT_SIGNATURE_TEMPLATE_RAW.format(
    output_schema=_OUTPUT_SCHEMA,
    common_rules=_COMMON_RULES,
    mail="{mail}",
)

# Backward compatibility for existing imports/tests that still reference PROMPT_TEMPLATE.
PROMPT_TEMPLATE = PROMPT_CONTEXT_TEMPLATE
