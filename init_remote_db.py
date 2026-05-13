import asyncio
import asyncpg
import os

async def run_init_sql():
    # Connection details
    db_url = "postgresql://kgh:kgh_admin_secure123!@192.168.101.226:5435/kgh_metads"
    sql_file = "backend/sql/init.sql"
    
    try:
        # Read the SQL file
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_queries = f.read()
            
        print("Connecting to database...")
        conn = await asyncpg.connect(db_url)
        
        print("Executing init.sql...")
        await conn.execute(sql_queries)
        
        print("Successfully executed init.sql!")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_init_sql())
