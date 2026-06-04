import pydantic
import os

from dotenv import load_dotenv
from pathlib import Path

# load environmental variable
load_dotenv()  # load env_var for local dev environment, do nothing for prod env

class Settings(pydantic.BaseModel):
    RAPID_API_KEY: str
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    STORE_LOGOS_FOLDER_PATH: Path
    LOGS_FOLDER_PATH: Path
    MONGO_DB_CONNECTION_STRING: str
    MONGO_DB_NAME: str
    ALLOWED_CORS_ORIGINS: list[str]
    SUPABASE_API_KEY: str
    SUPABASE_PROJECT_URL: str
    SUPABASE_STORAGE_BUCKET_NAME: str
    SUPABASE_STORAGE_BUCKET_LOGO_PATH: str
    ENV: str
rapid_api_key = os.getenv("RAPIDAPI_KEY", "")
if not rapid_api_key:
    raise ValueError("Rapid API Key is missing! Please check if key is set in .env or environmental variables of platform settings.")

gemini_api_key = os.getenv("GOOGLE_CLOUD_AI_API_KEY")
if not gemini_api_key:
    raise ValueError("Google Cloud AI API key is missing! Please set GOOGLE_CLOUD_AI_API_KEY in .env or environment variables.")

gemini_model = os.getenv("GEMINI_MODEL", "")
if not gemini_model:
    raise ValueError("Gemini model is missing! Please set GEMINI_MODEL in .env or environment variables.")

mongo_connection_string = os.getenv("MONGO_DB_CONNECTION_STRING", "")
if not mongo_connection_string:
    raise ValueError("Mongo DB connection string is missing! Please set MONGO_DB_CONNECTION_STRING in .env or environment variables.")

mongo_db_name = os.getenv("MONGO_DB_NAME", "")
if not mongo_db_name:
    raise ValueError("Mongo database name is missing! Please set MONGO_DB_NAME in .env or environment variables.")

allowed_cors_origins = os.getenv("ALLOWED_CORS_ORIGINS", "")
allowed_cors_origins_list = []
if not allowed_cors_origins:
    raise ValueError("Allowed CORS Origins list is missing! Please set ALLOWED_CORS_ORIGINS in .env or environment variables.")
else:
    allowed_cors_origins_list = allowed_cors_origins.split(",")

supabase_api_key = os.getenv("SUPABASE_ANON_API_KEY", "")
if not supabase_api_key:
    raise ValueError("Supabase api key is missing! Please set SUPABASE_ANON_API_KEY in .env or environment variables.")

supabase_project_url = os.getenv("SUPABASE_PROJECT_URL", "")
if not supabase_project_url:
    raise ValueError("Supabase project url is missing! Please set SUPABASE_PROJECT_URL in .env or environment variables.")

supabase_storage_bucket_name = os.getenv("SUPABASE_STORAGE_BUCKET_NAME", "")
if not supabase_storage_bucket_name:
    raise ValueError("Supabase storage bucket name is missing! Please set SUPABASE_STORAGE_BUCKET_NAME in .env or environment variables.")

supabase_storage_bucket_logo_path = os.getenv("SUPABASE_STORAGE_BUCKET_LOGO_PATH", "")
if not supabase_storage_bucket_logo_path:
    raise ValueError("Supabase storage bucket logo path is missing! Please set SUPABASE_STORAGE_BUCKET_LOGO_PATH in .env or environment variables.")

env = os.getenv("ENV", "dev").strip().strip('"').lower()

project_root = Path(__file__).resolve().parent.parent
store_logos_folder_path = project_root / "store_logos"
logs_folder_path = project_root / "logs"

store_logos_folder_path.mkdir(parents=True, exist_ok=True)
logs_folder_path.mkdir(parents=True, exist_ok=True)

settings = Settings(
    RAPID_API_KEY=rapid_api_key,
    GEMINI_API_KEY=gemini_api_key,
    GEMINI_MODEL=gemini_model,
    MONGO_DB_CONNECTION_STRING=mongo_connection_string,
    MONGO_DB_NAME=mongo_db_name,
    STORE_LOGOS_FOLDER_PATH=store_logos_folder_path,
    LOGS_FOLDER_PATH=logs_folder_path,
    ALLOWED_CORS_ORIGINS=allowed_cors_origins_list,
    SUPABASE_API_KEY=supabase_api_key,
    SUPABASE_PROJECT_URL=supabase_project_url,
    SUPABASE_STORAGE_BUCKET_NAME=supabase_storage_bucket_name,
    SUPABASE_STORAGE_BUCKET_LOGO_PATH=supabase_storage_bucket_logo_path,
    ENV=env,
)