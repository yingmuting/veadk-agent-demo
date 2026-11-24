"""Tool A: normalize a single alert into a stable JSON contract."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Final

SUCCESS_FIELDS: Final[tuple[str, ...]] = (
    "alert_id",
    "title",
    "severity",
    "status",
    "source",
    "affected_service",
    "event_time",
    "description",
    "raw_text",
    "confidence",
    "notes",
)

SEVERITY_VALUES: Final[frozenset[str]] = frozenset(
    {"critical", "high", "medium", "low", "info"}
)
STATUS_VALUES: Final[frozenset[str]] = frozenset(
    {"active", "acknowledged", "resolved"}
)

ALIASES: Final[Mapping[str, tuple[str, ...]]] = {
    "alert_id": ("alert_id", "alertid", "alertId", "id"),
    "title": ("title", "summary", "alert_name", "告警标题"),
    "severity": ("severity", "level", "priority", "告警等级"),
    "status": ("status", "state", "告警状态"),
    "source": ("source", "source_system", "system", "来源", "告警来源"),
    "affected_service": (
        "affected_service",
        "service",
        "component",
        "service_name",
        "服务",
        "影响服务",
    ),
    "event_time": (
        "event_time",
        "time",
        "timestamp",
        "eventTime",
        "时间",
        "告警时间",
    ),
    "description": (
        "description",
        "message",
        "content",
        "detail",
        "描述",
        "详情",
    ),
}

# First-round common aliases. Keep mappings conservative until the open
# free-text coverage sample set is confirmed.
ENUM_ALIASES: Final[Mapping[str, str]] = {
    "严重": "critical",
    "紧急": "critical",
    "crit": "critical",
    "警告": "medium",
    "warning": "medium",
    "已恢复": "resolved",
    "恢复": "resolved",
    "已确认": "acknowledged",
    "确认": "acknowledged",
    "触发": "active",
    "firing": "active",
}


class _UnsupportedInputError(ValueError):
    """Internal sentinel for converting bad input into a structured error."""


def _error(error_code: str, error_message: str) -> str:
    return json.dumps(
        {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _empty_data(raw_text: str) -> dict[str, Any]:
    data: dict[str, Any] = {field: None for field in SUCCESS_FIELDS}
    data["raw_text"] = raw_text
    data["confidence"] = 0.0
    data["notes"] = []
    return data


def _parse_json_object(alert_input: str) -> tuple[dict[str, Any], bool]:
    """Return an alert object and whether the input was parsed as JSON."""
    stripped = alert_input.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return {}, False
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return {}, False
    if not isinstance(parsed, Mapping):
        return {}, False
    return dict(parsed), True


def _first_value(data: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in data and data[name] is not None:
            return data[name]
    return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _normalize_enum(
    value: Any,
    allowed: frozenset[str],
    notes: list[str],
    label: str,
) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in allowed:
        return normalized

    mapped = ENUM_ALIASES.get(normalized)
    if mapped in allowed:
        notes.append(f"{label} 使用别名映射：{value} -> {mapped}")
        return mapped

    notes.append(f"{label} 值无法映射到约定枚举，已置为 null：{value}")
    return None


def _normalize_object(data: Mapping[str, Any], raw_text: str) -> str:
    notes: list[str] = []
    result = _empty_data(raw_text)

    for target, names in ALIASES.items():
        value = _first_value(data, names)
        if target == "severity":
            result[target] = _normalize_enum(
                value, SEVERITY_VALUES, notes, "severity"
            )
        elif target == "status":
            result[target] = _normalize_enum(
                value, STATUS_VALUES, notes, "status"
            )
        else:
            result[target] = _as_text(value)

        used_alias = value is not None and next(
            (name for name in names if name != target and name in data),
            None,
        )
        if used_alias:
            notes.append(f"{target} 通过别名 {used_alias} 映射")

    known_fields = {name for names in ALIASES.values() for name in names}
    unrecognized = [key for key in data if key not in known_fields]
    if unrecognized:
        notes.append("输入中存在未纳入通用契约的字段：" + ", ".join(unrecognized))

    recognized_count = sum(
        result[field] is not None for field in SUCCESS_FIELDS[:8]
    )
    result["confidence"] = min(1.0, round(0.2 + recognized_count / 8 * 0.8, 2))
    result["notes"] = notes
    return json.dumps(
        {"success": True, "data": result},
        ensure_ascii=False,
        separators=(",", ":"),
    )


# Conservative labeled patterns for the first free-text implementation.
_LABEL_PATTERNS: Final[Mapping[str, re.Pattern[str]]] = {
    "alert_id": re.compile(
        r"(?:告警ID|告警 ID|alert[_\s-]?id)\s*[:：=]\s*([^\s，,；;]+)",
        re.I,
    ),
    "title": re.compile(
        r"(?:告警标题|标题|title)\s*[:：=]\s*([^，,。；;\n]+)",
        re.I,
    ),
    "source": re.compile(
        r"(?:告警来源|来源|source)\s*[:：=]\s*([^，,。；;\n]+)",
        re.I,
    ),
    "affected_service": re.compile(
        r"(?:影响服务|服务|service)\s*[:：=]\s*([^\s，,。；;]+)",
        re.I,
    ),
    "event_time": re.compile(
        r"(?:告警时间|时间|time)\s*[:：=]\s*([^，,。；;\n]+)",
        re.I,
    ),
    "description": re.compile(
        r"(?:告警描述|描述|详情|description|message)\s*[:：=]\s*([^，,。；;\n]+)",
        re.I,
    ),
}
_TIME_PATTERN = re.compile(
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"(?:[ T]\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?Z?)?"
)
_SEVERITY_TEXT: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"严重|critical|p0", re.I), "critical"),
    (re.compile(r"高|high|p1", re.I), "high"),
    (re.compile(r"中|medium|warning|p2", re.I), "medium"),
    (re.compile(r"低|low|p3", re.I), "low"),
    (re.compile(r"提示|informational|info", re.I), "info"),
)
_STATUS_TEXT: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"已恢复|恢复|resolved"), "resolved"),
    (re.compile(r"已确认|确认|acknowledged"), "acknowledged"),
    (re.compile(r"触发|告警|active|firing", re.I), "active"),
)


def _normalize_free_text(text: str) -> str:
    notes: list[str] = []
    result = _empty_data(text)

    for field, pattern in _LABEL_PATTERNS.items():
        match = pattern.search(text)
        if match:
            result[field] = match.group(1).strip()

    for pattern, value in _SEVERITY_TEXT:
        if pattern.search(text):
            result["severity"] = value
            notes.append(f"severity 从文本关键词映射：{value}")
            break

    for pattern, value in _STATUS_TEXT:
        if pattern.search(text):
            result["status"] = value
            notes.append(f"status 从文本关键词映射：{value}")
            break

    if result["event_time"] is None:
        time_match = _TIME_PATTERN.search(text)
        if time_match:
            result["event_time"] = time_match.group(0)

    if result["description"] is None and result["title"] is None:
        result["description"] = text.strip()
        notes.append("description 使用原始告警文本，尚未抽取更精简描述")

    if result["title"] is None:
        notes.append("title 未识别，已置为 null")

    recognized_count = sum(
        result[field] is not None for field in SUCCESS_FIELDS[:8]
    )
    result["confidence"] = min(1.0, round(0.2 + recognized_count / 8 * 0.8, 2))
    result["notes"] = notes
    return json.dumps(
        {"success": True, "data": result},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def format_alert_info(alert_input: Any) -> str:
    """Normalize one alert and return a JSON string.

    The tool is stateless and performs no external calls. Missing values stay
    ``null``; unsupported input is converted to the structured error contract.
    """
    try:
        if alert_input is None:
            return _error("EMPTY_INPUT", "告警输入不能为空")
        if isinstance(alert_input, str) and not alert_input.strip():
            return _error("EMPTY_INPUT", "告警输入不能为空")
        if isinstance(alert_input, (list, tuple)):
            return _error(
                "MULTIPLE_ALERTS",
                "Tool A 仅支持单条告警，不支持数组或多条告警",
            )
        if not isinstance(alert_input, (str, Mapping)):
            return _error(
                "UNSUPPORTED_INPUT",
                "告警输入仅支持自由文本、JSON 字符串或 JSON 对象",
            )

        if isinstance(alert_input, Mapping):
            raw_text = json.dumps(
                alert_input,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            return _normalize_object(dict(alert_input), raw_text)

        text = str(alert_input).strip()
        data, parsed_json = _parse_json_object(text)
        if parsed_json:
            return _normalize_object(data, text)
        return _normalize_free_text(text)
    except Exception:
        return _error(
            "UNSUPPORTED_INPUT",
            "告警输入无法处理，请提供单条自由文本或 JSON 对象",
        )
