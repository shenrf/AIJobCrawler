"""Configuration constants for AIJobCrawler."""

# --- Crawling ---
REQUEST_DELAY_SEC: float = 1.0
REQUEST_TIMEOUT_SEC: int = 15
MAX_RETRIES: int = 3

HEADERS: dict[str, str] = {
    "User-Agent": "AIJobCrawler/0.1 (bot; research project)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# --- Database ---
DB_PATH: str = "data/jobs.db"
DATA_DIR: str = "data"
OUTPUT_DIR: str = "output"

# --- ML/Research Role Keywords (lowercase) ---
ML_ROLE_KEYWORDS: list[str] = [
    "machine learning",
    "ml engineer",
    "ml scientist",
    "ml infrastructure",
    "applied ml",
    "research engineer",
    "research scientist",
    "applied scientist",
]

# --- Company Categories ---
COMPANY_CATEGORIES: list[str] = [
    "foundation-model",
    "ai-infra",
    "ai-app",
    "ai-safety",
    "ai-chip",
]
