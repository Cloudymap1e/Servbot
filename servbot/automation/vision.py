from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

# Lightweight "vision" helper that labels inputs and buttons using DOM geometry
# and falls back to coordinate clicks when selectors fail.

@dataclass
class LabeledNode:
    kind: str  # 'input' | 'button' | 'link'
    name: str  # semantic label, e.g., 'email', 'password', 'submit'
    selector: str
    bbox: Tuple[float, float, float, float]  # x, y, width, height


class VisionHelper:
    def __init__(self, page):
        self.page = page

    def label_elements(self) -> List[LabeledNode]:
        nodes: List[LabeledNode] = []
        # Collect inputs and buttons that are visible
        handles = self.page.query_selector_all('input, button, a[role="button"]')
        for h in handles:
            try:
                if not h.is_visible():
                    continue
                tag = (h.evaluate("el => el.tagName") or '').lower()
                typ = (h.get_attribute('type') or '').lower()
                name = (h.get_attribute('name') or '')
                placeholder = (h.get_attribute('placeholder') or '')
                aria = (h.get_attribute('aria-label') or '')
                # Try associated <label> text
                label_text = h.evaluate("""
                    el => {
                      const id = el.id;
                      if (id) {
                        const lab = document.querySelector(`label[for='${id}']`);
                        if (lab && lab.textContent) return lab.textContent.trim();
                      }
                      // nearest preceding text node
                      let p = el.previousElementSibling;
                      if (p && p.textContent && p.textContent.trim().length <= 20) return p.textContent.trim();
                      return '';
                    }
                """) or ''
                text = h.inner_text().strip() if tag != 'input' else ''
                sel = h.evaluate("""
                    el => {
                      const esc = (window.CSS && CSS.escape) ? CSS.escape : (s) => String(s).replace(/\"/g,'\\"');
                      const id = (el.id || '').trim();
                      const name = el.getAttribute('name');
                      if (id) return '#' + esc(id);
                      if (name) return '[name="' + esc(name) + '"]';
                      const tag = el.tagName.toLowerCase();
                      const type = (el.getAttribute('type') || '').toLowerCase();
                      if (tag === 'input' && type) return 'input[type="' + esc(type) + '"]';
                      return tag;
                    }
                """)
                # Fallback selector
                selector = sel if isinstance(sel, str) and sel else 'xpath=.'
                # Determine semantic name
                lowered = ' '.join([typ, name, placeholder, aria, label_text, text]).lower()
                semantic = 'unknown'
                if any(k in lowered for k in ['email', 'e-mail', 'mail']):
                    semantic = 'email'
                elif any(k in lowered for k in ['user', 'username', 'name']):
                    semantic = 'username'
                elif any(k in lowered for k in ['pass', 'password']):
                    semantic = 'password'
                elif any(k in lowered for k in ['code', 'otp', 'one-time', '验证码', '驗證碼', '校验码', '驗證', '验证']):
                    semantic = 'otp'
                elif any(k in lowered for k in ['continue', 'sign up', 'signup', 'register', 'next', 'submit']):
                    semantic = 'submit'
                kind = 'input' if tag == 'input' else 'button'
                box = h.bounding_box() or {"x": 0, "y": 0, "width": 0, "height": 0}
                nodes.append(
                    LabeledNode(kind=kind, name=semantic, selector=selector, bbox=(box['x'], box['y'], box['width'], box['height']))
                )
            except Exception:
                continue
        return nodes

    def fill_by_label(self, label: str, value: str) -> bool:
        try:
            for n in self.label_elements():
                if n.kind == 'input' and n.name == label:
                    try:
                        self.page.fill(n.selector, value)
                        return True
                    except Exception:
                        # coordinate fallback
                        x, y, w, h = n.bbox
                        self.page.mouse.click(x + w/2, y + h/2)
                        self.page.keyboard.type(value)
                        return True
            return False
        except Exception:
            return False

    def click_submit(self) -> bool:
        try:
            # Prefer semantic submit
            nodes = self.label_elements()
            submits = [n for n in nodes if n.kind == 'button' and n.name == 'submit'] or [n for n in nodes if n.kind == 'button']
            for n in submits:
                try:
                    self.page.click(n.selector)
                    return True
                except Exception:
                    x, y, w, h = n.bbox
                    self.page.mouse.click(x + w/2, y + h/2)
                    return True
            return False
        except Exception:
            return False
