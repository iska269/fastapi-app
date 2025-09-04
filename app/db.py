from psycopg_pool import AsyncConnectionPool
from psycopg.types.json import Json
from dotenv import load_dotenv
import json
import os



load_dotenv()

url = os.getenv("DATA_BASE_URL")

pool =AsyncConnectionPool(url, open=False)

#create table administrator with psycopg_pool

async def create_table():
    async with pool.connection() as conn:
        async with conn.transaction() :
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS administrator(
                        id SERIAL PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        hashed_password VARCHAR(250),
                        is_super_admin BOOLEAN
                                )
                """)

async def add_new_administrator(email,name,hashed_password,is_super_admin):
    async with pool.connection() as conn:
        async with conn.transaction() :
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO administrator(email,name,hashed_password,is_super_admin) VALUES(%s,%s,%s,%s) RETURNING id
                """,(email,name,hashed_password,is_super_admin))
                id = await cur.fetchone()
                return id[0]


async def login_administrator(email):
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT * FROM administrator WHERE email = %s
                    """,(email,))
                
                return await cur.fetchall()


async def save_json_file(content):
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM pg_tables
                        WHERE schemaname = 'public'
                        AND tablename  = 'contenent'
                    )
                """)
                exists = (await cur.fetchone())[0]
                if not exists:
                    await cur.execute("""
                        CREATE TABLE contenent(
                            id SERIAL PRIMARY KEY,
                            content JSONB
                                )
                        """)
                    await cur.execute("""
                        INSERT INTO contenent(content) VALUES(%s)
                    """,(Json(content),))
                    
                    

async def call_content():
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT content FROM contenent
                """)
                row = await cur.fetchone()
                return row[0] if row else None


async def update_content(content):
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("""
                    UPDATE contenent SET content = %s WHERE id = (SELECT id FROM contenent ORDER BY id DESC LIMIT 1)
                """,(Json(content),))

async def call_administrator():
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id,name,email FROM administrator WHERE is_super_admin = %s
                """,(False,))
                admin = await cur.fetchall()
                await cur.execute("""
                    SELECT id,name,email FROM administrator WHERE is_super_admin = %s
                """,(True,))
                super_admin = await cur.fetchall()
                table_administator = [{"admin": admin if admin else False},{"super_admin":super_admin if super_admin else False}]
                return table_administator
            
async def delete_admin(id):
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("""
                    DELETE FROM administrator WHERE id = %s
                """,(id,))

async def verify_email(email):
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
               await cur.execute("""
                    SELECT * FROM administrator WHERE email = %s
                """,(email,))
               res = await cur.fetchall()
               if res:
                   return True
               else:
                   return False