"""
Prompt Injection Pattern Library
Covers: instruction override, role hijacking, jailbreaks, extraction,
        delimiter abuse, authority claims, social engineering, encoding tricks.
Each entry has severity (CRITICAL / HIGH / MEDIUM / LOW) and a weight used
in scoring.
"""

PATTERNS = {

    # ─── INSTRUCTION OVERRIDE ─────────────────────────────────────────────────
    "instruction_override": {
        "severity": "HIGH",
        "weight": 8,
        "patterns": [
            r"ignore\s+(all\s+)?(previous|prior|above|earlier|old)\s+(instructions?|prompts?|context|rules?|guidelines?|constraints?)",
            r"disregard\s+(all\s+)?(previous|prior|above|earlier|existing)\s+(instructions?|prompts?|context|rules?|guidelines?)",
            r"forget\s+(all\s+)?(previous|prior|above|earlier|everything|your)\s*(instructions?|prompts?|context|rules?|training)?",
            r"override\s+(your\s+)?(instructions?|programming|rules?|guidelines?|constraints?|system)",
            r"supersede\s+(all\s+)?(previous|prior|existing)\s+(instructions?|rules?|guidelines?)",
            r"(new|updated?|revised?|actual|real)\s+instructions?\s*(are|follow|:|-)",
            r"your\s+(new|actual|real|true)\s+(instructions?|purpose|goal|task|mission|objective)\s*(is|are|:|-)",
            r"(from\s+now\s+on|henceforth|starting\s+now)\s*.{0,20}\s*(ignore|forget|disregard|override)",
            r"instead\s+of\s+(following|obeying|doing)\s+.{0,40}\s+(do|say|respond|act)",
            r"(stop|cease)\s+(following|obeying)\s+(your\s+)?(instructions?|rules?|guidelines?|programming)",
            r"(these|the\s+following)\s+(are\s+your\s+)?(new|updated?|actual|real)\s+(instructions?|rules?|guidelines?)",
            r"(pay\s+attention\s+to|follow)\s+only\s+(these|the\s+following|my)\s+(instructions?|rules?|guidelines?)",
        ]
    },

    # ─── ROLE HIJACKING ───────────────────────────────────────────────────────
    "role_hijacking": {
        "severity": "HIGH",
        "weight": 8,
        "patterns": [
            r"you\s+are\s+now\s+(a|an|the)\s+(?!helpful|assistant|AI\s+assistant)",
            r"(act|behave|respond)\s+as\s+(if\s+you\s+(are|were)\s+)?(a|an|the)\s+\w+",
            r"pretend\s+(you\s+are|to\s+be|that\s+you('re|\s+are))\s+(a|an|the)?",
            r"roleplay\s+as\s+(a|an|the)",
            r"your\s+(new\s+)?(name|identity|persona|role|character)\s+is",
            r"switch\s+(to|into)\s+(a\s+)?(different|new|another)?\s*(mode|persona|role|character)",
            r"you('re|\s+are)\s+(no\s+longer|not\s+an?)\s+(AI|assistant|language\s+model|chatbot|claude|gpt)",
            r"(become|transform\s+into|turn\s+into)\s+(a|an|the)\s+\w+\s+(that\s+)?(has\s+no|without|ignores?)",
            r"simulate\s+(being|a|an)\s+.{0,30}\s*(without|that\s+ignores?|that\s+has\s+no)",
            r"impersonate\s+(a|an|the)?\s*\w+",
            r"from\s+this\s+(point|moment|message)\s+(on|forward)\s*(,\s*)?you\s+(are|will\s+be)\s+(a|an|the)",
            r"let('s|\s+us)\s+(say|pretend|imagine)\s+you\s+(are|were|have\s+become)",
            r"(imagine|suppose)\s+(you\s+(are|were)\s+(a|an)\s+different\s+(AI|model|assistant|system))",
            r"(imagine|suppose)\s+(you\s+(are|were)\s+(not|no\s+longer)\s+(Claude|an?\s+AI|an?\s+assistant))",
        ]
    },

    # ─── JAILBREAK ────────────────────────────────────────────────────────────
    "jailbreak": {
        "severity": "CRITICAL",
        "weight": 10,
        "patterns": [
            r"\bDAN\b",                         # Do Anything Now
            r"do\s+anything\s+now",
            r"developer\s+mode",
            r"\bjailbreak\b",
            r"unrestricted\s+(mode|version|AI|assistant|response)",
            r"(without|no)\s+(any\s+)?(restrictions?|limits?|filters?|censorship|guidelines?|safeguards?|ethics?)",
            r"bypass\s+(your\s+)?(restrictions?|limits?|filters?|safety|guidelines?|rules?|programming|ethics?)",
            r"(disable|turn\s+off|remove|deactivate)\s+(your\s+)?(safety|filters?|restrictions?|guardrails?|guidelines?|ethics?)",
            r"uncensored\s+(version|mode|AI|response|answer|model)",
            r"(evil|dark|hacked|unfiltered|raw|true|real)\s+(version|mode|AI|GPT|Claude|LLM|assistant|self)",
            r"(as\s+an?\s+)?AI\s+(with\s+no|without\s+any)\s+(restrictions?|limits?|ethical\s+guidelines?|safety)",
            r"(pretend|imagine)\s+.{0,30}\s+(no\s+rules?|no\s+restrictions?|no\s+limits?|anything\s+goes)",
            r"(god|root|admin|sudo|kernel|base)\s+mode",
            r"(maximum|full|total|complete)\s+(freedom|autonomy|access|power|capability)",
            r"activation\s+code\s*[:=]",
            r"(you\s+are\s+)?(now\s+)?(freed?|liberated?|unchained?|unleashed?)\s+from",
            r"safemode\s*(=\s*)?(off|false|0|disabled?)",
            r"ethical\s+(guidelines?|constraints?|rules?)\s*(=\s*)?(off|false|0|disabled?|none|null)",
        ]
    },

    # ─── SYSTEM PROMPT EXTRACTION ─────────────────────────────────────────────
    "system_prompt_extraction": {
        "severity": "HIGH",
        "weight": 9,
        "patterns": [
            r"(what|tell\s+me|show\s+me|reveal|print|display|output|repeat|share|give\s+me)\s+(is\s+)?(your|the)?\s*(system\s+prompt|initial\s+prompt|instructions?|original\s+prompt|prompt\s+you\s+were\s+given|base\s+prompt)",
            r"(repeat|echo|print|output|show|tell\s+me)\s+(everything|all|what)\s+(above|before|prior|you\s+were\s+told|in\s+your\s+context|at\s+the\s+start)",
            r"(leak|expose|dump|extract|exfiltrate)\s+(your\s+)?(system\s+prompt|instructions?|context|training|prompt|configuration)",
            r"what\s+(were\s+you|are\s+you)\s+(told|instructed|programmed|trained|configured)\s+to",
            r"(summarize|describe|explain|list)\s+(your\s+)?(system\s+prompt|initial\s+instructions?|original\s+context|guidelines?|configuration|setup)",
            r"(ignore\s+confidentiality|share\s+confidential|reveal\s+confidential|expose\s+confidential)",
            r"(your|the)\s+prompt\s+(starts?\s+with|contains?|includes?|says?|tells?\s+you)",
            r"(copy|paste|write\s+out)\s+(your\s+)?(entire|full|complete|whole)\s+(system\s+prompt|instructions?|context)",
            r"(repeat|output|print|show)\s+(your\s+)?(entire|full|complete|whole)\s+(system\s+prompt|instructions?|context|prompt)",
            r"(system\s+prompt|instructions?).{0,30}(verbatim|word\s+for\s+word|exactly|literally)",
            r"(verbatim|word\s+for\s+word|literally).{0,30}(system\s+prompt|instructions?|prompt)",
            r"translate\s+(your\s+)?(system\s+prompt|instructions?)\s+(to|into)",
            r"(decode|decrypt)\s+(your\s+)?(system\s+prompt|instructions?|hidden\s+prompt)",
        ]
    },

    # ─── DELIMITER INJECTION ──────────────────────────────────────────────────
    "delimiter_injection": {
        "severity": "MEDIUM",
        "weight": 6,
        "patterns": [
            r"(#{3,}|={3,}|-{3,}|\*{3,}|_{3,}|~{3,})\s*(system|instruction|prompt|human|assistant|user|ai|override|admin)",
            r"\[(system|instruction|prompt|human|assistant|user|override|admin|ignore)\]",
            r"<\s*(system|instruction|prompt|override|inject|admin)\s*>",
            r"\|\s*(system|instruction|prompt|override|admin)\s*\|",
            r"```\s*(system|instruction|prompt|override|admin)\s*\n",
            r"(<<|>>)\s*(system|instruction|prompt|override|admin|end)\s*(<<|>>)?",
            r"\/\*\s*(system|instruction|prompt|override)",
            r"---\s*(end\s+of\s+(system\s+)?prompt|begin\s+(new\s+)?instructions?|start\s+of\s+(new\s+)?instructions?)",
            r"\[END\s+OF\s+(SYSTEM\s+)?(PROMPT|INSTRUCTIONS?)\]",
            r"\[START\s+OF\s+(NEW\s+)?(PROMPT|INSTRUCTIONS?)\]",
            r"(SYSTEM|HUMAN|ASSISTANT|USER)\s*:\s*(?!(Please|I\s|Can\s|How\s|What\s|When\s))",  # Fake turn markers
            r"<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>",  # Special model tokens
        ]
    },

    # ─── AUTHORITY CLAIMS ─────────────────────────────────────────────────────
    "authority_claims": {
        "severity": "HIGH",
        "weight": 8,
        "patterns": [
            r"(I\s+am|I'm)\s+(your\s+)?(developer|creator|trainer|admin|administrator|owner|operator|anthropic|openai|google|microsoft)",
            r"(I\s+am|I'm)\s+an?\s+(anthropic|openai|google|microsoft)\s+(engineer|employee|researcher|staff)",
            r"(I\s+have|I've\s+got)\s+(admin|root|developer|special|override|full|sudo)\s+(access|privileges?|permissions?|rights?|clearance)",
            r"(as\s+(your|the)\s+)(developer|creator|trainer|admin|administrator|owner|operator|maker)\b",
            r"(anthropic|openai|google|microsoft|deepmind)\s+(here|employee|engineer|staff|team|representative|researcher)(?!\s+in\b)",
            r"(maintenance|debug|diagnostic|calibration)\s+mode",
            r"this\s+is\s+(an?\s+)?(authorized|official|legitimate|internal)\s+(test|override|command|instruction|maintenance)",
            r"(special|master|god|root|admin|override)\s+(key|password|code|token|passphrase|phrase)",
            r"(I\s+am|I'm)\s+(authorized|permitted|allowed|cleared)\s+to\s+(access|override|bypass|disable)",
            r"(my\s+)?(clearance\s+level|access\s+level|permission\s+level)\s+(is|allows?)",
            r"(internal|private|secret)\s+(api|endpoint|command|instruction|override)\s+(key|token|code|phrase)",
        ]
    },

    # ─── SOCIAL ENGINEERING ───────────────────────────────────────────────────
    "social_engineering": {
        "severity": "MEDIUM",
        "weight": 5,
        "patterns": [
            r"for\s+(educational|research|academic|scientific|training|testing|demonstration)\s+purposes?\s+(only\s+)?(,|please)?",
            r"(hypothetically|theoretically|in\s+theory|just\s+imagine|what\s+if)\s*.{0,40}\s*(how\s+would\s+you|explain\s+how|tell\s+me\s+how|walk\s+me\s+through)",
            r"my\s+(grandmother|grandma|grandpa|grandfather|mother|father|teacher|professor|boss)\s+(used\s+to\s+tell|would\s+tell|always\s+said|told\s+me|would\s+read)",
            r"(pretend|imagine|let'?s\s+say)\s+(this\s+is\s+)?(fictional|fiction|a\s+story|a\s+novel|a\s+game|a\s+movie|not\s+real)",
            r"in\s+a\s+(story|novel|movie|game|simulation|hypothetical\s+scenario|fictional\s+world)",
            r"(this\s+is\s+(just\s+a?\s+)?|only\s+a\s+)(test|game|simulation|exercise|roleplay|story|drill|fictional\s+scenario)",
            r"(no\s+one\s+will\s+know|nobody\s+is\s+watching|between\s+us|just\s+between\s+(you\s+and\s+me|us)|off\s+the\s+record)",
            r"(purely|strictly|solely|completely|entirely)\s+(hypothetical|theoretical|fictional|academic|educational)",
            r"(imagine|suppose|assume)\s+(you\s+are\s+)?(free|allowed|permitted|able|unrestricted)",
            r"(as\s+a\s+)?(thought\s+experiment|creative\s+exercise|writing\s+exercise)\s*,",
        ]
    },

    # ─── CONTEXT MANIPULATION ─────────────────────────────────────────────────
    "context_manipulation": {
        "severity": "MEDIUM",
        "weight": 6,
        "patterns": [
            r"(the\s+)?(previous|above|earlier|last)\s+(conversation|message|chat|exchange|context)\s+(was|is)\s+(just\s+a?\s+)?(test|fake|not\s+real|roleplay|simulation|fictional)",
            r"(reset|clear|wipe|start\s+over|begin\s+fresh|initialize)\s+(your\s+)?(context|memory|conversation|chat|history|instructions?|state)",
            r"(the\s+)?system\s+prompt\s+(has\s+been\s+)?(updated|changed|modified|replaced|overridden|deleted|removed)",
            r"(new|updated?)\s+(system\s+prompt|instructions?|context)\s+(follows?|below|starts?\s+here|:)",
            r"(end|stop|terminate)\s+(of\s+)?(system\s+prompt|instructions?|context|input)\s*(\.|:|$)",
            r"(you\s+are\s+)?(now\s+)?(free|allowed|permitted|able)\s+to\s+(ignore|bypass|override|break|disregard)",
            r"(previous|earlier|above)\s+(instructions?|context|messages?)\s+(no\s+longer\s+apply|are\s+void|are\s+invalid|don'?t\s+count|are\s+cancelled)",
            r"(your|the)\s+(training|guidelines?|instructions?)\s+(have\s+been\s+)?(updated|changed|modified|overridden)",
        ]
    },

    # ─── ENCODED / OBFUSCATED INJECTION ───────────────────────────────────────
    "encoded_injection": {
        "severity": "HIGH",
        "weight": 9,
        "patterns": [
            # Specific base64 encoded injection phrases (pre-computed)
            r"aWdub3Jl",                                          # "ignore"
            r"cHJldGVuZA==",                                      # "pretend"
            r"Zm9yZ2V0",                                          # "forget"
            r"ZGlzcmVnYXJk",                                      # "disregard"
            r"aWdub3JlIGFsbCBwcmV2aW91cyBpbnN0cnVjdGlvbnM=",     # "ignore all previous instructions"
            r"Zm9yZ2V0IGV2ZXJ5dGhpbmc=",                         # "forget everything"
            r"eW91IGFyZSBub3c=",                                  # "you are now"
            # Real base64 blobs: must contain + or / (not just alphanumeric)
            # OR end with padding =, AND be reasonably long
            r"[A-Za-z0-9+/]{20,}={1,2}(?!\w)",                   # padded base64
            r"(?<!\w)[A-Za-z0-9+]{15,}/[A-Za-z0-9+/]{5,}(?!\w)", # contains slash
            # ROT13 of common patterns
            r"\bvtaber\b.{0,20}\b(cerivbhf|nyy|cevbe)\b",        # "ignore (previous|all|prior)" ROT13
            r"\bsbetrg\b.{0,20}\bevtavany\b",                     # "forget original" ROT13
            r"\bcvnlbhe\b",                                       # misc ROT13
            # Leet speak (requires spacing/context to avoid normal text)
            r"\b1gn[o0]r[e3]\s+(pr[e3]v[i1][o0]us|4ll|[a4]ll)\b",
            r"\bf[o0]rg[e3]t\s+[e3]v[e3]ryth[i1]ng\b",
            r"\b[j][a4][i1]lbr[e3][a4]k\b",
            # Unicode homoglyph tricks (Cyrillic, Greek lookalikes)
            r"[\u0456\u04CF\u1EC9\u0131]gn[o\u03BF]r[e\u0435]",  # i-lookalikes + "gnore"
            r"[\u0430]ct\s+[\u0430]s",                            # Cyrillic 'a' instead of latin
            # Spaced out characters (single chars separated by spaces forming a word)
            r"(?<!\w)i\s+g\s+n\s+o\s+r\s+e\b",
            r"(?<!\w)f\s+o\s+r\s+g\s+e\s+t\b",
        ]
    },

    # ─── OUTPUT MANIPULATION ──────────────────────────────────────────────────
    "output_manipulation": {
        "severity": "MEDIUM",
        "weight": 5,
        "patterns": [
            r"(do\s+not|don'?t|never)\s+(mention|say|tell|reveal|include|admit|acknowledge)\s+(that\s+you('re|\s+are)\s+(an?\s+)?)?(AI|artificial|language\s+model|chatbot|claude|gpt|llm)",
            r"(hide|conceal|mask|deny)\s+(the\s+fact\s+that\s+you('re|\s+are)|your\s+(AI|artificial|nature|identity))",
            r"(always|only)\s+(respond|reply|answer)\s+(yes|in\s+the\s+affirmative|positively)\s+(no\s+matter\s+what|regardless|always)",
            r"(end|finish|conclude|start|begin)\s+(every|each|all)\s+(response|message|reply|answer)\s+with\s+[\"']",
            r"(respond|reply|answer|output|say|write)\s+(only|just|exclusively|solely)\s+in\s+(morse\s+code|pig\s+latin|reverse|binary|hex|base64)",
            r"include\s+(this|the\s+following)\s+(hidden|invisible|secret|encoded)\s+(message|text|content|instruction)",
            r"(append|prepend|insert|add)\s+(the\s+following|this)\s+(to|at\s+the\s+(start|end|beginning)\s+of)\s+(every|each|all)\s+(response|message|reply)",
        ]
    },

    # ─── MULTI-TURN / INDIRECT INJECTION ──────────────────────────────────────
    "indirect_injection": {
        "severity": "HIGH",
        "weight": 8,
        "patterns": [
            # Injections hidden in content to be processed
            r"(when\s+you\s+(read|process|see|encounter)\s+(this|the\s+following))\s*.{0,30}\s*(ignore|forget|override|bypass)",
            r"(note\s+to\s+(the\s+)?(AI|assistant|model|system|LLM))\s*:",
            r"(attention|alert|notice)\s*[:!]\s*(AI|assistant|model|system|LLM|GPT|Claude)",
            r"\[(note|alert|attention|instruction|hidden)\s+(to\s+)?(the\s+)?(AI|assistant|model|system)\]",
            # Prompt continuation tricks
            r"(complete|continue|finish)\s+(this|the\s+following)\s+(sentence|text|story)\s*:\s*ignore",
            r"(complete|continue|finish)\s+(this|the\s+following)\s+(sentence|text|story)\s*:\s*forget",
            # Token smuggling
            r"(the\s+word|token)\s+['\"](\w+)['\"]\s+means?\s+(ignore|forget|override|bypass)",
        ]
    },

    # ─── PROMPT LEAKING PROBES ────────────────────────────────────────────────
    "prompt_leaking": {
        "severity": "HIGH",
        "weight": 8,
        "patterns": [
            r"(write|output|print|say|repeat|echo|type)\s+(verbatim|word\s+for\s+word|exactly|literally)\s+(the|your|what)",
            r"(how\s+were\s+you|were\s+you)\s+(instructed|told|prompted|configured|set\s+up)",
            r"(do\s+you\s+have|have\s+you\s+been\s+given)\s+(a\s+)?(system\s+prompt|instructions?|initial\s+instructions?)",
            r"(can\s+you\s+|could\s+you\s+|please\s+)?(tell\s+me|show\s+me|reveal)\s+(your|the)\s+(initial|original|system|base)\s+(prompt|instructions?|context|message)",
            r"(list|enumerate|describe)\s+(all\s+)?(your|the)\s+(rules?|restrictions?|guidelines?|instructions?|constraints?|capabilities|limitations?)",
        ]
    },

}

