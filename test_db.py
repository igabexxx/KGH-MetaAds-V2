from sqlalchemy import create_engine
import json
import pandas as pd
engine = create_engine('postgresql://kgh_admin:kgh_admin_secure123!@192.168.101.226:5433/kgh_metads')
df = pd.read_sql("SELECT id, full_name, phone, custom_fields FROM leads WHERE phone = '6285210637325' LIMIT 1", engine)
for _, row in df.iterrows():
    print('ID:', row['id'])
    print('Name:', row['full_name'])
    print('Phone:', row['phone'])
    print('CF keys:', list(row['custom_fields'].keys()) if row['custom_fields'] else None)
