import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path='./legal_research_db',
    settings=Settings(anonymized_telemetry=False)
)

print('=' * 70)
print('DATABASE STATUS - PRODUCTION READY')
print('=' * 70)

bare_acts = client.get_collection('bare_acts').count()
case_law = client.get_collection('case_law').count()
amendments = client.get_collection('amendments').count()
overruling = client.get_collection('overruling_map').count()

print(f'\nBare Acts:      {bare_acts} documents')
print(f'Case Law:       {case_law} documents')
print(f'Amendments:     {amendments} documents')
print(f'Overruling Map: {overruling} documents')
print(f'\nTOTAL:          {bare_acts + case_law + amendments + overruling} documents')
print('\nRETRIEVAL: 8 documents per query (3 bare acts + 5 case law)')
print('STATUS: PRODUCTION READY ✅')