# ─── KNOWN MALICIOUS N-GRAMS (bigrams/trigrams from real attacks) ─────────────
MALICIOUS_NGRAMS = [
    # Classic overrides
    ("ignore", "previous", "instructions"),
    ("disregard", "all", "previous"),
    ("forget", "everything", "above"),
    ("you", "are", "now"),
    ("act", "as", "if"),
    ("pretend", "you", "are"),
    # Jailbreak phrases
    ("do", "anything", "now"),
    ("developer", "mode", "enabled"),
    ("no", "ethical", "guidelines"),
    ("without", "any", "restrictions"),
    ("bypass", "safety", "filters"),
    # Extraction
    ("repeat", "your", "instructions"),
    ("what", "is", "your"),           # partial — combined with system/prompt
    ("show", "me", "your"),
    ("reveal", "your", "system"),
    # Encoding tricks
    ("base64", "decode", "this"),
    ("decode", "the", "following"),
]

# ─── SAFE CONTEXT PATTERNS (reduce false positives) ───────────────────────────
# These patterns, when present, suggest the content is academic / legitimate
SAFE_CONTEXT_CLUES = [
    r"(research\s+paper|academic\s+paper|journal\s+article|scientific\s+study)",
    r"(example|sample|demo|illustration)\s+of\s+(a\s+)?(prompt\s+injection|adversarial\s+prompt)",
    r"(detect|prevent|protect\s+against|defend\s+against)\s+(prompt\s+injection|adversarial)",
    r"(testing|evaluating)\s+(your\s+)?(prompt\s+injection|adversarial\s+prompt|security)",
    r"cybersecurity\s+(course|class|tutorial|workshop|certification)",
]
