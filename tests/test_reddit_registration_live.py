from __future__ import annotations

"""
Live Reddit registration test using Playwright, proxy, and network metering.

Enable with environment variable:
  - SERVBOT_RUN_LIVE=1 to allow live tests to run
  - Optional: SERVBOT_RUN_REDDIT=1 (for selective run)
  - Optional: SERVBOT_FLASHMAIL_CARD=<card> or SERVBOT_FLASHMAIL_CARD_ALIAS=<alias>

The test will:
  1) Acquire Flashmail account (new) if a card is available
  2) Acquire a proxy from the proxies DB
  3) Run GenericEmailCodeFlow against Reddit with metering enabled
  4) Print a summary including network meter stats and artifacts
"""

import json
import os
from pathlib import Path

import pytest

from servbot.automation.flows.generic import GenericEmailCodeFlow, FlowConfig
from servbot.automation.engine import BrowserBot
from servbot.core.models import EmailAccount
from servbot.data.database import ensure_db, upsert_account
from servbot.proxy.bridge import get_playwright_proxy_from_db
from servbot.proxy.database import ProxyDatabase
from servbot.proxy.models import ProxyEndpoint
from servbot.core.models import EmailAccount
from servbot.automation.http.agent import BrowserLikeSession
from servbot.data.database import get_accounts


def _load_reddit_flow_config() -> FlowConfig:
    cfg_path = Path(__file__).parent.parent / "flows" / "reddit.json"
    data = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    return FlowConfig(
        email_input=data.get("email_input", "input[type=email]"),
        email_start_button=data.get("email_start_button"),
        username_input=data.get("username_input"),
        password_input=data.get("password_input"),
        password_confirm_input=data.get("password_confirm_input"),
        accept_cookies_button=data.get("accept_cookies_button"),
        submit_button=data.get("submit_button", "button[type=submit]"),
        otp_input=data.get("otp_input"),
        otp_inputs=data.get("otp_inputs"),
        otp_submit_button=data.get("otp_submit_button"),
        success_selector=data.get("success_selector"),
        pre_submit_pause_ms=int(data.get("pre_submit_pause_ms", 1200)),
        post_submit_wait_ms=int(data.get("post_submit_wait_ms", 6000)),
    )


def _provision_flashmail_account() -> EmailAccount | None:
    # Try explicit env card
    card = os.environ.get("SERVBOT_FLASHMAIL_CARD")
    client = None
    if card:
        from servbot.clients.flashmail import FlashmailClient

        client = FlashmailClient(card)
    else:
        # Try alias via secure store
        alias = os.environ.get("SERVBOT_FLASHMAIL_CARD_ALIAS")
        if alias:
            from servbot.flashmail_cards import get_client_by_alias

            client = get_client_by_alias(alias)
        else:
            # Try to pick any configured card with available balance
            try:
                from servbot.flashmail_cards import pick_card, get_client_by_alias

                picked = pick_card(min_required_credits=1)
                if picked:
                    client = get_client_by_alias(picked)
            except Exception:
                client = None

    if not client:
        return None

    accounts = client.fetch_accounts(quantity=1, account_type="outlook")
    if not accounts:
        return None
    acc = accounts[0]
    # Persist to DB
    upsert_account(
        email=acc.email,
        password=acc.password,
        type=acc.account_type,
        source=acc.source,
        card=acc.card,
        refresh_token=acc.refresh_token,
        client_id=acc.client_id,
    )
    return acc


def _pick_existing_account() -> EmailAccount | None:
    try:
        rows = get_accounts()
    except Exception:
        rows = []
    if not rows:
        return None
    row = rows[0]
    return EmailAccount(
        email=row.get("email", ""),
        password=row.get("password", ""),
        account_type=row.get("type", "other") or "other",
        source=row.get("source", "manual") or "manual",
        imap_server=row.get("imap_server"),
        card=row.get("card"),
        refresh_token=row.get("refresh_token"),
        client_id=row.get("client_id"),
    )


def _iter_proxies(max_items: int = 15, region_filter: str | None = "SG"):
    """Yield Playwright proxy dicts from DB: working first, then all active, de-duplicated."""
    seen = set()
    db = ProxyDatabase("data/proxies.db")
    try:
        endpoints = db.get_working_proxies()
        if not endpoints:
            endpoints = []
        # Append actives not already in list
        all_active = db.get_all_proxies(active_only=True)
        merged = endpoints + [e for e in all_active if e not in endpoints]
        for ep in merged[: max_items * 6]:  # cap raw list, allow extra for filtering
            key = (ep.host, ep.port, ep.username or "")
            if key in seen:
                continue
            # region filter
            if region_filter:
                reg = (getattr(ep, 'region', None) or '').upper()
                pwd = (ep.password or '')
                if reg != region_filter.upper() and f"_country-{region_filter.upper()}_" not in pwd:
                    continue
            seen.add(key)
            yield ep
            if len(seen) >= max_items:
                break
    finally:
        db.close()


def _preflight_proxy(ep, timeout: int = 10) -> bool:
    """Quick HTTP GET via requests-style session to check basic reachability."""
    try:
        sess = BrowserLikeSession(proxies=ep.as_requests_proxies(), timeout=timeout)
        try:
            status, _text, _ctype = sess.get_text("https://www.reddit.com/register")
            return status < 400
        finally:
            sess.close()
    except Exception:
        return False


