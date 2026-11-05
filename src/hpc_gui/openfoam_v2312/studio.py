"""Case Studio page descriptors (W65 UNIT D, HPC-W65-UI-012).

Page cards and journey page flows for the studio layout. Descriptors only;
no wx widgets are created here. Every card names the real action behind its
primary control, so no inert decorative control can pass validation.
"""
from __future__ import annotations
from dataclasses import dataclass
PAGE_CASE_TREE = "case-tree"
PAGE_SOURCE_EDITOR = "source-editor"
PAGE_INSPECTOR = "inspector"
PAGE_WORKFLOW = "workflow"
PAGE_RUN_PREVIEW = "run-preview"
PAGE_RESULTS = "results"
PAGE_PROBLEMS = "problems"
PAGE_DIFF = "diff"
PAGE_VALIDATION = "validation"
PAGE_LIBRARY = "library"
STUDIO_PAGES = (
    PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_INSPECTOR, PAGE_WORKFLOW,
    PAGE_RUN_PREVIEW, PAGE_RESULTS, PAGE_PROBLEMS, PAGE_DIFF,
    PAGE_VALIDATION, PAGE_LIBRARY,
)
REQUIRED_PAGES = frozenset({PAGE_SOURCE_EDITOR, PAGE_VALIDATION})
JOURNEY_PAGES = {
    "T1": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_WORKFLOW, PAGE_RUN_PREVIEW, PAGE_RESULTS, PAGE_VALIDATION),
    "T2": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_WORKFLOW, PAGE_RUN_PREVIEW, PAGE_RESULTS, PAGE_PROBLEMS, PAGE_VALIDATION),
    "T3": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_PROBLEMS, PAGE_WORKFLOW, PAGE_RUN_PREVIEW, PAGE_RESULTS, PAGE_VALIDATION),
    "T4": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_INSPECTOR, PAGE_WORKFLOW, PAGE_RESULTS, PAGE_VALIDATION),
    "T5": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_WORKFLOW, PAGE_RUN_PREVIEW, PAGE_DIFF, PAGE_RESULTS, PAGE_VALIDATION),
    "T6": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_INSPECTOR, PAGE_WORKFLOW, PAGE_RUN_PREVIEW, PAGE_RESULTS, PAGE_VALIDATION),
    "T7": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_WORKFLOW, PAGE_RESULTS, PAGE_VALIDATION),
    "T8": (PAGE_CASE_TREE, PAGE_SOURCE_EDITOR, PAGE_INSPECTOR, PAGE_WORKFLOW, PAGE_RUN_PREVIEW, PAGE_RESULTS, PAGE_LIBRARY, PAGE_VALIDATION),
}
@dataclass(frozen=True)
class PageCard:
    """One studio page card with its backing action."""
    page: str
    title: str
    action: str
    needs_linter: bool = False
    def to_dict(self):
        return {
            "page": self.page, "title": self.title,
            "action": self.action, "needs_linter": self.needs_linter,
        }
    @staticmethod
    def from_dict(raw):
        return PageCard(
            page=str(raw["page"]), title=str(raw["title"]),
            action=str(raw.get("action", "")),
            needs_linter=bool(raw.get("needs_linter", False)),
        )
def validate_page(card):
    """Return deterministic error strings; empty means displayable."""
    errors = []
    if card.page not in STUDIO_PAGES:
        errors.append("unknown studio page: " + card.page)
    if not card.title.strip():
        errors.append("empty page title")
    if not card.action.strip():
        errors.append("page card has no backing action: " + card.page)
    return tuple(errors)
def validate_journey_pages(journey_id, pages):
    """Check a page list against its approved journey flow."""
    if journey_id not in JOURNEY_PAGES:
        return ("unknown journey: " + journey_id,)
    seen = set()
    for page in pages:
        if page not in STUDIO_PAGES:
            return ("unknown studio page in journey " + journey_id + ": " + page,)
        if page in seen:
            return ("duplicate page in journey " + journey_id + ": " + page,)
        seen.add(page)
    missing = [page for page in REQUIRED_PAGES if page not in seen]
    if missing:
        return ("journey " + journey_id + " misses required pages: " + "/".join(sorted(missing)),)
    expected = JOURNEY_PAGES[journey_id]
    if tuple(pages) != expected:
        return ("journey " + journey_id + " expects " + "/".join(expected)
                + " but got " + "/".join(tuple(pages)),)
    return ()
def list_studio_pages():
    return STUDIO_PAGES