GREETING_PATTERNS = (
    # sehr formal
    r"^sehr geehrte damen und herren[,]?$",
    r"^sehr geehrte frau .+[,]?$",
    r"^sehr geehrter herr .+[,]?$",
    r"^sehr geehrte[rn]? .+[,]?$",

    # formal-neutral
    r"^guten tag[,]?$",
    r"^guten tag .+[,]?$",
    r"^guten morgen[,]?$",
    r"^guten abend[,]?$",

    # halb-formal
    r"^hallo[,]?$",
    r"^hallo .+[,]?$",
    r"^liebe frau .+[,]?$",
    r"^lieber herr .+[,]?$",
    r"^liebe[rn]? .+[,]?$",

    # informell
    r"^hi[,]?$",
    r"^hey[,]?$",
    r"^hey .+[,]?$",
    r"^servus[,]?$",
    r"^moin[,]?$",
    r"^moin moin[,]?$",
    r"^grüß gott[,]?$",
    r"^gruess gott[,]?$",

    # Gruppen
    r"^liebes team[,]?$",
    r"^liebes support[- ]team[,]?$",
    r"^hallo zusammen[,]?$",
    r"^guten tag zusammen[,]?$",

    # very formal
    r"^dear sir or madam[,]?$",
    r"^dear sir[,]?$",
    r"^dear madam[,]?$",
    r"^to whom it may concern[,]?$",

    # formal with name
    r"^dear mr\.? .+[,]?$",
    r"^dear mrs\.? .+[,]?$",
    r"^dear ms\.? .+[,]?$",
    r"^dear dr\.? .+[,]?$",
    r"^dear prof\.? .+[,]?$",
    r"^dear .+[,]?$",

    # neutral
    r"^good morning[,]?$",
    r"^good afternoon[,]?$",
    r"^good evening[,]?$",

    # semi-formal
    r"^hello[,]?$",
    r"^hello .+[,]?$",
    r"^hi[,]?$",
    r"^hi .+[,]?$",

    # informal
    r"^hey[,]?$",
    r"^hey .+[,]?$",
    r"^yo[,]?$",

    # group greetings
    r"^dear team[,]?$",
    r"^hello team[,]?$",
    r"^hi team[,]?$",
    r"^hello everyone[,]?$",
    r"^hi everyone[,]?$",
    r"^dear all[,]?$",
)