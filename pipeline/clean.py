"""Steps 2-4: CLEAN, FILTER, DE-DUPE. Plain rules, no AI, so they are free and predictable."""
import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_INDIA_WORD = re.compile(r"\bindia\b", re.I)
_INDIA_CODE = re.compile(r"\bIND?\b(?=\s*[-,;)]|\s*$)|\bIN-[A-Z]{2}\b")   # "Pune, IN", "IND", "IN-MH"


class _India:
    @staticmethod
    def search(text):
        return _INDIA_WORD.search(text) or _INDIA_CODE.search(text)


INDIA_RE = _India()


def _word_re(words):
    parts = []
    for w in words:
        w = w.strip().lower()
        if not w:
            continue
        left = r"\b" if w[0].isalnum() else ""
        right = r"\b" if w[-1].isalnum() else ""
        parts.append(left + re.escape(w) + right)
    return re.compile("|".join(parts)) if parts else re.compile(r"(?!x)x")


class Rules:
    def __init__(self, cfg):
        self.entry = _word_re(cfg["entry_title_words"])
        self.senior = _word_re(cfg["senior_title_words"])
        self.fresher = _word_re(cfg["fresher_desc_phrases"])
        self.fraud = _word_re(cfg["fraud_phrases"])
        self.city_aliases = [(alias, city) for city, aliases in cfg["cities"].items() for alias in aliases]
        self.city_re = {city: _word_re(aliases) for city, aliases in cfg["cities"].items()}

    def cities_in(self, text):
        t = text.lower()
        return [c for c, rx in self.city_re.items() if rx.search(t)]

    def is_india(self, post):
        loc = post["location"]
        if INDIA_RE.search(loc):
            return True
        found = [c for c in self.cities_in(loc) if c != "Remote"]
        if found:
            return True
        # "Remote" alone could be anywhere: accept only if the post itself says India.
        if "Remote" in self.cities_in(loc) and INDIA_RE.search(post["description"][:3000]):
            return True
        return False

    def entry_level(self, post):
        title = post["title"].lower()
        if self.senior.search(title):
            return False, "senior title"
        if self.entry.search(title):
            return True, ""
        if self.fresher.search(post["description"].lower()):
            return True, ""
        return False, "not an entry-level title"

    def check(self, post):
        """Return '' if the post passes, else the reason it was rejected."""
        if not post["title"].strip() or not post["url"].startswith("http"):
            return "missing title or link"
        if not self.is_india(post):
            return "not in India"
        ok, why = self.entry_level(post)
        if not ok:
            return why
        if self.fraud.search((post["title"] + " " + post["description"]).lower()):
            return "asks for money (scam sign)"
        return ""


def canon_url(u):
    p = urlsplit(u.strip())
    q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(("utm_", "source", "ref"))]
    return urlunsplit(("https", p.netloc.lower().removeprefix("www."), p.path.rstrip("/"), urlencode(q), ""))


def norm_company(s):
    s = re.sub(r"\(.*?\)", " ", s.lower())
    s = re.sub(r"\b(pvt|private|ltd|limited|llp|inc|corp|corporation|technologies|technology|india|group)\b\.?", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def norm_title(s, rules):
    t = s.lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)                 # "(2026)", "[Remote]"
    t = re.sub(r"\b20\d\d\b|\bsummer\b|\bwinter\b|\bfall\b|\bspring\b", " ", t)
    for alias, _ in rules.city_aliases:                       # "Intern - Bangalore"
        t = re.sub(r"\b" + re.escape(alias) + r"\b", " ", t)
    t = re.sub(r"\bindia\b|\bremote\b|\bhybrid\b|\bonsite\b|\bon-site\b", " ", t)
    return " ".join(re.sub(r"[^a-z0-9+#]+", " ", t).split())


def job_id(company, title, rules):
    """Stable across days, so tomorrow's copy of the same post matches today's."""
    key = norm_company(company) + "|" + norm_title(title, rules)
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def dedupe(posts, rules):
    """Merge duplicates. Two posts are the same job when they share a link, or when the
    same company lists the same role (after removing years, cities, brackets).
    Multi-city copies are merged into one post that lists every city."""
    by_id, by_url, dup = {}, {}, 0
    for p in posts:
        p = dict(p)
        p["id"] = job_id(p["company"], p["title"], rules)
        cu = canon_url(p["url"])
        hit = by_id.get(p["id"]) or by_id.get(by_url.get(cu))
        if hit is None:
            by_id[p["id"]] = p
            by_url[cu] = p["id"]
            continue
        dup += 1
        if p["location"] and p["location"] not in hit["location"]:
            hit["location"] = f"{hit['location']}; {p['location']}".strip("; ")
        if len(p["description"]) > len(hit["description"]):
            hit["description"] = p["description"]
        if p["posted"] and (not hit["posted"] or p["posted"] > hit["posted"]):
            hit["posted"] = p["posted"]
        by_url[cu] = hit["id"]
    return list(by_id.values()), dup
