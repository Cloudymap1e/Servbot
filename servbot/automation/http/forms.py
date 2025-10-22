from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


_INPUT_RE = re.compile(r"<input\s+([^>]+)>", re.I)
_TEXTAREA_RE = re.compile(r"<textarea\s+([^>]*)>(.*?)</textarea>", re.I | re.S)
_SELECT_RE = re.compile(r"<select\s+([^>]*)>(.*?)</select>", re.I | re.S)
_FORM_RE = re.compile(r"<form\s+([^>]*)>(.*?)</form>", re.I | re.S)


def _attrs_to_dict(attrs: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in re.finditer(r"(\w+)(?:\s*=\s*\"([^\"]*)\"|\s*=\s*'([^']*)'|\s*=\s*([^\s>]+))?", attrs):
        key = m.group(1).lower()
        val = m.group(2) or m.group(3) or m.group(4) or ""
        out[key] = html.unescape(val)
    return out


@dataclass
class ParsedForm:
    action: str
    method: str = "post"
    inputs: Dict[str, str] = field(default_factory=dict)
    hidden: Dict[str, str] = field(default_factory=dict)

    def fill(self, values: Dict[str, str]) -> Dict[str, str]:
        data = dict(self.hidden)
        for k, v in values.items():
            if v is None:
                continue
            data[k] = v
        # include known inputs set to defaults if not provided
        for k, v in self.inputs.items():
            data.setdefault(k, v)
        return data


class FormParser:
    """Minimal HTML form parser sufficient for common signup pages.

    Not a full HTML parser; relies on regex for speed and zero deps.
    """

    @staticmethod
    def find_first_form(html_text: str) -> Optional[ParsedForm]:
        m = _FORM_RE.search(html_text or "")
        if not m:
            return None
        form_attrs = _attrs_to_dict(m.group(1) or "")
        form_inner = m.group(2) or ""
        action = form_attrs.get("action", "") or ""
        method = (form_attrs.get("method", "post") or "post").lower()

        inputs: Dict[str, str] = {}
        hidden: Dict[str, str] = {}

        # inputs
        for im in _INPUT_RE.finditer(form_inner):
            attrs = _attrs_to_dict(im.group(1) or "")
            name = attrs.get("name") or ""
            if not name:
                continue
            typ = (attrs.get("type", "text") or "text").lower()
            value = attrs.get("value", "")
            if typ in ("hidden",):
                hidden[name] = value
            else:
                inputs[name] = value

        # textareas
        for tm in _TEXTAREA_RE.finditer(form_inner):
            attrs = _attrs_to_dict(tm.group(1) or "")
            name = attrs.get("name") or ""
            if not name:
                continue
            value = html.unescape(tm.group(2) or "")
            inputs[name] = value

        # selects: choose first option if any
        for sm in _SELECT_RE.finditer(form_inner):
            attrs = _attrs_to_dict(sm.group(1) or "")
            name = attrs.get("name") or ""
            if not name:
                continue
            options_html = sm.group(2) or ""
            opt = re.search(r"<option[^>]*value=\"([^\"]*)\"[^>]*>", options_html, re.I)
            if not opt:
                opt = re.search(r"<option[^>]*>([^<]*)</option>", options_html, re.I)
            value = html.unescape(opt.group(1)) if opt else ""
            inputs[name] = value

        return ParsedForm(action=action, method=method, inputs=inputs, hidden=hidden)


