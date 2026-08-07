"""Session-safe TranscriptAggregator for merging partial transcripts, deduplicating fragments, and ordering."""

from __future__ import annotations

from collections import defaultdict
from app.voice.schemas import TranscriptChunk


class TranscriptAggregator:
    """Aggregates partial transcript chunks into clean final transcript text per session."""

    def __init__(self) -> None:
        self._session_chunks: dict[str, list[TranscriptChunk]] = defaultdict(list)

    def add_chunk(self, chunk: TranscriptChunk, session_id: str | None = None) -> None:
        """Ingest a partial transcript chunk preserving timestamp order per session."""
        if not chunk or not chunk.text or not chunk.text.strip():
            return
        target_session = session_id or chunk.session_id or "default"
        self._session_chunks[target_session].append(chunk)

    def get_final_transcript(self, session_id: str | None = None) -> str:
        """Merge, deduplicate, and return final transcript text string for specified session."""
        if session_id:
            chunks = self._session_chunks.get(session_id, [])
        else:
            # Fallback: flatten all session chunks if no specific session_id is provided
            chunks = [c for chunk_list in self._session_chunks.values() for c in chunk_list]

        if not chunks:
            return ""

        sorted_chunks = sorted(chunks, key=lambda c: c.timestamp_ms)
        text_fragments: list[str] = []

        for chunk in sorted_chunks:
            clean_text = chunk.text.strip()
            if not text_fragments:
                text_fragments.append(clean_text)
            else:
                last_fragment = text_fragments[-1]
                if clean_text != last_fragment:
                    # Deduplicate overlapping word prefix/suffix if present
                    words_last = last_fragment.split()
                    words_current = clean_text.split()
                    if words_last and words_current and words_last[-1].lower() == words_current[0].lower():
                        clean_text = " ".join(words_current[1:])
                    if clean_text:
                        text_fragments.append(clean_text)

        return " ".join(text_fragments).strip()

    def clear_session(self, session_id: str) -> None:
        """Clear chunks for a specific session."""
        self._session_chunks.pop(session_id, None)

    def clear(self) -> None:
        """Reset all aggregator state."""
        self._session_chunks.clear()
