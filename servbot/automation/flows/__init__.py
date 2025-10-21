"""Registration flow implementations for browser automation.

This package contains concrete implementations of RegistrationFlow for various
website signup patterns.

Modules:
    generic: GenericEmailCodeFlow for standard email+OTP registration

Available Flows:
    GenericEmailCodeFlow: Configurable flow for email/username/password forms
        with OTP verification support. Handles:
        - Email input with optional username/password
        - Form submission
        - Verification code/link fetching via Microsoft Graph
        - OTP submission (single input or digit-by-digit)
        - Success detection
        - Vision-assisted fallback when selectors fail

Configuration:
    Flows are configured via FlowConfig dataclass with CSS selectors:
    
    from servbot.automation.flows.generic import FlowConfig
    
    config = FlowConfig(
        email_input="input[type=email]",
        submit_button="button[type=submit]",
        otp_input="input[name=otp]",
        success_selector=".dashboard"
    )

Custom Flows:
    Extend RegistrationFlow to implement custom registration patterns:
    
    from servbot.automation.engine import RegistrationFlow, RegistrationResult
    
    class MyCustomFlow(RegistrationFlow):
        service_name = "MyService"
        entry_url = "https://myservice.com/signup"
        
        def perform_registration(self, page, actions, email_account, 
                                fetch_verification, timeout_sec, prefer_link):
            # Implementation here
            return RegistrationResult(...)

See Also:
    docs/BROWSER_AUTOMATION.md: Complete automation documentation
    automation.engine: Core engine and base classes
"""
