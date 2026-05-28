from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    kb_root: Path = field(default_factory=lambda: Path(os.environ.get("KB_ROOT", "~/.kb")).expanduser())
    # Chat + classification — local Ollama LLM
    chat_model: str = field(default_factory=lambda: os.environ.get("KB_CHAT_MODEL", "llama3.2:8b"))
    # Embeddings — dedicated embedding model
    embed_model: str = field(default_factory=lambda: os.environ.get("KB_EMBED_MODEL", "nomic-embed-text"))
    backend_port: int = field(default_factory=lambda: int(os.environ.get("KB_PORT", "8765")))

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

    def ensure_dirs(self) -> None:
        dirs = [
            self.events_raw_dir,
            self.events_clean_dir,
            self.index_dir,
            self.graph_dir,
            self.hashes_dir,
            self.buckets_dir,
            self.auth_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


config = Config()
