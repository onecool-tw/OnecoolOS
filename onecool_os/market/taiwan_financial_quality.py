"""Evidence-limited financial research notes; never an investment signal."""
from __future__ import annotations

from math import isfinite

VERSION = "onecool_tw_financial_quality_v1"
MISSING_CHECKS = ["營業現金流與獲利核對", "ROE與財務槓桿拆解", "存貨及應收帳款同期變化"]


def number(value):
    try:
        result = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def assess_financial_quality(income: dict, industry: str, period: str) -> dict:
    """Use CI income fields only; absent full statements cannot earn NORMAL.

    Figures are the source's reported cumulative period, not inferred single
    quarters. Non-operating income is not automatically a one-off item.
    """
    result = {
        "version": VERSION,
        "status": "INSUFFICIENT_DATA",
        "label": "資料不足",
        "as_of": period,
        "source_snapshot_date": income.get("出表日期"),
        "scope": "INCOME_STATEMENT_ONLY",
        "period_basis": "SOURCE_REPORTED_CUMULATIVE",
        "ranking_effect": "NONE",
        "missing_checks": list(MISSING_CHECKS),
        "flags": [],
        "evidence": {},
    }
    source = income.get("_financial_source")
    if any(word in industry for word in ("金融", "保險", "銀行", "證券")) or (
        source and not source.endswith("_ci")
    ):
        result["reason"] = "金融業須用專屬財報檢核，目前資料不足"
        result["scope"] = "SECTOR_SPECIFIC_REVIEW_REQUIRED"
        return result
    fields = {
        "operating_profit": "營業利益（損失）",
        "non_operating_profit": "營業外收入及支出",
        "pretax_profit": "稅前淨利（淨損）",
    }
    values = {key: number(income.get(field)) for key, field in fields.items()}
    result["evidence"] = {
        key: {"field": field, "value": values[key]}
        for key, field in fields.items()
    }
    result["source_url"] = source
    if any(value is None for value in values.values()):
        result["missing_checks"].insert(0, "本業與業外獲利核對")
        result["reason"] = "損益欄位或完整財報不足，尚無法判定品質正常"
        return result
    operating, non_operating, pretax = (values[key] for key in fields)
    if abs(operating + non_operating - pretax) > max(1, abs(pretax) * 0.001):
        result["reason"] = "本業、業外與稅前損益無法勾稽，需覆核來源"
        result["missing_checks"].insert(0, "損益勾稽")
        return result
    if operating <= 0 and pretax > 0:
        result["flags"].append("OPERATING_NOT_PROFITABLE")
        result["reason"] = "稅前獲利為正，但本業未獲利；需核對業外來源"
    elif operating > 0 and non_operating > operating:
        result["flags"].append("NON_OPERATING_DOMINANT")
        result["reason"] = "業外淨收益高於本業利益；需核對是否可持續"
    elif pretax <= 0:
        result["flags"].append("PRETAX_NOT_PROFITABLE")
        result["reason"] = "稅前未獲利，需覆核EPS與整體損益差異"
    else:
        result["reason"] = "本業／業外初檢未見上述警示；現金流、槓桿及周轉資料不足"
    if result["flags"]:
        result.update(status="REVIEW", label="需留意")
    return result
