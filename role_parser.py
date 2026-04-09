"""role_parser.py — Crawl job detail pages and extract ML/Research role requirements."""

import logging
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag

from config import HEADERS, REQUEST_DELAY_SEC, REQUEST_TIMEOUT_SEC
from db import get_connection, insert_requirements

logger = logging.getLogger(__name__)

# --- Skill / framework patterns (lowercase) ---
SKILL_PATTERNS: list[str] = [
    "pytorch", "tensorflow", "jax", "keras", "mxnet",
    "cuda", "triton", "tensorrt", "cudnn",
    "distributed training", "multi-gpu", "multi-node",
    "transformers", "llms", "large language models",
    "rlhf", "reinforcement learning from human feedback",
    "reinforcement learning", "diffusion models",
    "fine-tuning", "fine tuning", "pre-training", "pretraining",
    "inference optimization", "quantization", "distillation",
    "computer vision", "nlp", "natural language processing",
    "speech recognition", "multimodal",
    "kubernetes", "docker", "ray", "spark", "hadoop",
    "mlflow", "wandb", "weights & biases",
    "hugging face", "huggingface",
    "openai api", "langchain",
    "scikit-learn", "sklearn", "numpy", "pandas",
    "sql", "nosql", "mongodb", "redis",
    "aws", "gcp", "azure",
    "verilog", "fpga",
]

LANGUAGE_PATTERNS: list[str] = [
    "python", "c\\+\\+", "c/c\\+\\+", "rust", "go", "golang",
    "java", "scala", "julia", "r\\b", "matlab", "bash", "shell",
    "typescript", "javascript",
]

DEGREE_PATTERNS: dict[str, str] = {
    "phd": "PhD",
    "ph\\.d": "PhD",
    "doctorate": "PhD",
    "doctoral": "PhD",
    "master": "MS",
    "m\\.s": "MS",
    "m\\.sc": "MS",
    "msc": "MS",
    "bachelor": "BS",
    "b\\.s": "BS",
    "b\\.sc": "BS",
    "undergraduate": "BS",
    "b\\.e": "BS",
}

# Headings that typically introduce the requirements section
REQUIREMENTS_HEADINGS: list[str] = [
    "requirements",
    "qualifications",
    "what we.re looking for",
    "what you.ll need",
    "what you need",
    "you might be a good fit",
    "you should have",
    "minimum qualifications",
    "preferred qualifications",
    "basic qualifications",
    "who you are",
    "what we.re seeking",
    "required qualifications",
    "candidate profile",
    "about you",
]


def _extract_requirements_text(soup: BeautifulSoup) -> str:
    """Extract the requirements section text from a job page."""
    # Try to find a heading that matches requirements patterns, then grab sibling content
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
        text = tag.get_text(strip=True).lower()
        if any(re.search(pat, text) for pat in REQUIREMENTS_HEADINGS):
            # Collect following sibling text until next heading
            parts: list[str] = []
            for sib in tag.next_siblings:
                if isinstance(sib, Tag):
                    if sib.name in ("h1", "h2", "h3", "h4") and sib.get_text(strip=True):
                        break
                    parts.append(sib.get_text(" ", strip=True))
            section = " ".join(parts).strip()
            if len(section) > 50:
                return section

    # Fallback: return all body text
    body = soup.find("body")
    if body:
        return body.get_text(" ", strip=True)[:5000]
    return soup.get_text(" ", strip=True)[:5000]


def _parse_yoe(text: str) -> tuple[Optional[int], Optional[int]]:
    """Return (min_yoe, max_yoe) from text like '3+ years' or '5-8 years'."""
    text_lower = text.lower()

    # Pattern: "X-Y years"
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s+year", text_lower)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Pattern: "X+ years"
    m = re.search(r"(\d+)\+\s+year", text_lower)
    if m:
        return int(m.group(1)), None

    # Pattern: "at least X years" / "minimum X years"
    m = re.search(r"(?:at least|minimum of?|over)\s+(\d+)\s+year", text_lower)
    if m:
        return int(m.group(1)), None

    # Pattern: "X years of experience"
    m = re.search(r"(\d+)\s+year[s]?\s+of", text_lower)
    if m:
        return int(m.group(1)), None

    return None, None


def _parse_degree(text: str) -> Optional[str]:
    """Return highest degree level mentioned: PhD > MS > BS."""
    text_lower = text.lower()
    for pat, level in DEGREE_PATTERNS.items():
        if re.search(pat, text_lower):
            if level == "PhD":
                return "PhD"
    for pat, level in DEGREE_PATTERNS.items():
        if re.search(pat, text_lower):
            if level == "MS":
                return "MS"
    for pat, level in DEGREE_PATTERNS.items():
        if re.search(pat, text_lower):
            if level == "BS":
                return "BS"
    return None


