import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from servbot.parsers.code_parser import (
    parse_verification_codes,
    parse_verification_links,
)
from servbot.parsers.service_parser import (
    identify_service,
    canonical_service_name,
    services_equal,
)
from servbot.parsers.email_parser import html_to_text

class TestParsers(unittest.TestCase):

    def test_html_to_text(self):
        html = "<html><head><style>p{color:red}</style></head><body><p>Hello &nbsp; <b>World</b></p><script>alert(1)</script></body></html>"
        expected = "Hello World"
        self.assertEqual(html_to_text(html).strip(), expected)

    def test_parse_verification_codes(self):
        # Basic cases
        self.assertEqual(parse_verification_codes("Your code is 123456.", use_ai_fallback=False), ["123456"])
        self.assertEqual(parse_verification_codes("G-987654 is your Google code", use_ai_fallback=False), ["987654"])
        self.assertEqual(parse_verification_codes("Use code: ABCDE123", use_ai_fallback=False), ["ABCDE123"])
        self.assertEqual(parse_verification_codes("Security code: 555-666", use_ai_fallback=False), []) # Not a code
        self.assertEqual(parse_verification_codes("Your OTP is 888777", use_ai_fallback=False), ["888777"])
        
        # Multiple codes
        text = "Code 1 is 111111. Code 2 is 222222. 111111 is a repeat."
        self.assertEqual(parse_verification_codes(text, use_ai_fallback=False), ["111111", "222222"])

        # No code
        self.assertEqual(parse_verification_codes("Hello world, how are you?", use_ai_fallback=False), [])

    def test_parse_verification_links(self):
        text = '''
            Click here to verify: https://service.com/verify?token=123
            Or go to https://service.com/login
            Please do not unsubscribe: https://service.com/unsubscribe
        '''
        links = parse_verification_links(text)
        self.assertEqual(len(links), 2)
        self.assertIn("https://service.com/verify?token=123", links[0])
        self.assertIn("https://service.com/login", links[1])

    def test_identify_service(self):
        # From domain
        self.assertEqual(identify_service("noreply@github.com", "", "", use_ai_fallback=False), "GitHub")
        self.assertEqual(identify_service("security@account.google.com", "", "", use_ai_fallback=False), "Google")
        
        # From subject
        self.assertEqual(identify_service("test@test.com", "Your Amazon verification code", "", use_ai_fallback=False), "Amazon")
        
        # From body
        self.assertEqual(identify_service("test@test.com", "", "Welcome to Stripe!", use_ai_fallback=False), "Stripe")

        # Unknown
        self.assertEqual(identify_service("foo@bar.com", "baz", "qux", use_ai_fallback=False), "Bar") # Capitalized root

    def test_canonical_service_name(self):
        self.assertEqual(canonical_service_name("google mail"), "Gmail")
        self.assertEqual(canonical_service_name("  GitHub "), "GitHub")
        self.assertEqual(canonical_service_name("aws"), "AWS")
        self.assertEqual(canonical_service_name("My Custom Service"), "My Custom Service")

    def test_services_equal(self):
        self.assertTrue(services_equal("Google", "google"))
        self.assertTrue(services_equal("Office 365", "Microsoft"))
        self.assertFalse(services_equal("Google", "GitHub"))

if __name__ == "__main__":
    unittest.main()