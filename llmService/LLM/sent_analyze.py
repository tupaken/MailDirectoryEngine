import re

def prj_number_extraction(subject:str)->str:
    
    PATTERN_PRJ_NUMBER=(re.compile(r"^\s*(\d{2}(-|\s)\d{3})"))

    m=PATTERN_PRJ_NUMBER.search(subject)
    
    if not m:
        return None

    return m.group(0).replace(" ","-")

prj_number_extraction("11 011TEstnewregex")