from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.store import InMemoryStore


@dataclass
class SourceAdapterSpec:
    name: str
    kind: str
    description: str
    requires_manual_review: bool = True
    aliases: tuple[str, ...] = ()
    public: bool = True


class SourceAdapter:
    spec: SourceAdapterSpec

    def collect(self, *, job_order_id: str, items: list[dict], source_config: dict) -> list[dict]:
        raise NotImplementedError


class StructuredImportAdapter(SourceAdapter):
    spec = SourceAdapterSpec(
        name="structured-import",
        kind="structured-import",
        description="Import already normalized candidate payloads into the buffered review lane before they touch the main candidate system.",
        aliases=("experimental-browser-adapter",),
    )

    def collect(self, *, job_order_id: str, items: list[dict], source_config: dict) -> list[dict]:
        source_label = (source_config.get("source_label") or "structured-import").strip()
        if not items:
            raise ValueError("Structured import requires at least one candidate payload")
        normalized_items = []
        for item in items:
            full_name = (item.get("full_name") or item.get("name") or "").strip()
            resume_text = (item.get("resume_text") or item.get("summary") or "").strip()
            if not full_name:
                raise ValueError("Structured import requires full_name on every candidate payload")
            if not resume_text:
                raise ValueError("Structured import requires resume_text or summary on every candidate payload")
            normalized_items.append(
                {
                    **item,
                    "full_name": full_name,
                    "resume_text": resume_text,
                    "source_label": source_label,
                    "captured_at": _captured_at(source_config),
                    "adapter_kind": self.spec.kind,
                }
            )
        return normalized_items


class BrowserCaptureAdapter(SourceAdapter):
    spec = SourceAdapterSpec(
        name="browser-capture",
        kind="browser-capture",
        description="Controlled browser capture lane that buffers manually reviewed source findings behind explicit review and promote steps.",
        aliases=("browser-prototype",),
        public=False,
    )

    def collect(self, *, job_order_id: str, items: list[dict], source_config: dict) -> list[dict]:
        source_url = (source_config.get("source_url") or "").strip()
        if not source_url:
            raise ValueError("Browser capture requires source_url")
        source_label = (source_config.get("source_label") or "browser-capture").strip()
        if items:
            return [
                {
                    **item,
                    "source_url": source_url,
                    "source_label": source_label,
                    "capture_notes": source_config.get("capture_notes"),
                    "captured_at": _captured_at(source_config),
                    "adapter_kind": self.spec.kind,
                }
                for item in items
            ]

        capture_notes = (source_config.get("capture_notes") or "").strip()
        if not capture_notes and not source_config.get("candidate_name"):
            raise ValueError("Browser capture requires capture_notes or candidate_name")

        blocks = _split_capture_blocks(capture_notes) if capture_notes else [""]
        captured_items: list[dict] = []
        for index, block in enumerate(blocks):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            candidate_name = (
                source_config.get("candidate_name")
                if len(blocks) == 1 and source_config.get("candidate_name")
                else _extract_prefixed(lines, "candidate")
            ) or f"Browser Prospect {index + 1}"
            current_title = (
                source_config.get("current_title")
                if len(blocks) == 1 and source_config.get("current_title")
                else _extract_prefixed(lines, "title")
            )
            current_company = (
                source_config.get("current_company")
                if len(blocks) == 1 and source_config.get("current_company")
                else _extract_prefixed(lines, "company")
            )
            city = (source_config.get("city") if len(blocks) == 1 and source_config.get("city") else _extract_prefixed(lines, "city"))
            email = (source_config.get("email") if len(blocks) == 1 and source_config.get("email") else _extract_prefixed(lines, "email"))
            phone = (source_config.get("phone") if len(blocks) == 1 and source_config.get("phone") else _extract_prefixed(lines, "phone"))
            resume_text = (
                source_config.get("resume_text")
                if len(blocks) == 1 and source_config.get("resume_text")
                else block
            ) or capture_notes or "Browser capture pending richer summary."
            captured_items.append(
                {
                    "full_name": candidate_name,
                    "current_company": current_company,
                    "current_title": current_title,
                    "city": city,
                    "email": email,
                    "phone": phone,
                    "resume_text": resume_text,
                    "source_url": source_url,
                    "source_label": source_label,
                    "capture_notes": block or capture_notes,
                    "captured_at": _captured_at(source_config),
                    "adapter_kind": self.spec.kind,
                }
            )
        return captured_items


def _extract_prefixed(lines: list[str], key: str) -> str | None:
    prefix = f"{key}:"
    for line in lines:
        if line.lower().startswith(prefix):
            return line.split(":", 1)[1].strip() or None
    return None


def _captured_at(source_config: dict) -> str:
    return (source_config.get("captured_at") or datetime.now(timezone.utc).isoformat()).strip()


def _split_capture_blocks(capture_notes: str) -> list[str]:
    blocks = [block.strip() for block in capture_notes.split("\n---\n") if block.strip()]
    return blocks or [capture_notes.strip()]


class SourceAdapterRegistry:
    def __init__(self, store: InMemoryStore | None = None) -> None:
        self.store = store
        adapters = (StructuredImportAdapter(), BrowserCaptureAdapter())
        self._canonical_adapters = {adapter.spec.name: adapter for adapter in adapters}
        self._adapters = {}
        for adapter in adapters:
            self._adapters[adapter.spec.name] = adapter
            for alias in adapter.spec.aliases:
                self._adapters[alias] = adapter

    def list_specs(self) -> list[dict]:
        return [
            {
                "name": adapter.spec.name,
                "kind": adapter.spec.kind,
                "description": adapter.spec.description,
                "requires_manual_review": adapter.spec.requires_manual_review,
                "aliases": list(adapter.spec.aliases),
            }
            for adapter in self._canonical_adapters.values()
            if adapter.spec.public
        ]

    def normalize_public_source_name(self, source_name: str) -> str:
        normalized_name = source_name.strip()
        adapter = self._adapters.get(normalized_name)
        if not adapter:
            raise ValueError(f"Unknown source adapter: {source_name}")
        if not adapter.spec.public:
            raise ValueError(
                f"Source adapter '{normalized_name}' is retired from the public experimental contract; use 'structured-import'"
            )
        return adapter.spec.name

    def collect(self, *, source_name: str, job_order_id: str, items: list[dict], source_config: dict) -> list[dict]:
        canonical_name = self.normalize_public_source_name(source_name)
        adapter = self._canonical_adapters[canonical_name]
        return adapter.collect(job_order_id=job_order_id, items=items, source_config=source_config)
