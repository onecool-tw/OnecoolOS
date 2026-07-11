"""Enums for the Onecool Research Framework."""

from __future__ import annotations

from enum import StrEnum


class ResearchProviderType(StrEnum):
    """Supported external research provider classes."""

    CHATGPT = "CHATGPT"
    GEMINI = "GEMINI"
    EBAY = "EBAY"
    CARD_LADDER = "CARD_LADDER"
    MANUAL = "MANUAL"
    CUSTOM = "CUSTOM"


class ResearchCapability(StrEnum):
    """Capabilities that a research provider may expose."""

    TEXT_RESEARCH = "TEXT_RESEARCH"
    MARKET_RESEARCH = "MARKET_RESEARCH"
    SOLD_COMPARABLES = "SOLD_COMPARABLES"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    NEWS = "NEWS"
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    IMAGE_ANALYSIS = "IMAGE_ANALYSIS"


class ResearchStatus(StrEnum):
    """Status for normalized provider research results."""

    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NO_MATCH = "NO_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ResearchConfidence(StrEnum):
    """Confidence carried by provider output after normalization."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"


class ResearchType(StrEnum):
    """Research domains supported by the framework."""

    COLLECTIBLE_MARKET = "COLLECTIBLE_MARKET"
    SOLD_COMPARABLES = "SOLD_COMPARABLES"
    VALUATION_SUPPORT = "VALUATION_SUPPORT"
    ASSET_IDENTITY = "ASSET_IDENTITY"
    NEWS_CONTEXT = "NEWS_CONTEXT"
    PORTFOLIO_CONTEXT = "PORTFOLIO_CONTEXT"
    CUSTOM = "CUSTOM"
