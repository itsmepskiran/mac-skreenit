# Marks 'backend' as a Python package for imports like 'backend.main'
from dotenv import load_dotenv

# Load environment variables from .env file in root
# This runs on import before any modules that need env vars
load_dotenv()
