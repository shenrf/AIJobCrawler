"""
companies.py — Curated list of AI companies with metadata.

Each entry is a dict with:
  name, url, careers_url, category, founded, hq_location,
  funding_stage, known_products
"""

from typing import TypedDict


class Company(TypedDict):
    name: str
    url: str
    careers_url: str
    category: str          # foundation-model | ai-infra | ai-app | ai-safety | ai-chip
    founded: int
    hq_location: str
    funding_stage: str     # public | private | acquired | subsidiary
    known_products: list[str]


COMPANIES: list[Company] = [
    # ── Foundation-model labs ──────────────────────────────────────────────
    {
        "name": "OpenAI",
        "url": "https://openai.com",
        "careers_url": "https://openai.com/careers",
        "category": "foundation-model",
        "founded": 2015,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["GPT-4", "ChatGPT", "DALL-E", "Sora", "Whisper", "o1"],
    },
    {
        "name": "Anthropic",
        "url": "https://anthropic.com",
        "careers_url": "https://www.anthropic.com/careers",
        "category": "foundation-model",
        "founded": 2021,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Claude", "Claude 3", "Constitutional AI"],
    },
    {
        "name": "Google DeepMind",
        "url": "https://deepmind.google",
        "careers_url": "https://deepmind.google/careers/",
        "category": "foundation-model",
        "founded": 2010,
        "hq_location": "London, UK",
        "funding_stage": "subsidiary",
        "known_products": ["Gemini", "AlphaFold", "AlphaCode", "Gemma"],
    },
    {
        "name": "Meta FAIR",
        "url": "https://ai.meta.com",
        "careers_url": "https://www.metacareers.com/areas-of-work/artificial-intelligence/",
        "category": "foundation-model",
        "founded": 2013,
        "hq_location": "Menlo Park, CA",
        "funding_stage": "public",
        "known_products": ["LLaMA", "PyTorch", "Segment Anything", "ImageBind"],
    },
    {
        "name": "xAI",
        "url": "https://x.ai",
        "careers_url": "https://x.ai/careers",
        "category": "foundation-model",
        "founded": 2023,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Grok"],
    },
    {
        "name": "Mistral AI",
        "url": "https://mistral.ai",
        "careers_url": "https://jobs.mistral.ai/",
        "category": "foundation-model",
        "founded": 2023,
        "hq_location": "Paris, France",
        "funding_stage": "private",
        "known_products": ["Mistral 7B", "Mixtral", "Le Chat"],
    },
    {
        "name": "Cohere",
        "url": "https://cohere.com",
        "careers_url": "https://cohere.com/careers",
        "category": "foundation-model",
        "founded": 2019,
        "hq_location": "Toronto, Canada",
        "funding_stage": "private",
        "known_products": ["Command R", "Embed", "Rerank", "Aya"],
    },
    {
        "name": "AI21 Labs",
        "url": "https://www.ai21.com",
        "careers_url": "https://www.ai21.com/careers",
        "category": "foundation-model",
        "founded": 2017,
        "hq_location": "Tel Aviv, Israel",
        "funding_stage": "private",
        "known_products": ["Jurassic", "Jamba", "Wordtune"],
    },
    {
        "name": "Inflection AI",
        "url": "https://inflection.ai",
        "careers_url": "https://inflection.ai/careers",
        "category": "foundation-model",
        "founded": 2022,
        "hq_location": "Palo Alto, CA",
        "funding_stage": "private",
        "known_products": ["Pi", "Inflection-2"],
    },
    {
        "name": "Adept AI",
        "url": "https://www.adept.ai",
        "careers_url": "https://www.adept.ai/careers",
        "category": "foundation-model",
        "founded": 2022,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["ACT-1", "Fuyu"],
    },
    # ── AI Safety ─────────────────────────────────────────────────────────
    {
        "name": "Redwood Research",
        "url": "https://www.redwoodresearch.org",
        "careers_url": "https://www.redwoodresearch.org/careers",
        "category": "ai-safety",
        "founded": 2021,
        "hq_location": "Berkeley, CA",
        "funding_stage": "private",
        "known_products": ["RLHF research", "Causal scrubbing"],
    },
    {
        "name": "ARC (Alignment Research Center)",
        "url": "https://www.alignment.org",
        "careers_url": "https://www.alignment.org/careers/",
        "category": "ai-safety",
        "founded": 2021,
        "hq_location": "Berkeley, CA",
        "funding_stage": "private",
        "known_products": ["Evals", "ARC Evals"],
    },
    # ── AI Applications ───────────────────────────────────────────────────
    {
        "name": "Character.ai",
        "url": "https://character.ai",
        "careers_url": "https://character.ai/careers",
        "category": "ai-app",
        "founded": 2021,
        "hq_location": "Menlo Park, CA",
        "funding_stage": "private",
        "known_products": ["Character.AI chatbots"],
    },
    {
        "name": "Stability AI",
        "url": "https://stability.ai",
        "careers_url": "https://stability.ai/careers",
        "category": "ai-app",
        "founded": 2020,
        "hq_location": "London, UK",
        "funding_stage": "private",
        "known_products": ["Stable Diffusion", "SDXL", "Stable Audio"],
    },
    {
        "name": "Midjourney",
        "url": "https://www.midjourney.com",
        "careers_url": "https://www.midjourney.com/jobs",
        "category": "ai-app",
        "founded": 2021,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Midjourney image generation"],
    },
    {
        "name": "Runway",
        "url": "https://runwayml.com",
        "careers_url": "https://runwayml.com/careers/",
        "category": "ai-app",
        "founded": 2018,
        "hq_location": "New York, NY",
        "funding_stage": "private",
        "known_products": ["Gen-2", "Gen-3", "Runway video AI"],
    },
    {
        "name": "Perplexity AI",
        "url": "https://www.perplexity.ai",
        "careers_url": "https://www.perplexity.ai/hub/careers",
        "category": "ai-app",
        "founded": 2022,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Perplexity search", "Perplexity Pro"],
    },
    {
        "name": "Cursor",
        "url": "https://cursor.sh",
        "careers_url": "https://cursor.sh/careers",
        "category": "ai-app",
        "founded": 2022,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Cursor IDE", "AI code editor"],
    },
    # ── AI Infrastructure ─────────────────────────────────────────────────
    {
        "name": "Hugging Face",
        "url": "https://huggingface.co",
        "careers_url": "https://apply.workable.com/huggingface/",
        "category": "ai-infra",
        "founded": 2016,
        "hq_location": "New York, NY",
        "funding_stage": "private",
        "known_products": ["Transformers library", "Hub", "Diffusers", "PEFT"],
    },
    {
        "name": "Databricks",
        "url": "https://www.databricks.com",
        "careers_url": "https://www.databricks.com/company/careers",
        "category": "ai-infra",
        "founded": 2013,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Lakehouse", "DBRX", "MLflow", "Delta Lake"],
    },
    {
        "name": "Scale AI",
        "url": "https://scale.com",
        "careers_url": "https://scale.com/careers",
        "category": "ai-infra",
        "founded": 2016,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Scale Data Engine", "RLHF platform", "Spellbook"],
    },
    {
        "name": "Anyscale",
        "url": "https://www.anyscale.com",
        "careers_url": "https://www.anyscale.com/careers",
        "category": "ai-infra",
        "founded": 2019,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Ray", "Anyscale Platform"],
    },
    {
        "name": "Modal",
        "url": "https://modal.com",
        "careers_url": "https://modal.com/careers",
        "category": "ai-infra",
        "founded": 2021,
        "hq_location": "New York, NY",
        "funding_stage": "private",
        "known_products": ["Modal serverless compute"],
    },
    {
        "name": "Replicate",
        "url": "https://replicate.com",
        "careers_url": "https://replicate.com/careers",
        "category": "ai-infra",
        "founded": 2019,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Replicate model hosting", "Cog"],
    },
    {
        "name": "Together AI",
        "url": "https://www.together.ai",
        "careers_url": "https://www.together.ai/careers",
        "category": "ai-infra",
        "founded": 2022,
        "hq_location": "San Francisco, CA",
        "funding_stage": "private",
        "known_products": ["Together Inference", "FlashAttention-3", "RedPajama"],
    },
    # ── AI Chips ──────────────────────────────────────────────────────────
    {
        "name": "Cerebras Systems",
        "url": "https://www.cerebras.net",
        "careers_url": "https://www.cerebras.net/careers/",
        "category": "ai-chip",
        "founded": 2016,
        "hq_location": "Sunnyvale, CA",
        "funding_stage": "private",
        "known_products": ["Wafer Scale Engine", "CS-3", "Cerebras Cloud"],
    },
    {
        "name": "Groq",
        "url": "https://groq.com",
        "careers_url": "https://groq.com/careers/",
        "category": "ai-chip",
        "founded": 2016,
        "hq_location": "Mountain View, CA",
        "funding_stage": "private",
        "known_products": ["LPU", "GroqCloud"],
    },
    {
        "name": "SambaNova Systems",
        "url": "https://sambanova.ai",
        "careers_url": "https://sambanova.ai/careers/",
        "category": "ai-chip",
        "founded": 2017,
        "hq_location": "Palo Alto, CA",
        "funding_stage": "private",
        "known_products": ["SN40L chip", "SambaNova Cloud", "Samba-1"],
    },
    {
        "name": "NVIDIA AI",
        "url": "https://www.nvidia.com/en-us/ai/",
        "careers_url": "https://www.nvidia.com/en-us/about-nvidia/careers/",
        "category": "ai-chip",
        "founded": 1993,
        "hq_location": "Santa Clara, CA",
        "funding_stage": "public",
        "known_products": ["H100", "A100", "CUDA", "TensorRT", "NIM", "Megatron-LM"],
    },
    {
        "name": "AMD AI",
        "url": "https://www.amd.com/en/solutions/ai.html",
        "careers_url": "https://careers.amd.com/careers-home",
        "category": "ai-chip",
        "founded": 1969,
        "hq_location": "Santa Clara, CA",
        "funding_stage": "public",
        "known_products": ["MI300X", "ROCm", "Instinct GPUs"],
    },
    # ── Big Tech AI divisions ─────────────────────────────────────────────
    {
        "name": "Apple ML Research",
        "url": "https://machinelearning.apple.com",
        "careers_url": "https://jobs.apple.com/en-us/search?team=machine-learning-and-ai-MLAI",
        "category": "foundation-model",
        "founded": 1976,
        "hq_location": "Cupertino, CA",
        "funding_stage": "public",
        "known_products": ["Core ML", "Create ML", "Apple Intelligence", "MLX"],
    },
    {
        "name": "Amazon AI",
        "url": "https://aws.amazon.com/ai/",
        "careers_url": "https://www.amazon.jobs/en/teams/aws-ai",
        "category": "foundation-model",
        "founded": 1994,
        "hq_location": "Seattle, WA",
        "funding_stage": "public",
        "known_products": ["Bedrock", "Titan", "SageMaker", "Trainium", "Inferentia"],
    },
    {
        "name": "Microsoft AI",
        "url": "https://www.microsoft.com/en-us/ai",
        "careers_url": "https://careers.microsoft.com/us/en/search-results?keywords=machine+learning",
        "category": "foundation-model",
        "founded": 1975,
        "hq_location": "Redmond, WA",
        "funding_stage": "public",
        "known_products": ["Copilot", "Azure OpenAI", "Phi", "Orca"],
    },
]


def get_companies_by_category(category: str) -> list[Company]:
    """Return all companies matching the given category."""
    return [c for c in COMPANIES if c["category"] == category]


def get_company_by_name(name: str) -> Company | None:
    """Return company dict by exact name match, or None."""
    name_lower = name.lower()
    for c in COMPANIES:
        if c["name"].lower() == name_lower:
            return c
    return None


if __name__ == "__main__":
    print(f"Total companies: {len(COMPANIES)}")
    from collections import Counter
    cats = Counter(c["category"] for c in COMPANIES)
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")