def _parse_skills(text: str) -> list[str]:
    """Return list of matched skills/frameworks found in text."""
    text_lower = text.lower()
    found: list[str] = []
    for skill in SKILL_PATTERNS:
        if re.search(r"\b" + skill + r"\b", text_lower):
            # Normalize display name
            found.append(skill.replace("\\", ""))
    return list(dict.fromkeys(found))  # deduplicate preserving order


def _parse_languages(text: str) -> list[str]:
    """Return list of programming languages found in text."""
    text_lower = text.lower()
    found: list[str] = []
    display = {
        "python": "Python",
        "c\\+\\+": "C++",
        "c/c\\+\\+": "C/C++",
        "rust": "Rust",
        "go": "Go",
        "golang": "Go",
        "java": "Java",
        "scala": "Scala",
        "julia": "Julia",
        "r\\b": "R",
        "matlab": "MATLAB",
        "bash": "Bash",
        "shell": "Shell",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
    }
    for pat, name in display.items():
        if re.search(r"\b" + pat, text_lower) and name not in found:
            found.append(name)
    return found


def _parse_publications(text: str) -> bool:
    """Return True if the text mentions publication expectations."""
    text_lower = text.lower()
    pub_patterns = [
        r"\bpublication[s]?\b",
        r"\bpublish(ed|ing)?\b",
        r"\bpaper[s]?\b",
        r"\bconference[s]?\b",
        r"\bjournal[s]?\b",
        r"\bneurips\b", r"\bicml\b", r"\biclr\b", r"\baistats\b",
        r"\bacl\b", r"\bemnlp\b", r"\bnaacl\b",
        r"\bcvpr\b", r"\biccv\b", r"\beccv\b",
        r"\bsigkdd\b", r"\baaai\b",
        r"\bresearch contribution[s]?\b",
        r"\bpeer.reviewed\b",
    ]
    return any(re.search(p, text_lower) for p in pub_patterns)


def parse_role_requirements(
    url: str,
    session: Optional[requests.Session] = None,
    delay: float = REQUEST_DELAY_SEC,
) -> dict:
    """Fetch a job detail page and extract requirements.

    Returns a dict with keys:
        min_yoe, max_yoe, degree_level, skills, languages,
        publications_expected, description_raw
    """
    sess = session or requests.Session()
    result: dict = {
        "min_yoe": None,
        "max_yoe": None,
        "degree_level": None,
        "skills": [],
        "languages": [],
        "publications_expected": False,
        "description_raw": "",
    }

    try:
        time.sleep(delay)
        resp = sess.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    req_text = _extract_requirements_text(soup)

    result["description_raw"] = req_text[:4000]
    result["min_yoe"], result["max_yoe"] = _parse_yoe(req_text)
    result["degree_level"] = _parse_degree(req_text)
    result["skills"] = _parse_skills(req_text)
    result["languages"] = _parse_languages(req_text)
    result["publications_expected"] = _parse_publications(req_text)

    return result


def parse_and_save_role(
    role_id: int,
    url: str,
    session: Optional[requests.Session] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Parse requirements for a role URL and save to DB. Returns True on success."""
    reqs = parse_role_requirements(url, session=session)
    if not reqs["description_raw"]:
        logger.warning("No content extracted for role_id=%d url=%s", role_id, url)
        return False

    kwargs = {} if db_path is None else {"db_path": db_path}
    conn = get_connection(**kwargs)
    try:
        insert_requirements(
            conn,
            role_id=role_id,
            min_yoe=reqs["min_yoe"],
            max_yoe=reqs["max_yoe"],
            degree_level=reqs["degree_level"],
            skills=reqs["skills"],
            languages=reqs["languages"],
            publications_expected=reqs["publications_expected"],
            description_raw=reqs["description_raw"],
        )
    finally:
        conn.close()

    return True


def parse_all_roles(
    db_path: Optional[str] = None,
    limit: Optional[int] = None,
) -> None:
    """Parse requirements for all roles in the DB that don't have requirements yet."""
    kwargs = {} if db_path is None else {"db_path": db_path}
    conn = get_connection(**kwargs)

    query = """
        SELECT r.id, r.url, r.title, c.name AS company
        FROM roles r
        JOIN companies c ON c.id = r.company_id
        LEFT JOIN requirements req ON req.role_id = r.id
        WHERE req.id IS NULL AND r.url IS NOT NULL
        ORDER BY r.id
    """
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    conn.close()

    logger.info("Parsing requirements for %d roles", len(rows))
    sess = requests.Session()
    success = 0

    for row in rows:
        role_id = row["id"]
        url = row["url"]
        company = row["company"]
        title = row["title"]
        logger.info("  [%s] %s → %s", company, title, url)

        ok = parse_and_save_role(role_id, url, session=sess, db_path=db_path)
        if ok:
            success += 1

    logger.info("Done: %d/%d roles parsed successfully", success, len(rows))


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    parse_all_roles(limit=limit_arg)
    print("Done.")
