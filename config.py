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

# --- Iteration 2: Talent Flow ---

GOOGLE_API_KEY: str = ""  # Set via env var GOOGLE_API_KEY
GOOGLE_CX: str = ""       # Set via env var GOOGLE_CX (Custom Search Engine ID)

SOURCE_LABS: list[dict[str, str | list[str]]] = [
    {"name": "OpenAI", "queries": ["OpenAI"]},
    {"name": "Anthropic", "queries": ["Anthropic"]},
    {"name": "Google DeepMind", "queries": ["Google DeepMind", "DeepMind"]},
    {"name": "Meta FAIR", "queries": ["Meta FAIR", "Facebook AI Research"]},
    {"name": "xAI", "queries": ["xAI"]},
    {"name": "Mistral", "queries": ["Mistral AI", "Mistral"]},
    {"name": "Cohere", "queries": ["Cohere"]},
    {"name": "AI21 Labs", "queries": ["AI21 Labs", "AI21"]},
    {"name": "Inflection AI", "queries": ["Inflection AI", "Inflection"]},
    {"name": "Stability AI", "queries": ["Stability AI"]},
    {"name": "Character.ai", "queries": ["Character.ai", "Character AI"]},
    {"name": "Adept", "queries": ["Adept AI", "Adept"]},
    {"name": "Amazon AGI", "queries": ["Amazon AGI", "AWS AI"]},
    {"name": "Apple ML", "queries": ["Apple Machine Learning", "Apple ML"]},
    {"name": "Microsoft Research AI", "queries": ["Microsoft Research", "MSR AI"]},
    {"name": "NVIDIA Research", "queries": ["NVIDIA Research", "NVIDIA AI"]},
    {"name": "Baidu AI", "queries": ["Baidu Research", "Baidu AI"]},
    {"name": "ByteDance AI", "queries": ["ByteDance AI", "TikTok AI"]},
    {"name": "Samsung AI", "queries": ["Samsung AI", "Samsung Research"]},
    {"name": "Alibaba DAMO", "queries": ["Alibaba DAMO", "DAMO Academy"]},
]

SEARCH_QUERY_TEMPLATES: list[str] = [
    'site:linkedin.com/in "ex-{query}"',
    'site:linkedin.com/in "formerly at {query}"',
    'site:linkedin.com/in "{query}" "former"',
    'site:linkedin.com/in "previously at {query}"',
]

SEARCH_RATE_LIMIT_DELAY: float = 1.5
SEARCH_MAX_RESULTS_PER_QUERY: int = 10
