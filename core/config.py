from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_REPO_ROOT / ".env")


@dataclass
class Config:
    kb_root: Path = field(default_factory=lambda: Path(os.environ.get("KB_ROOT", "~/.kb")).expanduser())
    # Chat + classification — local Ollama LLM
    chat_model: str = field(default_factory=lambda: os.environ.get("KB_CHAT_MODEL", "qwen2.5:3b"))
    # Embeddings — Ollama by default; OpenAI when KB_EMBED_PROVIDER=openai
    embed_model: str = field(default_factory=lambda: os.environ.get("KB_EMBED_MODEL", "nomic-embed-text"))
    embed_provider: str = field(default_factory=lambda: os.environ.get("KB_EMBED_PROVIDER", "auto"))
    backend_port: int = field(default_factory=lambda: int(os.environ.get("KB_PORT", "8765")))
    # auto: use OpenAI when OPENAI_API_KEY is set, otherwise Ollama
    llm_provider: str = field(default_factory=lambda: os.environ.get("KB_LLM_PROVIDER", "auto"))
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    openai_embed_model: str = field(
        default_factory=lambda: os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    )
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"))
    # Minutes between proactive insight checks (desktop pet + extension banner)
    proactive_interval_minutes: int = field(
        default_factory=lambda: int(os.environ.get("KB_PROACTIVE_INTERVAL_MINUTES", "20"))
    )

    @property
    def pages_dir(self) -> Path:
        return self.kb_root / "pages"

    @property
    def events_raw_dir(self) -> Path:
        return self.kb_root / "events" / "raw"

    @property
    def events_clean_dir(self) -> Path:
        return self.kb_root / "events" / "clean"

    @property
    def index_dir(self) -> Path:
        return self.kb_root / "index"

    @property
    def graph_dir(self) -> Path:
        return self.kb_root / "graph"

    @property
    def hashes_dir(self) -> Path:
        return self.kb_root / "hashes"

    @property
    def buckets_dir(self) -> Path:
        return self.kb_root / "buckets"

    @property
    def auth_dir(self) -> Path:
        return self.kb_root / "auth"

    @property
    def paused_log(self) -> Path:
        return self.kb_root / "events" / "paused.log"

    @property
    def hash_map_path(self) -> Path:
        return self.kb_root / "hashes" / "map.json"

    @property
    def hash_salt_path(self) -> Path:
        return self.kb_root / "hashes" / "salt"

    @property
    def wiki_dir(self) -> Path:
        return self.kb_root / "wiki"

    @property
    def wiki_raw_dir(self) -> Path:
        return self.kb_root / "wiki" / "raw"

    @property
    def wiki_articles_dir(self) -> Path:
        return self.kb_root / "wiki" / "articles"

    @property
    def wiki_outputs_dir(self) -> Path:
        return self.kb_root / "wiki" / "outputs"

    def ensure_dirs(self) -> None:
        dirs = [
            self.events_raw_dir,
            self.events_clean_dir,
            self.index_dir,
            self.graph_dir,
            self.hashes_dir,
            self.buckets_dir,
            self.auth_dir,
            self.pages_dir,
            self.wiki_raw_dir,
            self.wiki_articles_dir,
            self.wiki_outputs_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


config = Config()
