from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import uuid

MEMO_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
MEMO_ORDER_FILE_NAME = ".order.json"


@dataclass(slots=True, frozen=True)
class MemoDocument:
    memo_id: str
    title: str
    content: str


@dataclass(slots=True, frozen=True)
class MemoSearchResult:
    memo_id: str
    title: str
    snippet: str


class MemoStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.order_path = self.root / MEMO_ORDER_FILE_NAME

    def list_memos(self) -> list[MemoDocument]:
        memos: list[MemoDocument] = []
        for path in self.root.glob("*.md"):
            try:
                memos.append(self._read_path(path))
            except OSError:
                continue

        by_id = {memo.memo_id: memo for memo in memos}
        ordered: list[MemoDocument] = []
        seen: set[str] = set()

        for memo_id in self._load_order():
            memo = by_id.get(memo_id)
            if memo is None or memo_id in seen:
                continue
            ordered.append(memo)
            seen.add(memo_id)

        remaining = sorted(
            (memo for memo in memos if memo.memo_id not in seen),
            key=lambda memo: memo.title.casefold(),
        )
        ordered.extend(remaining)
        return ordered

    def create(self, title: str, content: str = "") -> MemoDocument:
        current_order = [memo.memo_id for memo in self.list_memos()]
        memo_id = uuid.uuid4().hex
        memo = self.save(memo_id, title, content)
        self._save_order([*current_order, memo.memo_id])
        return memo

    def load(self, memo_id: str) -> MemoDocument:
        return self._read_path(self.path_for(memo_id))

    def save(self, memo_id: str, title: str, content: str) -> MemoDocument:
        clean_title = " ".join(title.splitlines()).strip() or "제목 없음"
        path = self.path_for(memo_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.serialize(clean_title, content), encoding="utf-8")
        return MemoDocument(memo_id=memo_id, title=clean_title, content=content)

    def delete(self, memo_id: str) -> None:
        path = self.path_for(memo_id)
        if path.exists():
            path.unlink()

        order = [
            value
            for value in self._load_order()
            if value != memo_id
        ]
        if order:
            self._save_order(order)
        elif self.order_path.exists():
            self.order_path.unlink()

    def reorder(self, memo_ids: list[str]) -> None:
        existing = {path.stem for path in self.root.glob("*.md")}
        if (
            len(memo_ids) != len(existing)
            or len(set(memo_ids)) != len(memo_ids)
            or set(memo_ids) != existing
        ):
            raise ValueError("memo order must contain every memo exactly once")
        self._save_order(memo_ids)

    def search(self, query: str) -> list[MemoSearchResult]:
        keyword = query.strip().casefold()
        if not keyword:
            return []

        results: list[MemoSearchResult] = []
        for memo in self.list_memos():
            title_match = keyword in memo.title.casefold()
            content_match = keyword in memo.content.casefold()
            if not title_match and not content_match:
                continue
            results.append(
                MemoSearchResult(
                    memo_id=memo.memo_id,
                    title=memo.title,
                    snippet=(
                        f"제목: {memo.title}"
                        if title_match
                        else self._matching_line(memo.content, keyword)
                    ),
                )
            )
        return results

    def path_for(self, memo_id: str) -> Path:
        if not MEMO_ID_RE.fullmatch(memo_id):
            raise ValueError("invalid memo id")
        return self.root / f"{memo_id}.md"

    @staticmethod
    def serialize(title: str, content: str) -> str:
        if content:
            return f"# {title}\n\n{content}"
        return f"# {title}\n"

    @staticmethod
    def parse(memo_id: str, text: str) -> MemoDocument:
        if not text.startswith("# "):
            return MemoDocument(memo_id=memo_id, title=memo_id, content=text)

        first_break = text.find("\n")
        if first_break < 0:
            return MemoDocument(
                memo_id=memo_id,
                title=text[2:].strip() or "제목 없음",
                content="",
            )

        title = text[2:first_break].strip() or "제목 없음"
        content = text[first_break + 1 :]
        if content.startswith("\n"):
            content = content[1:]
        return MemoDocument(memo_id=memo_id, title=title, content=content)

    def _read_path(self, path: Path) -> MemoDocument:
        text = path.read_text(encoding="utf-8")
        return self.parse(path.stem, text)

    def _load_order(self) -> list[str]:
        if not self.order_path.exists():
            return []

        try:
            payload = json.loads(self.order_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(payload, list):
            return []

        return [
            value
            for value in payload
            if isinstance(value, str) and MEMO_ID_RE.fullmatch(value)
        ]

    def _save_order(self, memo_ids: list[str]) -> None:
        self.order_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.order_path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(memo_ids, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp.replace(self.order_path)

    @staticmethod
    def _matching_line(content: str, keyword: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and keyword in stripped.casefold():
                return stripped
        return "본문에서 일치"
