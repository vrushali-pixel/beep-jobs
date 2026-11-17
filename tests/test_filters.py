"""India / entry-level / scam rules, and company-name tidying."""

import pytest

from conftest import make_post
from fresherjobs.filters import ASK_AI, KEEP, tidy_company


@pytest.mark.parametrize("post,expected", [
    (make_post("Software Engineer Intern"), KEEP),
    (make_post("Graduate Engineer Trainee", "Pune, IN"), KEEP),
    (make_post("Software Engineer Intern", "Gurgaon"), KEEP),
    (make_post("Senior Software Engineer"), "senior title"),
    (make_post("Engineering Manager"), "senior title"),
    (make_post("Software Engineer II"), "senior title"),
    (make_post("Software Engineer Intern", "San Francisco, CA"), "not in India"),
    (make_post("Software Engineer Intern", "Remote"), "not in India"),
    (make_post("Software Engineer Intern", "Remote", desc="Open to candidates across India"), KEEP),
    (make_post("Software Engineer Intern", "Remote - Anywhere", desc="team in India"), KEEP),
    (make_post("Operations Specialist", "The Philippines (Remote)", desc="We hire across India"), "not in India"),
    (make_post("Analyst", desc="Freshers welcome, 2026 batch"), KEEP),
    (make_post("Analyst", desc="3+ years experience"), ASK_AI),
    (make_post("Data Entry Intern", desc="Pay a registration fee of Rs 999"), "asks for money (scam sign)"),
    (make_post("", "Pune"), "missing title or link"),
])
def test_rules(rules, post, expected):
    assert rules.check(post) == expected


def test_city_aliases(rules):
    assert rules.cities_in("Bangalore; Gurgaon, Haryana; Navi Mumbai") == ["Bengaluru", "Mumbai", "Gurugram"]


def test_tidy_company():
    names = ["Rubrik Job Board", "HackerRank Careers", "Stable Money1", "ZoomInfo Technologies LLC", "Bosch Group"]
    assert [tidy_company(x) for x in names] == \
        ["Rubrik", "HackerRank", "Stable Money", "ZoomInfo Technologies", "Bosch Group"]