def _load_proxifier_sessions() -> list[str]:
    sessions: set[str] = set()
    for fname in (
        Path("data/proxy_ipcheck_proxifier-current.json"),
        Path("data/proxy_ipcheck_proxifier-current-headers.json"),
    ):
        try:
            data = json.loads(Path(fname).read_text(encoding="utf-8"))
            for r in data.get("results", []):
                s = r.get("session")
                if s:
                    sessions.add(str(s))
        except Exception:
            pass
    # Return deterministic order
    return list(sorted(sessions))


def _augment_with_mooproxy_sessions(base_ep: ProxyEndpoint, limit: int = 30) -> list[ProxyEndpoint]:
    out: list[ProxyEndpoint] = []
    if not (base_ep and base_ep.password and base_ep.username and base_ep.host and base_ep.port):
        return out
    pw = base_ep.password
    if "_session-" not in pw:
        return out
    prefix = pw.split("_session-", 1)[0] + "_session-"
    for sid in _load_proxifier_sessions():
        new_ep = ProxyEndpoint(
            scheme=base_ep.scheme,
            host=base_ep.host,
            port=base_ep.port,
            username=base_ep.username,
            password=prefix + sid,
            provider=base_ep.provider,
            session=sid,
            proxy_type=base_ep.proxy_type,
            ip_version=base_ep.ip_version,
            rotation_type=base_ep.rotation_type,
            region=base_ep.region,
        )
        out.append(new_ep)
        if len(out) >= limit:
            break
    return out


@pytest.mark.live
@pytest.mark.integration
def test_reddit_registration_end_to_end(tmp_path):
    allow = os.environ.get("SERVBOT_RUN_REDDIT") in {"1", "true", "yes"} or Path("RUN_REDDIT").exists() or Path(__file__).parent.joinpath("RUN_REDDIT").exists()
    if not allow:
        pytest.skip("SERVBOT_RUN_REDDIT not enabled")

    ensure_db()

    # Try proxies until one loads reddit register page
    max_attempts = int(os.environ.get("SERVBOT_MAX_PROXY_ATTEMPTS", "6"))
    candidates = list(_iter_proxies(max_items=max_attempts * 3, region_filter="SG"))
    # If a MooProxy endpoint present, permute with known good sessions from headers file
    augmented: list[ProxyEndpoint] = []
    for ep in candidates:
        if ep.provider and 'mooproxy' in ep.provider:
            augmented.extend(_augment_with_mooproxy_sessions(ep, limit=max_attempts))
    if augmented:
        # Prepend augmented sessions for early trials
        candidates = augmented + candidates
    if not candidates:
        pytest.skip("No proxy available in proxies DB")

    acc = _provision_flashmail_account()
    if not acc:
        acc = _pick_existing_account()
    if not acc:
        pytest.skip("No account available: Flashmail not configured and no DB accounts")

    cfg = _load_reddit_flow_config()
    flow = GenericEmailCodeFlow(
        service_name="Reddit",
        entry_url="https://www.reddit.com/register",
        config=cfg,
    )

    last_result = None
    used_proxy = None
    attempts = 0
    for ep in candidates:
        attempts += 1
        pw_proxy = ep.as_playwright_proxy()
        # Preflight reachability
        if not _preflight_proxy(ep, timeout=8):
            print(f"[skip] proxy preflight failed: {ep.host}:{ep.port}")
            continue
        print(f"[try] proxy {attempts}: {ep.provider or ''} {ep.host}:{ep.port}")
        bot = BrowserBot(
            headless=False,  # headful per site behavior
            proxy=pw_proxy,
            traffic_profile="minimal",  # lighter blocking
            block_third_party=False,     # allow resources to reduce blocks
            measure_network=True,
            default_timeout=20,          # reduced per-step timeout
        )
        result = bot.run_flow(flow=flow, email_account=acc, timeout_sec=120, prefer_link=True)
        last_result = result
        used_proxy = pw_proxy
        # Consider loaded if any artifact or cookies present
        if result.cookies_json:
            break
        if attempts >= max_attempts:
            break

    # Report
    print("\n===== Reddit Registration Result =====")
    if last_result:
        print(f"Success: {last_result.success}")
        print(f"Error: {last_result.error}")
        print(f"Artifacts: {len(last_result.artifacts or [])}")
        print(f"Debug dir: {last_result.debug_dir}")
        net_files = [p for p in (last_result.artifacts or []) if isinstance(p, str) and p.endswith(".json") and "_net_" in p]
        if net_files:
            net_path = net_files[-1]
            try:
                data = json.loads(Path(net_path).read_text(encoding="utf-8"))
                totals = data.get("totals", {})
                blocked = data.get("blocked", {})
                profile = data.get("profile", {})
                print("\n===== Network Meter Summary =====")
                print(f"Traffic profile: {profile.get('traffic_profile')}")
                print(f"Allowed domains: {profile.get('allowed_domains')}")
                print(f"Total requests: {totals.get('requests')}")
                print(f"Encoded bytes: {totals.get('encoded_bytes')}")
                print(f"Blocked: {blocked}")
            except Exception as e:
                print(f"Failed to read network meter JSON: {e}")
        else:
            print("No network meter artifact found")

    assert last_result and last_result.debug_dir and Path(last_result.debug_dir).exists(), "Debug directory should exist"
    assert used_proxy is not None


