"""Validation data classes."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Issue:
    title: str
    description: str
    why_it_matters: str
    recommendation: str
    source: str = "rule_engine"  # "rule_engine" or "deepseek"


@dataclass
class ValidationResult:
    validator_name: str
    passed: bool
    issues: list[Issue] = field(default_factory=list)


@dataclass
class QAReport:
    overall_status: str  # "Ready to Send" | "Needs Review" | "Not Ready to Send"
    validation_summary: dict
    issues: list[Issue] = field(default_factory=list)
    ai_review_summary: str = ""
    final_recommendation: str = ""
