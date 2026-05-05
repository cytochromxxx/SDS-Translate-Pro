#!/usr/bin/env python3
"""
SDS Completeness Validator
Validates parsed SDS data against required fields and generates gap reports.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Section names for reporting
SECTION_NAMES = {
    1: "Identification",
    2: "Hazard Identification",
    3: "Composition",
    4: "First Aid",
    5: "Firefighting",
    6: "Accidental Release",
    7: "Handling & Storage",
    8: "Exposure Controls",
    9: "Physical & Chemical Properties",
    10: "Stability & Reactivity",
    11: "Toxicological Information",
    12: "Ecological Information",
    13: "Disposal",
    14: "Transport",
    15: "Regulatory Information",
    16: "Other Information",
}

# Required fields per section.
# Each entry is a tuple: (field_path, is_critical)
# field_path uses dot notation relative to the section dict.
# For section 16, the data lives under 'other_information' key at root level.
SECTION_FIELDS: Dict[int, List[Tuple[str, bool]]] = {
    1: [
        ("product_identifier.trade_name", True),
        ("supplier_details.name", True),
        ("emergency_phone.number", True),
        ("relevant_uses.lcs", False),  # recommended
    ],
    2: [
        ("classification", True),          # list, non-empty
        ("labelling.signal_word", True),
    ],
    3: [
        ("mixture_components", True),      # list, non-empty
    ],
    4: [
        ("description.inhalation", True),
        ("description.skin", True),
        ("description.eye", True),
        ("description.ingestion", True),
    ],
    5: [
        ("suitable_media", True),
    ],
    6: [
        ("personal_precautions", True),
    ],
    7: [
        ("safe_handling", True),
        ("storage_conditions", True),
    ],
    8: [
        ("occupational_exposure_limits", True),  # list
        ("eye_protection", True),
        ("skin_protection", True),
    ],
    9: [
        ("safety_data", True),              # list, non-empty
    ],
    10: [
        ("chemical_stability", True),
    ],
    11: [
        ("acute_toxicity", True),
    ],
    12: [
        ("ecotox_components", True),        # list
        ("mobility_info", False),           # recommended
        ("endocrine_disrupting_info", False),  # recommended
    ],
    13: [
        ("waste_treatment", True),
    ],
    14: [
        ("land.un_number", True),
        ("land.transport_class", True),
    ],
    15: [
        ("eu_legislation", True),
        ("wgk", True),
    ],
    16: [
        ("abbreviations", True),            # list
        ("indication_of_changes", False),   # recommended
    ],
}


def _get_nested(data: dict, path: str) -> Any:
    """Resolve a dot-notation path against a dict. Returns None if not found."""
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _is_empty(value: Any) -> bool:
    """Return True if the value is considered empty/missing."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def _get_section_data(parsed_data: dict, section_num: int) -> dict:
    """Return the dict for a given section number."""
    if section_num == 16:
        # Section 16 is stored under 'other_information' at root level
        return parsed_data.get("other_information", {})
    return parsed_data.get(f"section_{section_num}", {})


def _validate_section(section_num: int, section_data: dict) -> dict:
    """
    Validate a single section.
    Returns a dict with status, completeness, missing_required, missing_recommended.
    """
    fields = SECTION_FIELDS.get(section_num, [])
    if not fields:
        return {
            "status": "pass",
            "completeness": 1.0,
            "missing_required": [],
            "missing_recommended": [],
        }

    missing_required: List[str] = []
    missing_recommended: List[str] = []
    total = len(fields)

    for field_path, is_critical in fields:
        value = _get_nested(section_data, field_path)
        if _is_empty(value):
            if is_critical:
                missing_required.append(field_path)
            else:
                missing_recommended.append(field_path)

    present = total - len(missing_required) - len(missing_recommended)
    completeness = present / total if total > 0 else 1.0

    if missing_required:
        status = "fail"
    elif missing_recommended:
        status = "warning"
    else:
        status = "pass"

    return {
        "status": status,
        "completeness": round(completeness, 4),
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
    }


