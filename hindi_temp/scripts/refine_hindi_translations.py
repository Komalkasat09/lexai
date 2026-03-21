import pandas as pd

p='evaluation/hindi_queries.xlsx'
df=pd.read_excel(p)

translations={
"What does Section 420 IPC say?":"IPC की धारा 420 में क्या कहा गया है?",
"What is the punishment for rape under BNS?":"BNS के तहत बलात्कार के लिए क्या सजा है?",
"Has Section 66A IT Act been struck down?":"क्या IT Act की धारा 66A को निरस्त किया जा चुका है?",
"Has IPC 302 been replaced?":"क्या IPC की धारा 302 को प्रतिस्थापित कर दिया गया है?",
"Landmark cases on cheque bounce Section 138":"धारा 138 (चेक बाउंस) पर प्रमुख न्यायिक फैसले कौन-से हैं?",
"Has the Section 377 judgment been challenged after decriminalization?":"क्या अपराधमुक्ति के बाद धारा 377 के फैसले को चुनौती दी गई है?",
"What are the grounds for quashing FIR under Section 482?":"धारा 482 के तहत FIR रद्द करने के आधार क्या हैं?",
"What is Section 498A IPC?":"IPC की धारा 498A क्या है?",
"What is the punishment for dowry harassment under Section 498A?":"धारा 498A के तहत दहेज उत्पीड़न के लिए क्या सजा है?",
"What are the new bail provisions under BNSS 2023?":"BNSS 2023 के तहत जमानत के नए प्रावधान क्या हैं?",
"What is IPC 376 called in BNS?":"BNS में IPC की धारा 376 को किस नाम/धारा से जाना जाता है?",
"Supreme Court cases on sedition Section 124A":"धारा 124A (राजद्रोह) पर सुप्रीम कोर्ट के प्रमुख मामले कौन-से हैं?",
"Is A.K. Gopalan v State of Madras still good law?":"क्या A.K. Gopalan बनाम State of Madras आज भी लागू विधि माना जाता है?",
"What is the doctrine of common intention under Section 34 IPC?":"IPC की धारा 34 के तहत common intention का सिद्धांत क्या है?",
"What does Section 354 IPC cover?":"IPC की धारा 354 में क्या प्रावधान है?",
"What is the sentence for criminal breach of trust under IPC 406?":"IPC की धारा 406 के तहत criminal breach of trust की सजा क्या है?",
"What happened to Section 377 IPC?":"IPC की धारा 377 के साथ क्या हुआ?",
"What is IPC 307 called in BNS?":"BNS में IPC की धारा 307 को क्या कहा जाता है?",
"Cases on adultery Section 497 IPC":"IPC की धारा 497 (व्यभिचार) पर प्रमुख मामले कौन-से हैं?",
"What happened to the judgment in Suresh Kumar Koushal case?":"Suresh Kumar Koushal मामले के फैसले का क्या हुआ?",
"What are the ingredients to prove cheating under IPC 420?":"IPC की धारा 420 के तहत cheating सिद्ध करने के आवश्यक तत्व क्या हैं?",
"Explain Section 506 IPC":"IPC की धारा 506 की व्याख्या करें।",
"How many years for kidnapping under IPC 363?":"IPC की धारा 363 के तहत अपहरण के लिए कितने वर्ष की सजा है?",
"What changed in CrPC after BNSS came into force?":"BNSS लागू होने के बाद CrPC में क्या बदलाव हुए?",
"What is the BNS section for criminal breach of trust?":"criminal breach of trust के लिए BNS की संबंधित धारा कौन-सी है?",
"Cases on Section 156(3) CrPC investigation direction":"CrPC की धारा 156(3) के तहत जांच के निर्देश पर प्रमुख मामले कौन-से हैं?",
"Has ADM Jabalpur v Shukla been overruled?":"क्या ADM Jabalpur बनाम Shukla को निरस्त कर दिया गया है?",
"What must prosecution prove in a murder trial?":"हत्या के मुकदमे में अभियोजन को क्या साबित करना होता है?",
"What is Section 323 IPC about?":"IPC की धारा 323 किस बारे में है?",
"How long imprisonment for robbery under IPC 392?":"IPC की धारा 392 के तहत robbery के लिए कितनी अवधि की सजा है?",
"Was adultery decriminalized in India?":"क्या भारत में व्यभिचार को अपराध की श्रेणी से बाहर कर दिया गया है?",
"What is IPC 120B called in BNS?":"BNS में IPC की धारा 120B को क्या कहा जाता है?",
"Cases on Section 313 CrPC statement of accused":"CrPC की धारा 313 में अभियुक्त के बयान पर प्रमुख मामले कौन-से हैं?",
"Is the Joseph Shine judgment on adultery still valid?":"क्या व्यभिचार पर Joseph Shine का फैसला अभी भी मान्य है?",
"What is the legal position on anticipatory bail for economic offences?":"आर्थिक अपराधों में अग्रिम जमानत की कानूनी स्थिति क्या है?",
"Explain Section 279 IPC":"IPC की धारा 279 की व्याख्या करें।",
"What is the sentence for causing grievous hurt under IPC 325?":"IPC की धारा 325 के तहत grievous hurt पहुंचाने की सजा क्या है?",
"Has the definition of rape been amended?":"क्या बलात्कार की परिभाषा में संशोधन किया गया है?",
"What is IPC 304B (dowry death) called in BNS?":"BNS में IPC की धारा 304B (dowry death) को क्या कहा जाता है?",
"Supreme Court on electronic evidence Section 65B":"धारा 65B के तहत electronic evidence पर सुप्रीम कोर्ट का दृष्टिकोण क्या है?",
}

df['hindi_query']=df['english_query'].map(lambda q: translations.get(q, f"{q} का हिंदी विधिक अनुवाद लंबित है।"))
df.to_excel(p,index=False)
print('updated',p)
print(df[['english_query','hindi_query']].head(8).to_string(index=False))
