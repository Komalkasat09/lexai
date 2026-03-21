import re
import pandas as pd

p='evaluation/hindi_queries.xlsx'
df=pd.read_excel(p)

def translate(q):
    q=str(q).strip()

    m=re.match(r'^What does (Section\s+[0-9A-Za-z()/.]+\s*(?:IPC|BNS|CrPC|BNSS)?) say\?$', q)
    if m:
        return f"{m.group(1)} में क्या कहा गया है?"

    m=re.match(r'^Explain (Section\s+[0-9A-Za-z()/.]+\s*(?:IPC|BNS|CrPC|BNSS)?)$', q)
    if m:
        return f"{m.group(1)} की व्याख्या करें।"

    m=re.match(r'^What is (Section\s+[0-9A-Za-z()/.]+\s*(?:IPC|BNS|CrPC|BNSS)?)\?$', q)
    if m:
        return f"{m.group(1)} क्या है?"

    m=re.match(r'^What is the punishment for (.+) under (IPC|BNS|CrPC|BNSS)\?$', q)
    if m:
        return f"{m.group(2)} के तहत {m.group(1)} के लिए क्या सजा है?"

    m=re.match(r'^What is the sentence for (.+) under (IPC|BNS|CrPC|BNSS)\s*([0-9A-Za-z()/.]+)\?$', q)
    if m:
        return f"{m.group(2)} की धारा {m.group(3)} के तहत {m.group(1)} की सजा क्या है?"

    m=re.match(r'^How many years for (.+) under (IPC|BNS|CrPC|BNSS)\s*([0-9A-Za-z()/.]+)\?$', q)
    if m:
        return f"{m.group(2)} की धारा {m.group(3)} के तहत {m.group(1)} के लिए कितने वर्ष की सजा है?"

    m=re.match(r'^How long imprisonment for (.+) under (IPC|BNS|CrPC|BNSS)\s*([0-9A-Za-z()/.]+)\?$', q)
    if m:
        return f"{m.group(2)} की धारा {m.group(3)} के तहत {m.group(1)} के लिए कितनी अवधि की सजा है?"

    m=re.match(r'^Has (.+) been overruled\?$', q)
    if m:
        return f"क्या {m.group(1)} को निरस्त किया जा चुका है?"

    m=re.match(r'^Has (.+) been challenged\?$', q)
    if m:
        return f"क्या {m.group(1)} को चुनौती दी गई है?"

    m=re.match(r'^What happened to (.+)\?$', q)
    if m:
        return f"{m.group(1)} का क्या हुआ?"

    m=re.match(r'^What changed in (.+)\?$', q)
    if m:
        return f"{m.group(1)} में क्या बदलाव हुए?"

    m=re.match(r'^What are the grounds for (.+)\?$', q)
    if m:
        return f"{m.group(1)} के आधार क्या हैं?"

    m=re.match(r'^What are the ingredients to prove (.+)\?$', q)
    if m:
        return f"{m.group(1)} सिद्ध करने के आवश्यक तत्व क्या हैं?"

    m=re.match(r'^What are the ingredients of (.+)\?$', q)
    if m:
        return f"{m.group(1)} के आवश्यक तत्व क्या हैं?"

    m=re.match(r'^What are the new (.+)\?$', q)
    if m:
        return f"{m.group(1)} के नए प्रावधान क्या हैं?"

    m=re.match(r'^What is the legal position on (.+)\?$', q)
    if m:
        return f"{m.group(1)} पर कानूनी स्थिति क्या है?"

    m=re.match(r'^What must prosecution prove in (.+)\?$', q)
    if m:
        return f"{m.group(1)} में अभियोजन को क्या साबित करना होता है?"

    m=re.match(r'^Landmark cases on (.+)$', q)
    if m:
        return f"{m.group(1)} पर प्रमुख मामले कौन-से हैं?"

    m=re.match(r'^Supreme Court cases on (.+)$', q)
    if m:
        return f"{m.group(1)} पर सुप्रीम कोर्ट के प्रमुख मामले कौन-से हैं?"

    m=re.match(r'^Cases on (.+)$', q)
    if m:
        return f"{m.group(1)} पर प्रमुख मामले कौन-से हैं?"

    m=re.match(r'^Supreme Court on (.+)$', q)
    if m:
        return f"{m.group(1)} पर सुप्रीम कोर्ट का दृष्टिकोण क्या है?"

    m=re.match(r'^Was (.+)\?$', q)
    if m:
        return f"क्या {m.group(1)}?"

    m=re.match(r'^Is (.+)\?$', q)
    if m:
        return f"क्या {m.group(1)}?"

    m=re.match(r'^What is (.+) called in (.+)\?$', q)
    if m:
        return f"{m.group(2)} में {m.group(1)} को क्या कहा जाता है?"

    if q.endswith('?'):
        q=q[:-1]
    return f"{q} के बारे में कानूनी जानकारी क्या है?"

# light terminology localization
term_map=[
    ('Section','धारा'),
    ('judgment','फैसला'),
    ('cases','मामले'),
    ('case','मामला'),
    ('investigation','जांच'),
    ('statement of accused','अभियुक्त का बयान'),
    ('electronic evidence','इलेक्ट्रॉनिक साक्ष्य'),
    ('common intention','समान आशय'),
    ('criminal breach of trust','आपराधिक न्यासभंग'),
    ('cheque bounce','चेक बाउंस'),
    ('anticipatory bail','अग्रिम जमानत'),
    ('economic offences','आर्थिक अपराध'),
    ('decriminalization','अपराधमुक्ति'),
]

def postprocess(s):
    for a,b in term_map:
        s=s.replace(a,b)
    return s

df['hindi_query']=df['english_query'].map(lambda x: postprocess(translate(x)))
df.to_excel(p,index=False)
print('updated',p)
print(df[['english_query','hindi_query']].head(10).to_string(index=False))
