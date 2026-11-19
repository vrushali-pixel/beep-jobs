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
    (make_post("Analyst", desc="3+ years experience"), "asks for 1+ years of experience"),   # BUILD_LOG #27
    (make_post("Data Entry Intern", desc="Pay a registration fee of Rs 999"), "asks for money (scam sign)"),
    (make_post("", "Pune"), "missing title or link"),
])
def test_rules(rules, post, expected):
    assert rules.check(post) == expected


def test_city_aliases(rules):
    assert rules.cities_in("Bangalore; Gurgaon, Haryana; Navi Mumbai") == ["Bengaluru", "Mumbai", "Gurugram"]
    # Hyderabad area names seen in the 19 Nov accuracy check (BUILD_LOG #29)
    assert rules.cities_in("Medchal, Telangana, India") == ["Hyderabad"]
    assert rules.cities_in("Miyapur, Telangana, India") == ["Hyderabad"]


def test_tidy_company():
    names = ["Rubrik Job Board", "HackerRank Careers", "Stable Money1", "ZoomInfo Technologies LLC", "Bosch Group"]
    assert [tidy_company(x) for x in names] == \
        ["Rubrik", "HackerRank", "Stable Money", "ZoomInfo Technologies", "Bosch Group"]


# BUILD_LOG #27: real wordings from live posts. The AI let "1-3 years" posts through.
@pytest.mark.parametrize("text,years", [
    ("B.E. Mechanical with 1 - 3 years of Experience", 1),
    ("4–5 years of graphic design experience", 4),
    ("2+ years of experience managing campaigns", 2),
    ("Experience: 1-3 years", 1),
    ("1+ years’ experience in customer support", 1),
    ("0-1 years in software development", 0),
    ("early-career engineers with up to 2 years of experience", 0),
    ("6 months to 3 years of experience in telesales", 0),
    ("graduates (preferably tier 1 college) OR graduates with 2+ years of work experience", 0),
    ("Experience: 0 months – 5 years", 0),
    ("Hevo was founded 10 years ago", 0),
])
def test_min_experience_years(rules, text, years):
    assert rules.min_experience_years(text) == years


def test_required_experience_drops_unclear_and_clear_titles_but_not_internships(rules):
    two_years = "You bring 2+ years of experience in sales."
    assert rules.check(make_post("Graphic Designer", desc=two_years)) == "asks for 1+ years of experience"
    assert rules.check(make_post("Junior Analyst", desc=two_years)) == "asks for 1+ years of experience"
    assert rules.check(make_post("Marketing Intern", desc=two_years)) == KEEP
    assert rules.check(make_post("Graphic Designer", desc=two_years + " Freshers can apply.")) == KEEP
    assert rules.check(make_post("Graphic Designer", desc="Design social posts.")) == ASK_AI
