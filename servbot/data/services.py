"""
Service catalog and aliases for email-based verification code detection.

Exposes:
- ServiceIndicators: typing alias
- compile_top_services(): returns the service indicator mapping
- SERVICES: compiled service indicator mapping
- ALIASES: common service aliases
"""
from __future__ import annotations

from typing import Dict, Sequence

ServiceIndicators = Dict[str, Dict[str, Sequence[str]]]


def compile_top_services() -> ServiceIndicators:
    services: ServiceIndicators = {
        # Identity/Email providers
        "Google": {"from_domains": ["google.com"], "subject_keywords": ["google verification", "g-"]},
        "Gmail": {"from_domains": ["gmail.com"], "subject_keywords": ["gmail verification"]},
        "Microsoft": {"from_domains": ["microsoft.com", "accountprotection.microsoft.com"], "subject_keywords": ["microsoft account", "security code"]},
        "Outlook": {"from_domains": ["outlook.com", "live.com", "hotmail.com"], "subject_keywords": ["outlook verification"]},
        "Yahoo": {"from_domains": ["yahoo.com"], "subject_keywords": ["yahoo verification"]},
        "Apple": {"from_domains": ["apple.com", "appleid.apple.com"], "subject_keywords": ["apple id", "apple verification"]},
        "Proton": {"from_domains": ["proton.me", "protonmail.com"], "subject_keywords": ["proton verification"]},
        "Fastmail": {"from_domains": ["fastmail.com"], "subject_keywords": ["fastmail verification"]},
        "AOL": {"from_domains": ["aol.com"], "subject_keywords": ["aol verification"]},

        # Social/Comms
        "Facebook": {"from_domains": ["facebookmail.com", "facebook.com"], "subject_keywords": ["facebook confirmation", "facebook code"]},
        "Instagram": {"from_domains": ["instagram.com"], "subject_keywords": ["instagram code", "confirm your account"]},
        "WhatsApp": {"from_domains": ["support.whatsapp.com", "whatsapp.com"], "subject_keywords": ["whatsapp code"]},
        "Telegram": {"from_domains": ["telegram.org"], "subject_keywords": ["telegram code"]},
        "Signal": {"from_domains": ["signal.org"], "subject_keywords": ["signal verification"]},
        "Snapchat": {"from_domains": ["snapchat.com"], "subject_keywords": ["snapchat code"]},
        "TikTok": {"from_domains": ["tiktok.com"], "subject_keywords": ["tiktok code", "tiktok verification"]},
        "X": {"from_domains": ["x.com", "twitter.com"], "subject_keywords": ["twitter verification", "x verification"]},
        "Reddit": {"from_domains": ["reddit.com"], "subject_keywords": ["reddit verification"]},
        "Pinterest": {"from_domains": ["pinterest.com"], "subject_keywords": ["pinterest code"]},
        "Discord": {"from_domains": ["discord.com", "discordapp.com"], "subject_keywords": ["discord verification", "discord code"]},
        "Slack": {"from_domains": ["slack.com"], "subject_keywords": ["slack code", "sign-in code"]},
        "Zoom": {"from_domains": ["zoom.us"], "subject_keywords": ["zoom verification"]},
        "LinkedIn": {"from_domains": ["linkedin.com"], "subject_keywords": ["linkedin verification"]},
        "WeChat": {"from_domains": ["wechat.com", "tencent.com"], "subject_keywords": ["wechat code"]},

        # Developer platforms
        "GitHub": {"from_domains": ["github.com"], "subject_keywords": ["github authentication", "github verification"]},
        "GitLab": {"from_domains": ["gitlab.com"], "subject_keywords": ["gitlab verification"]},
        "Bitbucket": {"from_domains": ["bitbucket.org"], "subject_keywords": ["bitbucket verification"]},
        "Atlassian": {"from_domains": ["atlassian.com"], "subject_keywords": ["atlassian verification", "jira code", "confluence code"]},
        "Stack Overflow": {"from_domains": ["stackoverflow.email", "stackoverflow.com"], "subject_keywords": ["stack overflow code"]},
        "HashiCorp": {"from_domains": ["hashicorp.com"], "subject_keywords": ["hashicorp verification"]},
        "Docker": {"from_domains": ["docker.com"], "subject_keywords": ["docker verification"]},

        # Cloud/Infra
        "AWS": {"from_domains": ["aws.amazon.com", "amazon.com"], "subject_keywords": ["aws verification", "aws authentication"]},
        "Azure": {"from_domains": ["azure.com", "microsoft.com"], "subject_keywords": ["azure verification"]},
        "Google Cloud": {"from_domains": ["cloud.google.com", "google.com"], "subject_keywords": ["google cloud verification"]},
        "Cloudflare": {"from_domains": ["cloudflare.com"], "subject_keywords": ["cloudflare code", "zero trust code"]},
        "DigitalOcean": {"from_domains": ["digitalocean.com"], "subject_keywords": ["digitalocean code"]},
        "Heroku": {"from_domains": ["heroku.com"], "subject_keywords": ["heroku verification"]},
        "Netlify": {"from_domains": ["netlify.com"], "subject_keywords": ["netlify verification"]},
        "Vercel": {"from_domains": ["vercel.com"], "subject_keywords": ["vercel verification"]},
        "Linode": {"from_domains": ["linode.com"], "subject_keywords": ["linode verification"]},

        # Payments/Finance
        "PayPal": {"from_domains": ["paypal.com"], "subject_keywords": ["paypal code", "security code"]},
        "Stripe": {"from_domains": ["stripe.com"], "subject_keywords": ["stripe verification"], "body_keywords": ["stripe"]},
        "Square": {"from_domains": ["squareup.com", "square.com"], "subject_keywords": ["square verification", "cash app"]},
        "Cash App": {"from_domains": ["cash.app", "square.com"], "subject_keywords": ["cash app code"]},
        "Venmo": {"from_domains": ["venmo.com"], "subject_keywords": ["venmo code"]},
        "Zelle": {"from_domains": ["zellepay.com"], "subject_keywords": ["zelle code"]},
        "Wise": {"from_domains": ["wise.com", "transferwise.com"], "subject_keywords": ["wise code"]},
        "Revolut": {"from_domains": ["revolut.com"], "subject_keywords": ["revolut code"]},
        "Payoneer": {"from_domains": ["payoneer.com"], "subject_keywords": ["payoneer code"]},
        "Plaid": {"from_domains": ["plaid.com"], "subject_keywords": ["plaid verification"]},

        # Crypto
        "Coinbase": {"from_domains": ["coinbase.com"], "subject_keywords": ["coinbase code"]},
        "Binance": {"from_domains": ["binance.com"], "subject_keywords": ["binance code"]},
        "Kraken": {"from_domains": ["kraken.com"], "subject_keywords": ["kraken code"]},
        "Gemini": {"from_domains": ["gemini.com"], "subject_keywords": ["gemini code"]},
        "Bitfinex": {"from_domains": ["bitfinex.com"], "subject_keywords": ["bitfinex code"]},
        "Bybit": {"from_domains": ["bybit.com"], "subject_keywords": ["bybit code"]},
        
        # Commerce/Marketplaces
        "Amazon": {"from_domains": ["amazon.com", "amazon.ca", "amazon.co.uk"], "subject_keywords": ["amazon verification", "otp"]},
        "eBay": {"from_domains": ["ebay.com"], "subject_keywords": ["ebay code"]},
        "Etsy": {"from_domains": ["etsy.com"], "subject_keywords": ["etsy code"]},
        "Shopify": {"from_domains": ["shopify.com"], "subject_keywords": ["shopify code"]},
        "Walmart": {"from_domains": ["walmart.com"], "subject_keywords": ["walmart code"]},
        "Costco": {"from_domains": ["costco.com"], "subject_keywords": ["costco code"]},
        "Target": {"from_domains": ["target.com"], "subject_keywords": ["target code"]},
        "Best Buy": {"from_domains": ["bestbuy.com"], "subject_keywords": ["best buy code"]},
        "AliExpress": {"from_domains": ["aliexpress.com"], "subject_keywords": ["aliexpress code"]},
        "JD.com": {"from_domains": ["jd.com"], "subject_keywords": ["jd.com code"]},

        # Streaming/Media
        "Netflix": {"from_domains": ["netflix.com"], "subject_keywords": ["netflix code"]},
        "Hulu": {"from_domains": ["hulu.com"], "subject_keywords": ["hulu code"]},
        "Disney+": {"from_domains": ["disneyplus.com", "disney.com"], "subject_keywords": ["disney+ code", "disney code"]},
        "HBO Max": {"from_domains": ["hbomax.com", "max.com"], "subject_keywords": ["max code", "hbo code"]},
        "YouTube": {"from_domains": ["youtube.com", "google.com"], "subject_keywords": ["youtube verification"]},
        "Spotify": {"from_domains": ["spotify.com"], "subject_keywords": ["spotify code"]},
        "Twitch": {"from_domains": ["twitch.tv"], "subject_keywords": ["twitch code"]},
        "Apple Music": {"from_domains": ["apple.com"], "subject_keywords": ["apple music code"]},

        # Gaming
        "Steam": {"from_domains": ["steampowered.com", "steamcommunity.com"], "subject_keywords": ["steam guard", "steam code"]},
        "Epic Games": {"from_domains": ["epicgames.com"], "subject_keywords": ["epic games code"]},
        "PlayStation": {"from_domains": ["sony.com", "playstation.com"], "subject_keywords": ["playstation code"]},
        "Xbox": {"from_domains": ["xbox.com", "microsoft.com"], "subject_keywords": ["xbox code"]},
        "Nintendo": {"from_domains": ["nintendo.com"], "subject_keywords": ["nintendo code"]},
        
        # Travel/Transport
        "Uber": {"from_domains": ["uber.com"], "subject_keywords": ["uber code"]},
        "Lyft": {"from_domains": ["lyft.com"], "subject_keywords": ["lyft code"]},
        "DoorDash": {"from_domains": ["doordash.com"], "subject_keywords": ["doordash code"]},
        "Grubhub": {"from_domains": ["grubhub.com"], "subject_keywords": ["grubhub code"]},
        "Instacart": {"from_domains": ["instacart.com"], "subject_keywords": ["instacart code"]},
        "Airbnb": {"from_domains": ["airbnb.com"], "subject_keywords": ["airbnb code"]},
        "Booking.com": {"from_domains": ["booking.com"], "subject_keywords": ["booking.com code"]},
        "Expedia": {"from_domains": ["expedia.com"], "subject_keywords": ["expedia code"]},
        "Trip.com": {"from_domains": ["trip.com", "ctrip.com"], "subject_keywords": ["trip.com code"]},

        # Productivity/Work
        "Notion": {"from_domains": ["notion.so"], "subject_keywords": ["notion code", "magic code"]},
        "Asana": {"from_domains": ["asana.com"], "subject_keywords": ["asana code"]},
        "Trello": {"from_domains": ["trello.com"], "subject_keywords": ["trello code"]},
        "Monday.com": {"from_domains": ["monday.com"], "subject_keywords": ["monday.com code"]},
        "Jira": {"from_domains": ["atlassian.com"], "subject_keywords": ["jira code"]},
        "Confluence": {"from_domains": ["atlassian.com"], "subject_keywords": ["confluence code"]},
        "Miro": {"from_domains": ["miro.com"], "subject_keywords": ["miro code"]},
        "Figma": {"from_domains": ["figma.com"], "subject_keywords": ["figma code"]},
        "Canva": {"from_domains": ["canva.com"], "subject_keywords": ["canva code"]},
        "Dropbox": {"from_domains": ["dropbox.com"], "subject_keywords": ["dropbox code"]},
        "Box": {"from_domains": ["box.com"], "subject_keywords": ["box code"]},
        "OneDrive": {"from_domains": ["onedrive.com", "microsoft.com"], "subject_keywords": ["onedrive code"]},
        "Evernote": {"from_domains": ["evernote.com"], "subject_keywords": ["evernote code"]},
        "Quora": {"from_domains": ["quora.com"], "subject_keywords": ["quora code"]},

        # Customer support/CRM
        "Zendesk": {"from_domains": ["zendesk.com"], "subject_keywords": ["zendesk code"]},
        "Freshdesk": {"from_domains": ["freshdesk.com"], "subject_keywords": ["freshdesk code"]},
        "Salesforce": {"from_domains": ["salesforce.com"], "subject_keywords": ["salesforce code"]},
        "ServiceNow": {"from_domains": ["servicenow.com"], "subject_keywords": ["servicenow code"]},
        "HubSpot": {"from_domains": ["hubspot.com"], "subject_keywords": ["hubspot code"]},
        "Intercom": {"from_domains": ["intercom.com"], "subject_keywords": ["intercom code"]},

        # DevOps/Monitoring
        "Datadog": {"from_domains": ["datadoghq.com"], "subject_keywords": ["datadog code"]},
        "New Relic": {"from_domains": ["newrelic.com"], "subject_keywords": ["new relic code"]},
        "Sentry": {"from_domains": ["sentry.io"], "subject_keywords": ["sentry code"]},
        "Grafana": {"from_domains": ["grafana.com"], "subject_keywords": ["grafana code"]},
        "PagerDuty": {"from_domains": ["pagerduty.com"], "subject_keywords": ["pagerduty code"]},
        "Splunk": {"from_domains": ["splunk.com"], "subject_keywords": ["splunk code"]},
        
        # Security/Identity
        "Okta": {"from_domains": ["okta.com"], "subject_keywords": ["okta verification", "okta code"]},
        "Auth0": {"from_domains": ["auth0.com"], "subject_keywords": ["auth0 code"]},
        "Duo": {"from_domains": ["duosecurity.com"], "subject_keywords": ["duo code"]},
        "LastPass": {"from_domains": ["lastpass.com"], "subject_keywords": ["lastpass code"]},
        "1Password": {"from_domains": ["1password.com"], "subject_keywords": ["1password code"]},
        "Bitwarden": {"from_domains": ["bitwarden.com"], "subject_keywords": ["bitwarden code"]},
        "NordVPN": {"from_domains": ["nordvpn.com"], "subject_keywords": ["nordvpn code"]},
        "ExpressVPN": {"from_domains": ["expressvpn.com"], "subject_keywords": ["expressvpn code"]},
        "Proton VPN": {"from_domains": ["protonvpn.com"], "subject_keywords": ["proton vpn code"]},
        "Cloudflare Zero Trust": {"from_domains": ["cloudflare.com"], "subject_keywords": ["zero trust code"]},

        # Education
        "Coursera": {"from_domains": ["coursera.org"], "subject_keywords": ["coursera code"]},
        "Udemy": {"from_domains": ["udemy.com"], "subject_keywords": ["udemy code"]},
        "edX": {"from_domains": ["edx.org"], "subject_keywords": ["edx code"]},
        "Khan Academy": {"from_domains": ["khanacademy.org"], "subject_keywords": ["khan academy code"]},

        # Communication & Email services
        "SendGrid": {"from_domains": ["sendgrid.com"], "subject_keywords": ["sendgrid code"]},
        "Mailgun": {"from_domains": ["mailgun.com"], "subject_keywords": ["mailgun code"]},
        "Mailchimp": {"from_domains": ["mailchimp.com"], "subject_keywords": ["mailchimp code"]},
        "Twilio": {"from_domains": ["twilio.com"], "subject_keywords": ["twilio code"]},
        "MessageBird": {"from_domains": ["messagebird.com"], "subject_keywords": ["messagebird code"]},

        # Canadian banks (example set)
        "RBC": {"from_domains": ["rbc.com", "royalbank.com"], "subject_keywords": ["rbc verification"]},
        "BMO": {"from_domains": ["bmo.com", "bmo.com"], "subject_keywords": ["bmo code", "bank of montreal"]},
        "Scotiabank": {"from_domains": ["scotiabank.com", "scotia.com"], "subject_keywords": ["scotia code"]},
        "CIBC": {"from_domains": ["cibc.com"], "subject_keywords": ["cibc code"]},
        "TD Bank": {"from_domains": ["td.com", "tdbank.com"], "subject_keywords": ["td verification"]},
        
        # Other global banks/fintech
        "HSBC": {"from_domains": ["hsbc.com"], "subject_keywords": ["hsbc code"]},
        "Barclays": {"from_domains": ["barclays.com"], "subject_keywords": ["barclays code"]},
        "Santander": {"from_domains": ["santander.com"], "subject_keywords": ["santander code"]},
        "ING": {"from_domains": ["ing.com"], "subject_keywords": ["ing code"]},
        "BBVA": {"from_domains": ["bbva.com"], "subject_keywords": ["bbva code"]},
        "Revolut Business": {"from_domains": ["revolut.com"], "subject_keywords": ["revolut business code"]},

        # CMS/Hosting
        "WordPress.com": {"from_domains": ["wordpress.com"], "subject_keywords": ["wordpress.com code"]},
        "Ghost": {"from_domains": ["ghost.org"], "subject_keywords": ["ghost code"]},
        "Squarespace": {"from_domains": ["squarespace.com"], "subject_keywords": ["squarespace code"]},
        "Wix": {"from_domains": ["wix.com"], "subject_keywords": ["wix code"]},
        "Weebly": {"from_domains": ["weebly.com"], "subject_keywords": ["weebly code"]},

        # AI/ML
        "OpenAI": {"from_domains": ["openai.com"], "subject_keywords": ["openai code"]},
        "Anthropic": {"from_domains": ["anthropic.com"], "subject_keywords": ["anthropic code"]},
        "Hugging Face": {"from_domains": ["huggingface.co"], "subject_keywords": ["hugging face code"]},
        
        # File storage and sharing
        "WeTransfer": {"from_domains": ["wetransfer.com"], "subject_keywords": ["wetransfer code"]},
        "Mega": {"from_domains": ["mega.nz"], "subject_keywords": ["mega code"]},
        "pCloud": {"from_domains": ["pcloud.com"], "subject_keywords": ["pcloud code"]},

        # Forums/communities
        "Hacker News": {"from_domains": ["ycombinator.com"], "subject_keywords": ["hacker news code"]},
        "Stack Exchange": {"from_domains": ["stackexchange.com"], "subject_keywords": ["stack exchange code"]},

        # Healthcare
        "Fitbit": {"from_domains": ["fitbit.com"], "subject_keywords": ["fitbit code"]},
        "Strava": {"from_domains": ["strava.com"], "subject_keywords": ["strava code"]},
        
        # Transportation/Others
        "Tesla": {"from_domains": ["tesla.com"], "subject_keywords": ["tesla code"]},
        "Dell": {"from_domains": ["dell.com"], "subject_keywords": ["dell code"]},
        "HP": {"from_domains": ["hp.com"], "subject_keywords": ["hp code"]},
        "Adobe": {"from_domains": ["adobe.com"], "subject_keywords": ["adobe code"]},
        "Intuit": {"from_domains": ["intuit.com"], "subject_keywords": ["intuit code", "quickbooks code", "turbotax code"]},
        "QuickBooks": {"from_domains": ["intuit.com"], "subject_keywords": ["quickbooks code"]},
        "Trello": {"from_domains": ["trello.com"], "subject_keywords": ["trello code"]},
        
        # Government authentication portals (examples; region-specific)
        "IRS": {"from_domains": ["irs.gov"], "subject_keywords": ["irs code", "secure access"]},
        "Canada Revenue Agency": {"from_domains": ["cra-arc.gc.ca"], "subject_keywords": ["security code", "access code"]},
        "Gov.uk": {"from_domains": ["gov.uk"], "subject_keywords": ["gov.uk code"]},

        # Misc. popular apps
        "Notability": {"from_domains": ["notability.com"], "subject_keywords": ["code"]},
        "Calendly": {"from_domains": ["calendly.com"], "subject_keywords": ["calendly code"]},
        "Typeform": {"from_domains": ["typeform.com"], "subject_keywords": ["typeform code"]},
        "Softr": {"from_domains": ["softr.io"], "subject_keywords": ["softr code"]},
        "Bubble": {"from_domains": ["bubble.io"], "subject_keywords": ["bubble code"]},
        "Retool": {"from_domains": ["retool.com"], "subject_keywords": ["retool code"]},
        "Zapier": {"from_domains": ["zapier.com"], "subject_keywords": ["zapier code"]},
        "IFTTT": {"from_domains": ["ifttt.com"], "subject_keywords": ["ifttt code"]},
        "Airtable": {"from_domains": ["airtable.com"], "subject_keywords": ["airtable code"]},
        "Smartsheet": {"from_domains": ["smartsheet.com"], "subject_keywords": ["smartsheet code"]},
    }

    if len(services) < 100:
        variants = {
            "YouTube TV": {"from_domains": ["google.com"], "subject_keywords": ["youtube tv code"]},
            "Disney+ Hotstar": {"from_domains": ["hotstar.com"], "subject_keywords": ["hotstar code"]},
            "Paramount+": {"from_domains": ["paramount.com"], "subject_keywords": ["paramount+ code"]},
            "Peacock": {"from_domains": ["peacocktv.com"], "subject_keywords": ["peacock code"]},
            "BBC": {"from_domains": ["bbc.co.uk"], "subject_keywords": ["bbc code"]},
            "Yandex": {"from_domains": ["yandex.ru"], "subject_keywords": ["yandex code"]},
            "VK": {"from_domains": ["vk.com"], "subject_keywords": ["vk code"]},
            "Weibo": {"from_domains": ["weibo.com"], "subject_keywords": ["weibo code"]},
            "Alibaba": {"from_domains": ["alibaba.com"], "subject_keywords": ["alibaba code"]},
            "Rakuten": {"from_domains": ["rakuten.com"], "subject_keywords": ["rakuten code"]},
            "Flipkart": {"from_domains": ["flipkart.com"], "subject_keywords": ["flipkart code"]},
            "Mercado Libre": {"from_domains": ["mercadolibre.com"], "subject_keywords": ["mercado libre code"]},
            "Shopee": {"from_domains": ["shopee.com"], "subject_keywords": ["shopee code"]},
            "Gojek": {"from_domains": ["gojek.com"], "subject_keywords": ["gojek code"]},
            "Grab": {"from_domains": ["grab.com"], "subject_keywords": ["grab code"]},
            "Bolt": {"from_domains": ["bolt.eu"], "subject_keywords": ["bolt code"]},
            "Yelp": {"from_domains": ["yelp.com"], "subject_keywords": ["yelp code"]},
            "OpenTable": {"from_domains": ["opentable.com"], "subject_keywords": ["opentable code"]},
            "DoorDash Drive": {"from_domains": ["doordash.com"], "subject_keywords": ["doordash drive code"]},
            "Ghost.org": {"from_domains": ["ghost.org"], "subject_keywords": ["ghost.org code"]},
            "OkCupid": {"from_domains": ["okcupid.com"], "subject_keywords": ["okcupid code"]},
            "Tinder": {"from_domains": ["tinder.com"], "subject_keywords": ["tinder code"]},
            "Bumble": {"from_domains": ["bumble.com"], "subject_keywords": ["bumble code"]},
            "Hinge": {"from_domains": ["hinge.co"], "subject_keywords": ["hinge code"]},
            "Robinhood": {"from_domains": ["robinhood.com"], "subject_keywords": ["robinhood code"]},
            "Fidelity": {"from_domains": ["fidelity.com"], "subject_keywords": ["fidelity code"]},
            "Charles Schwab": {"from_domains": ["schwab.com"], "subject_keywords": ["schwab code"]},
            "E*TRADE": {"from_domains": ["etrade.com"], "subject_keywords": ["etrade code"]},
            "TD Ameritrade": {"from_domains": ["tdameritrade.com"], "subject_keywords": ["td ameritrade code"]},
            "Interactive Brokers": {"from_domains": ["interactivebrokers.com"], "subject_keywords": ["interactive brokers code"]},
            "Okta Verify": {"from_domains": ["okta.com"], "subject_keywords": ["okta verify code"]},
            "Azure AD": {"from_domains": ["microsoft.com"], "subject_keywords": ["azure ad code"]},
            "OneLogin": {"from_domains": ["onelogin.com"], "subject_keywords": ["onelogin code"]},
            "Ping Identity": {"from_domains": ["pingidentity.com"], "subject_keywords": ["pingid code", "ping identity"]},
            "Workday": {"from_domains": ["workday.com"], "subject_keywords": ["workday code"]},
            "SAP": {"from_domains": ["sap.com"], "subject_keywords": ["sap code"]},
            "Oracle": {"from_domains": ["oracle.com"], "subject_keywords": ["oracle code"]},
            "FreshBooks": {"from_domains": ["freshbooks.com"], "subject_keywords": ["freshbooks code"]},
            "Zoho": {"from_domains": ["zoho.com"], "subject_keywords": ["zoho code"]},
            "Basecamp": {"from_domains": ["basecamp.com"], "subject_keywords": ["basecamp code"]},
            "ClickUp": {"from_domains": ["clickup.com"], "subject_keywords": ["clickup code"]},
            "Linear": {"from_domains": ["linear.app"], "subject_keywords": ["linear code"]},
            "Shortcut": {"from_domains": ["app.shortcut.com"], "subject_keywords": ["shortcut code"]},
            "Clubhouse": {"from_domains": ["clubhouse.io"], "subject_keywords": ["clubhouse code"]},
            "Calendars": {"from_domains": ["calendar.com"], "subject_keywords": ["code"]},
            "SAML": {"from_domains": ["sso"], "subject_keywords": ["one-time passcode"]},
        }
        for k, v in variants.items():
            if k not in services:
                services[k] = v
            if len(services) >= 110:
                break
    return services


SERVICES = compile_top_services()

# Common aliases and brand synonyms
ALIASES: Dict[str, str] = {
    "twitter": "X",
    "x": "X",
    "steam guard": "Steam",
    "google mail": "Gmail",
    "g suite": "Google",
    "office 365": "Microsoft",
    "o365": "Microsoft",
}
