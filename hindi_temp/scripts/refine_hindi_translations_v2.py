import re
import pandas as pd

p='evaluation/hindi_queries.xlsx'
df=pd.read_excel(p)

def translate(q):
    q=str(q).strip()

    pats=[
        (r'^What does (Section\s+[0-9A-Za-z()/.]+\s*(?:IPC|BNS|CrPC|BNSS)?) say\?$', r'\1 में क्या कहा गया है?'),
        (r'^Explain (Section\s+[0-9A-Za-z()/.]+\s*(?:IPC|BNS|CrPC|BNSS)?)$', r'\1 की व्याख्या करें।'),
        (r'^What is (Section\s+[0-9A-Za-z()/.]+\s*(?:IPC|BNS|CrPC|BNSS)?)\?$', r'\1 क्या है?'),
        (r'^What does (Section\s+[0-9A-Za-z()/.]+\s*(?:IPC|BNS|CrPC|BNSS)?) cover\?$', r'\1 में क्या प्रावधान है?'),
        (r'^What is the punishment for (.+) under (.+)\?$', r'\2 के तहत \1 के लिए क्या सजा है?'),
        (r'^What is the punishment for (.+) under Section\s*([0-9A-Za-z()/.]+)\?$', r'धारा \2 के तहत \1 के लिए क्या सजा है?'),
        (r'^What is the sentence for (.+) under (.+)\s*([0-9A-Za-z()/.]+)\?$', r'\2 की धारा \3 के तहत \1 की सजा क्या है?'),
        (r'^How many years for (.+) under (.+)\s*([0-9A-Za-z()/.]+)\?$', r'\2 की धारा \3 के तहत \1 के लिए कितने वर्ष की सजा है?'),
        (r'^How long imprisonment for (.+) under (.+)\s*([0-9A-Za-z()/.]+)\?$', r'\2 की धारा \3 के तहत \1 के लिए कितनी अवधि की सजा है?'),
        (r'^Has (.+) been struck down\?$', r'क्या \1 को निरस्त किया जा चुका है?'),
        (r'^Has (.+) been replaced\?$', r'क्या \1 को प्रतिस्थापित कर दिया गया है?'),
        (r'^Has (.+) been overruled\?$', r'क्या \1 को निरस्त किया जा चुका है?'),
        (r'^Has (.+) been challenged\?$', r'क्या \1 को चुनौती दी गई है?'),
        (r'^Has the (.+) been challenged after (.+)\?$', r'क्या \1 को \2 के बाद चुनौती दी गई है?'),
        (r'^What happened to (.+)\?$', r'\1 का क्या हुआ?'),
        (r'^What changed in (.+)\?$', r'\1 में क्या बदलाव हुए?'),
        (r'^What are the grounds for (.+)\?$', r'\1 के आधार क्या हैं?'),
        (r'^What are the ingredients to prove (.+)\?$', r'\1 सिद्ध करने के आवश्यक तत्व क्या हैं?'),
        (r'^What are the ingredients of (.+)\?$', r'\1 के आवश्यक तत्व क्या हैं?'),
        (r'^What are the new (.+)\?$', r'\1 के नए प्रावधान क्या हैं?'),
        (r'^What is the legal position on (.+)\?$', r'\1 पर कानूनी स्थिति क्या है?'),
        (r'^What must prosecution prove in (.+)\?$', r'\1 में अभियोजन को क्या साबित करना होता है?'),
        (r'^Landmark cases on (.+)$', r'\1 पर प्रमुख मामले कौन-से हैं?'),
        (r'^Supreme Court cases on (.+)$', r'\1 पर सुप्रीम कोर्ट के प्रमुख मामले कौन-से हैं?'),
        (r'^Cases on (.+)$', r'\1 पर प्रमुख मामले कौन-से हैं?'),
        (r'^Supreme Court on (.+)$', r'\1 पर सुप्रीम कोर्ट का दृष्टिकोण क्या है?'),
        (r'^Was (.+)\?$', r'क्या \1?'),
        (r'^Is (.+)\?$', r'क्या \1?'),
        (r'^What is (.+) called in (.+)\?$', r'\2 में \1 को क्या कहा जाता है?'),
    ]

    for ptn, rep in pats:
        if re.match(ptn, q):
            return re.sub(ptn, rep, q)

    if q.endswith('?'):
        q=q[:-1]
    return f"{q} के बारे में कानूनी जानकारी क्या है?"

term_map=[
    ('Section','धारा'),
    ('judgment','फैसला'),
    ('cases','मामले'),
    ('case','मामला'),
    ('investigation direction','जांच के निर्देश'),
    ('statement of accused','अभियुक्त का बयान'),
    ('electronic evidence','इलेक्ट्रॉनिक साक्ष्य'),
    ('common intention','समान आशय'),
    ('criminal breach of trust','आपराधिक न्यासभंग'),
    ('cheque bounce','चेक बाउंस'),
    ('anticipatory bail','अग्रिम जमानत'),
    ('economic offences','आर्थिक अपराध'),
    ('decriminalization','अपराधमुक्ति'),
    ('rape','बलात्कार'),
    ('dowry harassment','दहेज उत्पीड़न'),
    ('kidnapping','अपहरण'),
    ('murder trial','हत्या का मुकदमा'),
    ('quashing FIR','FIR रद्द करना'),
    ('bail provisions','जमानत प्रावधान'),
    ('good law','प्रभावी विधि'),
]

def postprocess(s):
    for a,b in term_map:
        s=s.replace(a,b)
    return s

df['hindi_query']=df['english_query'].map(lambda x: postprocess(translate(x)))
df.to_excel(p,index=False)
print('updated',p)
print(df[['english_query','hindi_query']].to_string(index=False))
