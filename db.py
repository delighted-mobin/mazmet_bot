import supabase
import os
from supabase import AsyncClient, acreate_client

db : AsyncClient = None

async def connect_db():
    try:
        global db
        db = await acreate_client(
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_KEY")
        )
        return db
    except Exception as e:
        return e

async def fetch(table_name:str = "users"):
    try:
        response = await db.table(table_name).select("*").execute()
        return response.data
    except Exception as e:
        return e

async def select(table_name:str = "users", eq:str = "id", eq_value:str = "0"):
    try:
        response = await db.table(table_name).select("*").eq(eq, eq_value).execute()
        return response.data
    except:
        return -1

async def insert(table_name:str = "users", data:dict = {}):
    try:
        response = await db.table(table_name).insert(data).execute()
        return response.data
    except:
        return -1

async def update(table_name:str = "users", eq:str = "id", eq_value:str = "0", data:dict = {}):
    try:
        response = await db.table(table_name).update(data).eq(eq, eq_value).execute()
        return response.data
    except:
        return -1

async def upsert(table_name:str = "users", data:dict = {}):
    try:
        response = await db.table(table_name).upsert(data).execute()
        return response.data
    except:
        return -1

async def exist(table_name:str = "users", eq:str = "id", eq_value:int = 0):
    try:
        response = await db.table(table_name).select("*").eq(eq, eq_value).execute()
        return True if response.data != [] else False
    except:
        return -1

async def set_status(table_name:str = "users", eq:str = "id", eq_value:int = 0, status:str = "main"):
    try:
        response = await db.table(table_name).update({"status": status}).eq(eq, eq_value).execute()
        return response.data
    except:
        return -1

async def get_status(table_name:str = "users", eq:str = "id", eq_value:int = 0, status:str = "main"):
    try:
        response = await db.table(table_name).select("status").eq(eq, eq_value).execute()
        return response.data
    except:
        return -1
