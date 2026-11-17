"""LLM tagging: role, city, type, skills, eligibility, pay and scam flags for each post."""

from fresherjobs.tagging.fallback import keyword_tag
from fresherjobs.tagging.tagger import Tagger

__all__ = ["Tagger", "keyword_tag"]
