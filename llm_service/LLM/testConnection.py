from ollama import Client


def test_connection(mail: str) -> str:
    """Send one mail text to the local Ollama model and return the raw response text."""

    client = Client(host="http://localhost:11434")

    response = client.generate(
        model="llama3.2",
            prompt = f"""
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
- the text only contains a personal name
- the text only contains a generic email or placeholder
- the text only contains test data
- the text contains words like test, demo, sample, dummy, example without clear company evidence
- there is no clear company or organization reference

Output format:
If True, output exactly:

True
Name:
Company:
Email:
Phone:
Address:
Website:

If False, output exactly:

False

Rules:
- Only one final answer
- No explanations
- No notes
- No extra text
- Missing fields must stay empty
- Generic placeholders like test, Test1, Test2, demo, sample do not count as company evidence
- A single email address alone does not make it company-related
- A single name alone does not make it company-related

Email:
\"\"\"{mail}\"\"\"
""".strip())
    return response["response"]
