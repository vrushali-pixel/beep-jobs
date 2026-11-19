"""The page (site/index.html) must only read job fields that publish.py writes to jobs.json."""
import re
from pathlib import Path

from fresherjobs.publish import PAGE_FIELDS

PAGE = Path(__file__).resolve().parents[1] / "site" / "index.html"


def test_page_reads_only_published_fields():
    html = PAGE.read_text(encoding="utf-8")
    used = set(re.findall(r"\bj\.([a-z_]+)\b", html)) - {"_h"}  # _h is the search text the page builds itself
    assert used, "expected the page to read job fields as j.<field>"
    missing = used - set(PAGE_FIELDS)
    assert not missing, f"page reads fields publish.py does not write: {sorted(missing)}"


def test_page_has_menu_filters_and_job_panels():
    html = PAGE.read_text(encoding="utf-8")
    for panel_id in ("menu", "filters", "detail"):
        assert f'id="{panel_id}"' in html
    for view_id in ("v-home", "v-list", "v-about"):
        assert f'id="{view_id}"' in html
