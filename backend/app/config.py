from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BASE_DIR / "medieval_ai.sqlite3"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_RECORDS = 10_000
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
IDENTIFIER_HINTS = (
    "patient", "name", "email", "phone", "mrn", "ssn", "address", "identifier",
    "birth", "dob", "zip_code",
)
