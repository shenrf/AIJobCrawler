"""Seed list of well-known AI companies.

A curated baseline of notable AI companies that no single directory captures.
This isn't the "hardcoded list" problem — it's a floor, not a ceiling. The
dynamic discoverers (YC, GitHub, Crunchbase, etc.) add everything else.
"""
from __future__ import annotations

from typing import Optional

from .base import CompanyDiscoverer, CompanyRecord

_SEED_COMPANIES = [
    # Foundation model labs
    ("OpenAI", "https://openai.com", "https://openai.com/careers", "foundation-model", "San Francisco, CA", "$13.3B"),
    ("Anthropic", "https://anthropic.com", "https://www.anthropic.com/careers", "foundation-model", "San Francisco, CA", "$7.6B"),
    ("Google DeepMind", "https://deepmind.google", "https://deepmind.google/about/careers/", "foundation-model", "London, UK", ""),
    ("Meta AI", "https://ai.meta.com", "https://ai.meta.com/jobs/", "foundation-model", "Menlo Park, CA", ""),
    ("Mistral AI", "https://mistral.ai", "https://mistral.ai/careers/", "foundation-model", "Paris, France", "$645M"),
    ("Cohere", "https://cohere.com", "https://cohere.com/careers", "foundation-model", "Toronto, Canada", "$970M"),
    ("AI21 Labs", "https://www.ai21.com", "https://www.ai21.com/careers", "foundation-model", "Tel Aviv, Israel", "$336M"),
    ("Inflection AI", "https://inflection.ai", "https://inflection.ai/careers", "foundation-model", "Palo Alto, CA", "$1.5B"),
    ("xAI", "https://x.ai", "https://x.ai/careers", "foundation-model", "Austin, TX", "$6B"),
    ("Together AI", "https://www.together.ai", "https://www.together.ai/careers", "foundation-model", "San Francisco, CA", "$225M"),
    ("Aleph Alpha", "https://aleph-alpha.com", "https://aleph-alpha.com/careers", "foundation-model", "Heidelberg, Germany", "$500M"),
    ("Zhipu AI", "https://zhipuai.cn", "", "foundation-model", "Beijing, China", "$341M"),
    ("Moonshot AI (Kimi)", "https://www.moonshot.cn", "", "foundation-model", "Beijing, China", "$1B"),
    ("01.AI (Yi)", "https://www.01.ai", "", "foundation-model", "Beijing, China", "$200M"),
    ("Sakana AI", "https://sakana.ai", "https://sakana.ai/careers", "foundation-model", "Tokyo, Japan", "$200M"),
    ("Reka AI", "https://reka.ai", "https://reka.ai/careers", "foundation-model", "London, UK", "$58M"),

    # AI safety / alignment
    ("Safe Superintelligence (SSI)", "https://ssi.inc", "", "ai-safety", "Palo Alto, CA", "$1B"),
    ("Redwood Research", "https://www.redwoodresearch.org", "", "ai-safety", "San Francisco, CA", ""),
    ("Conjecture", "https://www.conjecture.dev", "https://www.conjecture.dev/careers", "ai-safety", "London, UK", "$25M"),

    # AI agents / coding
    ("Cognition (Devin)", "https://www.cognition.ai", "https://www.cognition.ai/careers", "ai-agent", "San Francisco, CA", "$175M"),
    ("Cursor", "https://cursor.sh", "https://cursor.sh/careers", "ai-agent", "San Francisco, CA", "$400M"),
    ("Replit", "https://replit.com", "https://replit.com/site/careers", "ai-agent", "San Francisco, CA", "$222M"),
    ("Augment Code", "https://www.augmentcode.com", "", "ai-agent", "San Francisco, CA", "$252M"),
    ("Magic AI", "https://magic.dev", "", "ai-agent", "San Francisco, CA", "$465M"),
    ("Poolside AI", "https://www.poolside.ai", "", "ai-agent", "San Francisco, CA", "$500M"),
    ("Factory AI", "https://www.factory.ai", "", "ai-agent", "San Francisco, CA", "$35M"),
    ("Codeium / Windsurf", "https://codeium.com", "https://codeium.com/careers", "ai-agent", "Mountain View, CA", "$150M"),
    ("Adept AI", "https://www.adept.ai", "https://www.adept.ai/careers", "ai-agent", "San Francisco, CA", "$415M"),
    ("Sierra AI", "https://sierra.ai", "https://sierra.ai/careers", "ai-agent", "San Francisco, CA", "$175M"),
    ("Harvey AI", "https://www.harvey.ai", "https://www.harvey.ai/careers", "ai-agent", "San Francisco, CA", "$200M"),
    ("Glean", "https://www.glean.com", "https://www.glean.com/careers", "ai-agent", "Palo Alto, CA", "$360M"),
    ("Decagon", "https://decagon.ai", "https://decagon.ai/careers", "ai-agent", "San Francisco, CA", "$100M"),
    ("Cresta", "https://cresta.com", "https://cresta.com/careers/", "ai-agent", "San Francisco, CA", "$151M"),

    # Generative media (image / video / music / audio)
    ("Midjourney", "https://www.midjourney.com", "https://www.midjourney.com/careers", "ai-app", "San Francisco, CA", ""),
    ("Runway", "https://runwayml.com", "https://runwayml.com/careers/", "ai-app", "New York, NY", "$237M"),
    ("Pika", "https://pika.art", "https://pika.art/careers", "ai-app", "Palo Alto, CA", "$135M"),
    ("Suno", "https://suno.com", "https://suno.com/careers", "ai-app", "Cambridge, MA", "$125M"),
    ("ElevenLabs", "https://elevenlabs.io", "https://elevenlabs.io/careers", "ai-app", "New York, NY", "$180M"),
    ("Stability AI", "https://stability.ai", "https://stability.ai/careers", "ai-app", "London, UK", "$250M"),
    ("Luma AI", "https://lumalabs.ai", "https://lumalabs.ai/careers", "ai-app", "San Francisco, CA", "$43M"),
    ("Ideogram", "https://ideogram.ai", "https://ideogram.ai/careers", "ai-app", "Toronto, Canada", "$80M"),
    ("Black Forest Labs (FLUX)", "https://blackforestlabs.ai", "", "ai-app", "Freiburg, Germany", "$100M"),
    ("Kling AI (Kuaishou)", "https://klingai.com", "", "ai-app", "Beijing, China", ""),
    ("Minimax", "https://www.minimaxi.com", "", "ai-app", "Shanghai, China", "$600M"),
    ("Synthesia", "https://www.synthesia.io", "https://www.synthesia.io/careers", "ai-app", "London, UK", "$156M"),

    # AI infra / MLOps / data
    ("Databricks", "https://www.databricks.com", "https://www.databricks.com/company/careers", "ai-infra", "San Francisco, CA", "$4.3B"),
    ("Anyscale", "https://www.anyscale.com", "https://www.anyscale.com/careers", "ai-infra", "San Francisco, CA", "$259M"),
    ("Modal", "https://modal.com", "https://modal.com/careers", "ai-infra", "New York, NY", "$64M"),
    ("Weights & Biases", "https://wandb.ai", "https://wandb.ai/careers", "ai-infra", "San Francisco, CA", "$250M"),
    ("Hugging Face", "https://huggingface.co", "https://huggingface.co/jobs", "ai-infra", "New York, NY", "$395M"),
    ("Replicate", "https://replicate.com", "https://replicate.com/jobs", "ai-infra", "San Francisco, CA", "$58M"),
    ("Scale AI", "https://scale.com", "https://scale.com/careers", "ai-infra", "San Francisco, CA", "$1.4B"),
    ("Pinecone", "https://www.pinecone.io", "https://www.pinecone.io/careers/", "ai-infra", "New York, NY", "$138M"),
    ("Weaviate", "https://weaviate.io", "https://weaviate.io/company/careers", "ai-infra", "Amsterdam, Netherlands", "$67M"),
    ("Qdrant", "https://qdrant.tech", "https://qdrant.tech/careers/", "ai-infra", "Berlin, Germany", "$28M"),
    ("LangChain", "https://www.langchain.com", "https://www.langchain.com/careers", "ai-infra", "San Francisco, CA", "$25M"),
    ("Fireworks AI", "https://fireworks.ai", "https://fireworks.ai/careers", "ai-infra", "Redwood City, CA", "$52M"),
    ("Groq", "https://groq.com", "https://groq.com/careers/", "ai-chip", "Mountain View, CA", "$640M"),
    ("Cerebras", "https://cerebras.net", "https://cerebras.net/careers/", "ai-chip", "Sunnyvale, CA", "$720M"),
    ("SambaNova", "https://sambanova.ai", "https://sambanova.ai/careers", "ai-chip", "Palo Alto, CA", "$1.1B"),
    ("d-Matrix", "https://d-matrix.ai", "https://d-matrix.ai/careers/", "ai-chip", "Santa Clara, CA", "$160M"),
    ("Rain AI", "https://rain.ai", "", "ai-chip", "San Francisco, CA", "$82M"),
    ("Tenstorrent", "https://tenstorrent.com", "https://tenstorrent.com/careers", "ai-chip", "Toronto, Canada", "$320M"),
    ("Etched", "https://www.etched.com", "https://www.etched.com/careers", "ai-chip", "San Francisco, CA", "$120M"),
    ("MatX", "https://matx.com", "", "ai-chip", "Mountain View, CA", "$30M"),
    ("CoreWeave", "https://www.coreweave.com", "https://www.coreweave.com/careers", "ai-infra", "Roseland, NJ", "$12.6B"),
    ("Lambda", "https://lambdalabs.com", "https://lambdalabs.com/careers", "ai-infra", "San Francisco, CA", "$800M"),
    ("Crusoe Energy", "https://www.crusoeenergy.com", "https://www.crusoeenergy.com/careers", "ai-infra", "Denver, CO", "$600M"),

    # Robotics / embodied AI
    ("Figure AI", "https://figure.ai", "https://figure.ai/careers", "robotics", "Sunnyvale, CA", "$675M"),
    ("1X Technologies", "https://www.1x.tech", "https://www.1x.tech/careers", "robotics", "Moss, Norway", "$125M"),
    ("Skild AI", "https://www.skild.ai", "https://www.skild.ai/careers", "robotics", "Pittsburgh, PA", "$300M"),
    ("Physical Intelligence (Pi)", "https://www.physicalintelligence.company", "https://www.physicalintelligence.company/careers", "robotics", "San Francisco, CA", "$400M"),
    ("Covariant", "https://covariant.ai", "https://covariant.ai/careers/", "robotics", "Emeryville, CA", "$222M"),
    ("Agility Robotics", "https://agilityrobotics.com", "https://agilityrobotics.com/careers", "robotics", "Tangent, OR", "$179M"),
    ("Apptronik", "https://apptronik.com", "https://apptronik.com/careers", "robotics", "Austin, TX", "$350M"),
    ("Boston Dynamics", "https://bostondynamics.com", "https://bostondynamics.com/careers/", "robotics", "Waltham, MA", ""),
    ("Waymo", "https://waymo.com", "https://waymo.com/careers/", "robotics", "Mountain View, CA", ""),
    ("Nuro", "https://nuro.ai", "https://nuro.ai/careers", "robotics", "Mountain View, CA", "$2.1B"),
    ("Aurora", "https://aurora.tech", "https://aurora.tech/careers", "robotics", "Pittsburgh, PA", ""),
    ("Cruise", "https://getcruise.com", "https://getcruise.com/careers", "robotics", "San Francisco, CA", ""),

    # Applied AI / vertical
    ("Perplexity", "https://www.perplexity.ai", "https://www.perplexity.ai/hub/careers", "ai-app", "San Francisco, CA", "$250M"),
    ("Character.AI", "https://character.ai", "https://character.ai/careers", "ai-app", "Menlo Park, CA", "$150M"),
    ("Jasper AI", "https://jasper.ai", "https://jasper.ai/careers", "ai-app", "Austin, TX", "$125M"),
    ("Writer", "https://writer.com", "https://writer.com/careers/", "ai-app", "New York, NY", "$200M"),
    ("Typeface", "https://www.typeface.ai", "https://www.typeface.ai/careers", "ai-app", "San Francisco, CA", "$165M"),
    ("Hebbia", "https://www.hebbia.ai", "https://www.hebbia.ai/careers", "ai-app", "New York, NY", "$130M"),
    ("Coframe", "https://coframe.ai", "", "ai-app", "San Francisco, CA", "$4.5M"),
    ("You.com", "https://you.com", "https://about.you.com/careers/", "ai-app", "San Francisco, CA", "$45M"),
    ("Tome", "https://tome.app", "https://tome.app/careers", "ai-app", "San Francisco, CA", "$81M"),
    ("Observe.AI", "https://www.observe.ai", "https://www.observe.ai/company/careers", "ai-app", "San Francisco, CA", "$213M"),
    ("Inworld AI", "https://inworld.ai", "https://inworld.ai/careers", "ai-app", "Mountain View, CA", "$120M"),
    ("Imbue (fka Generally Intelligent)", "https://imbue.com", "https://imbue.com/careers", "ai-app", "San Francisco, CA", "$200M"),
    ("Nous Research", "https://nousresearch.com", "", "foundation-model", "Remote", ""),
    ("Mistral (Chinese)", "https://www.baichuan-ai.com", "", "foundation-model", "Beijing, China", "$300M"),
    ("Lightmatter", "https://lightmatter.co", "https://lightmatter.co/careers/", "ai-chip", "Mountain View, CA", "$400M"),

    # Stealth / recently announced
    ("Project Prometheus (Bezos)", "", "", "foundation-model", "San Francisco, CA", ""),

    # Bio / science AI
    ("Recursion Pharmaceuticals", "https://www.recursion.com", "https://www.recursion.com/careers", "ai-app", "Salt Lake City, UT", "$1.5B"),
    ("Insitro", "https://insitro.com", "https://insitro.com/careers", "ai-app", "South San Francisco, CA", "$643M"),
    ("Isomorphic Labs", "https://www.isomorphiclabs.com", "https://www.isomorphiclabs.com/careers", "ai-app", "London, UK", ""),
    ("Tempus AI", "https://www.tempus.com", "https://www.tempus.com/careers/", "ai-app", "Chicago, IL", ""),
    ("AbCellera", "https://www.abcellera.com", "https://www.abcellera.com/careers", "ai-app", "Vancouver, Canada", ""),
    ("Atomwise", "https://www.atomwise.com", "https://www.atomwise.com/careers/", "ai-app", "San Francisco, CA", "$174M"),
    ("BioNTech AI", "https://www.biontech.com", "", "ai-app", "Mainz, Germany", ""),

    # Defense / gov AI
    ("Anduril", "https://www.anduril.com", "https://www.anduril.com/careers/", "ai-app", "Costa Mesa, CA", "$3.7B"),
    ("Shield AI", "https://shield.ai", "https://shield.ai/careers/", "ai-app", "San Diego, CA", "$773M"),
    ("Palantir", "https://www.palantir.com", "https://www.palantir.com/careers/", "ai-app", "Denver, CO", ""),
    ("Helsing", "https://helsing.ai", "https://helsing.ai/careers", "ai-app", "Munich, Germany", "$450M"),

    # Autonomous vehicles / transportation
    ("Zoox", "https://zoox.com", "https://zoox.com/careers/", "robotics", "Foster City, CA", ""),
    ("Waabi", "https://waabi.ai", "https://waabi.ai/careers", "robotics", "Toronto, Canada", "$200M"),
    ("Ghost Autonomy", "https://ghostautonomy.com", "", "robotics", "Mountain View, CA", "$220M"),

    # Data labeling / annotation
    ("Labelbox", "https://labelbox.com", "https://labelbox.com/company/careers/", "ai-infra", "San Francisco, CA", "$188M"),
    ("Snorkel AI", "https://snorkel.ai", "https://snorkel.ai/careers/", "ai-infra", "Redwood City, CA", "$135M"),
    ("Surge AI", "https://www.surgehq.ai", "", "ai-infra", "San Francisco, CA", "$7M"),
]


class SeedCompaniesDiscoverer(CompanyDiscoverer):
    source_name = "seed_list"

    def discover(self, limit: Optional[int] = None) -> list[CompanyRecord]:
        records: list[CompanyRecord] = []
        for name, website, careers_url, category, hq, funding in _SEED_COMPANIES:
            records.append(
                CompanyRecord(
                    company_name=name,
                    source=self.source_name,
                    website=website,
                    careers_url=careers_url,
                    category=category,
                    hq_location=hq,
                    funding=funding,
                    description=f"Seed list: {category}",
                )
            )
            if limit and len(records) >= limit:
                break
        return records