def check_completeness(parsed_data: dict) -> dict:
    """
    Check if required fields are present in the parsed SDS data.

    Args:
        parsed_data: Dict returned by NewSDScomParser.parse()

    Returns:
        {
            'overall_status': 'pass' | 'warning' | 'fail',
            'overall_completeness': float,   # 0.0 – 1.0
            'sections': {
                1: {'status': ..., 'completeness': ...,
                    'missing_required': [...], 'missing_recommended': [...]},
                ...
            },
            'critical_gaps': [...],
            'warnings': [...],
            'total_fields': int,
            'present_fields': int,
            'missing_fields': int,
        }
    """
    sections_result: Dict[int, dict] = {}
    critical_gaps: List[str] = []
    warnings: List[str] = []
    total_fields = 0
    present_fields = 0

    for section_num in range(1, 17):
        section_data = _get_section_data(parsed_data, section_num)
        result = _validate_section(section_num, section_data)
        sections_result[section_num] = result

        fields = SECTION_FIELDS.get(section_num, [])
        total_fields += len(fields)
        missing = len(result["missing_required"]) + len(result["missing_recommended"])
        present_fields += len(fields) - missing

        for f in result["missing_required"]:
            critical_gaps.append(f"Section {section_num}: {f}")
        for f in result["missing_recommended"]:
            warnings.append(f"Section {section_num}: {f}")

    missing_fields = total_fields - present_fields
    overall_completeness = present_fields / total_fields if total_fields > 0 else 1.0

    if critical_gaps:
        overall_status = "fail"
    elif warnings:
        overall_status = "warning"
    else:
        overall_status = "pass"

    return {
        "overall_status": overall_status,
        "overall_completeness": round(overall_completeness, 4),
        "sections": sections_result,
        "critical_gaps": critical_gaps,
        "warnings": warnings,
        "total_fields": total_fields,
        "present_fields": present_fields,
        "missing_fields": missing_fields,
    }


def generate_gap_report(parsed_data: dict, validation_result: Optional[dict] = None) -> str:
    """
    Generate a Markdown-formatted gap report for the parsed SDS data.

    Args:
        parsed_data:       Dict returned by NewSDScomParser.parse()
        validation_result: Optional pre-computed result from check_completeness().
                           If None, check_completeness() is called automatically.

    Returns:
        Markdown string with the full gap report.
    """
    if validation_result is None:
        validation_result = check_completeness(parsed_data)

    # Header metadata
    product_name = (
        parsed_data.get("meta", {}).get("product_name")
        or parsed_data.get("section_1", {}).get("product_identifier", {}).get("trade_name")
        or "Unknown Product"
    )
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pct = round(validation_result["overall_completeness"] * 100, 1)
    status_raw = validation_result["overall_status"]
    status_icon = {"pass": "✅ PASS", "warning": "⚠️ WARNING", "fail": "❌ FAIL"}.get(status_raw, status_raw)

    total = validation_result["total_fields"]
    present = validation_result["present_fields"]
    missing = validation_result["missing_fields"]
    n_critical = len(validation_result["critical_gaps"])
    n_warnings = len(validation_result["warnings"])

    present_pct = round(present / total * 100, 1) if total else 0.0
    missing_pct = round(missing / total * 100, 1) if total else 0.0

    lines: List[str] = []

    # ── Title block ──────────────────────────────────────────────────────────
    lines.append("# SDS Gap Report")
    lines.append("")
    lines.append(f"**File**: {product_name}")
    lines.append(f"**Generated**: {timestamp}")
    lines.append(f"**Overall Completeness**: {pct}%")
    lines.append(f"**Status**: {status_icon}")
    lines.append("")

    # ── Summary ──────────────────────────────────────────────────────────────
    lines.append("## Summary")
    lines.append(f"- Total Fields: {total}")
    lines.append(f"- Present: {present} ({present_pct}%)")
    lines.append(f"- Missing: {missing} ({missing_pct}%)")
    lines.append(f"- Critical Gaps: {n_critical}")
    lines.append(f"- Warnings: {n_warnings}")
    lines.append("")

    # ── Section Details ───────────────────────────────────────────────────────
    lines.append("## Section Details")
    lines.append("")

    for section_num in range(1, 17):
        sec = validation_result["sections"].get(section_num, {})
        sec_status = sec.get("status", "pass")
        sec_pct = round(sec.get("completeness", 1.0) * 100, 1)
        sec_name = SECTION_NAMES.get(section_num, f"Section {section_num}")
        icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(sec_status, "")

        lines.append(f"### {icon} Section {section_num}: {sec_name} ({sec_pct}%)")

        missing_req = sec.get("missing_required", [])
        missing_rec = sec.get("missing_recommended", [])

        if not missing_req and not missing_rec:
            lines.append("- All required fields present.")
        else:
            for f in missing_req:
                lines.append(f"- ❌ Missing (required): {f}")
            for f in missing_rec:
                lines.append(f"- ⚠️ Missing (recommended): {f}")

        lines.append("")

    # ── Critical Gaps list ────────────────────────────────────────────────────
    if validation_result["critical_gaps"]:
        lines.append("## Critical Gaps")
        for gap in validation_result["critical_gaps"]:
            lines.append(f"- ❌ {gap}")
        lines.append("")

    # ── Warnings list ─────────────────────────────────────────────────────────
    if validation_result["warnings"]:
        lines.append("## Warnings")
        for w in validation_result["warnings"]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    return "\n".join(lines)


def validate_and_report(parsed_data: dict) -> Tuple[dict, str]:
    """
    Convenience function: validate completeness and generate a Markdown report.

    Args:
        parsed_data: Dict returned by NewSDScomParser.parse()

    Returns:
        (validation_result, markdown_report_string)
    """
    validation_result = check_completeness(parsed_data)
    report = generate_gap_report(parsed_data, validation_result)
    return validation_result, report
