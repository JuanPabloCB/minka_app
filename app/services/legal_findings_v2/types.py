from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _maybe_to_dict(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "TokenUsage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class ContractUnit:
    segment_id: str
    level: str
    title_guess: str
    text: str
    source: str
    start_index: int
    end_index: int

    parent_segment_id: str | None = None
    ordinal_rank: int | None = None
    parent_ordinal_rank: int | None = None
    hierarchy_id: str | None = None
    local_marker: str | None = None
    reason_hint: str | None = None

    reviewed_by_llm: bool = False
    header_status: str = "not_applicable"
    confidence_tier: str | None = None
    review_status: str | None = None

    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMClauseVerdict:
    segment_id: str
    decision: str
    normalized_level: str | None = None
    normalized_parent_rank: int | None = None
    normalized_hierarchy_id: str | None = None
    normalized_title: str | None = None
    is_valid_clause_unit: bool = True
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClauseDetectionPartition:
    trusted_units: list[ContractUnit] = field(default_factory=list)
    llm_candidates: list[ContractUnit] = field(default_factory=list)
    rejected_units: list[ContractUnit] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trusted_units": [_maybe_to_dict(u) for u in self.trusted_units],
            "llm_candidates": [_maybe_to_dict(u) for u in self.llm_candidates],
            "rejected_units": [_maybe_to_dict(u) for u in self.rejected_units],
        }


@dataclass
class GapCandidate:
    segment_id: str
    expected_rank: int
    previous_rank: int | None
    next_rank: int | None
    start_index: int
    end_index: int
    text: str

    start_line_index: int | None = None
    end_line_index: int | None = None
    header_candidates: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class GapCandidateVerdict:
    gap_segment_id: str
    accepted: bool
    ordinal_rank: int | None = None
    header_text: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class ClauseDetectionSummary:
    formal_clause_count: int = 0
    confirmed_main_clause_count: int = 0
    possible_main_clause_count: int = 0
    rejected_main_clause_count: int = 0

    subclause_count: int = 0
    list_item_count: int = 0
    atomic_provision_count: int = 0
    total_contract_units: int = 0
    appendix_length: int = 0

    missing_expected_ranks_count: int = 0
    needs_review_count: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class ClauseDetectionResult:
    formal_clauses: list[ContractUnit] = field(default_factory=list)

    confirmed_main_clauses: list[ContractUnit] = field(default_factory=list)
    possible_main_clauses: list[ContractUnit] = field(default_factory=list)
    rejected_main_clauses: list[ContractUnit] = field(default_factory=list)

    subclauses: list[ContractUnit] = field(default_factory=list)
    list_items: list[ContractUnit] = field(default_factory=list)

    atomic_findings: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)

    missing_expected_ranks: list[int] = field(default_factory=list)
    needs_review: list[ContractUnit] = field(default_factory=list)

    summary: ClauseDetectionSummary | dict[str, Any] = field(default_factory=ClauseDetectionSummary)
    appendix_text: str = ""
    token_usage: TokenUsage | dict[str, Any] = field(default_factory=TokenUsage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "formal_clauses": [_maybe_to_dict(u) for u in self.formal_clauses],
            "confirmed_main_clauses": [_maybe_to_dict(u) for u in self.confirmed_main_clauses],
            "possible_main_clauses": [_maybe_to_dict(u) for u in self.possible_main_clauses],
            "rejected_main_clauses": [_maybe_to_dict(u) for u in self.rejected_main_clauses],
            "subclauses": [_maybe_to_dict(u) for u in self.subclauses],
            "list_items": [_maybe_to_dict(u) for u in self.list_items],
            "atomic_findings": self.atomic_findings,
            "findings": self.findings,
            "missing_expected_ranks": self.missing_expected_ranks,
            "needs_review": [_maybe_to_dict(u) for u in self.needs_review],
            "summary": _maybe_to_dict(self.summary),
            "appendix_text": self.appendix_text,
            "token_usage": _maybe_to_dict(self.token_usage),
        }


@dataclass
class PdfLine:
    page_num: int
    line_index: int
    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    global_start: int
    global_end: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentLayout:
    full_text: str
    lines: list[PdfLine] = field(default_factory=list)
    page_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_text": self.full_text,
            "lines": [_maybe_to_dict(line) for line in self.lines],
            "page_count": self.page_count,
        }