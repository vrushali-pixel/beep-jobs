"""Accuracy scoring of the hand-checked sample."""

from fresherjobs.evaluation import score_rows


def test_score_rows():
    rows = [
        {"original_title": "A", "ai_role": "coding", "true_role": "coding",
         "ai_cities": "Pune; Remote", "true_cities": "remote, pune"},
        {"original_title": "B", "ai_role": "hr", "true_role": "operations", "ai_cities": "Pune", "true_cities": "Pune"},
        {"original_title": "C", "ai_role": "qa", "true_role": "qa", "ai_cities": "Pune", "true_cities": "Mumbai"},
        {"original_title": "D", "ai_role": "qa", "true_role": "", "ai_cities": "", "true_cities": ""},  # not checked
    ]
    res = score_rows(rows)
    assert res["checked"] == 3
    assert (res["role_pct"], res["city_pct"], res["both_pct"]) == (66.7, 66.7, 33.3)
    assert res["role_mistakes"] == {("operations", "hr"): 1}
    assert res["city_mistakes"] == [("C", "Pune", "Mumbai")]
