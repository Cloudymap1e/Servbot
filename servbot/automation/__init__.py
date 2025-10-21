"""Browser automation package for servbot.

This package provides comprehensive browser automation capabilities using Playwright:

Modules:
    engine: Core BrowserBot orchestration and ActionHelper utilities
    vision: Vision-assisted form filling with fallback mechanisms
    netmeter: Network traffic metering via Chrome DevTools Protocol
    flows: Registration flow implementations (GenericEmailCodeFlow)

Key Classes:
    BrowserBot: Orchestrates Playwright browser contexts with anti-detection
    RegistrationFlow: Abstract base for custom registration flows
    RegistrationResult: Dataclass for flow execution results
    ActionHelper: Debug-friendly actions with screenshots and highlighting
    VisionHelper: Semantic form detection and coordinate-based fallback
    NetworkMeter: Real-time bandwidth tracking

Features:
    - Anti-detection stealth measures (webdriver masking, realistic headers)
    - Traffic optimization profiles (off, minimal, ultra)
    - Third-party domain blocking with allowlists
    - Network usage metering and cost tracking
    - Debug artifacts with visual element highlighting
    - Session persistence (cookies, storage state, profiles)
    - Automatic headless/headed fallback on failures

Usage:
    from servbot import register_service_account
    
    result = register_service_account(
        service="Reddit",
        website_url="https://www.reddit.com/register",
        provision_new=True,
        traffic_profile="minimal",
        measure_network=True
    )

See Also:
    docs/BROWSER_AUTOMATION.md: Comprehensive automation guide
    docs/NETWORK_METERING.md: Traffic measurement and optimization
"""
