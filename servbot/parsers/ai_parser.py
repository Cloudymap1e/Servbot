"""AI-powered parsing fallback using Cerebras API.

Provides intelligent extraction of verification codes, links, and service
identification when regex patterns fail.
"""

import json
import re
from typing import Optional, Dict, Any

from ..config import load_cerebras_key

try:
    from cerebras.cloud.sdk import Cerebras
except ImportError:
    Cerebras = None  # type: ignore


def is_ai_available() -> bool:
    """Checks if AI parsing is available.
    
    Returns:
        True if Cerebras SDK is installed and API key is present
    """
    return Cerebras is not None and load_cerebras_key() is not None


def extract_with_ai(
    email_subject: str,
    email_body: str,
    from_addr: str,
) -> Optional[Dict[str, Any]]:
    """Extracts verification information using AI.
    
    Uses Cerebras API to intelligently extract service name, verification
    codes, and/or verification links from email content.
    
    Args:
        email_subject: Email subject line
        email_body: Email body text
        from_addr: Sender email address
        
    Returns:
        Dict with keys: service, code (optional), link (optional)
        Returns None if extraction fails or AI unavailable
    """
    if not Cerebras:
        return None
    
    api_key = load_cerebras_key()
    if not api_key:
        return None
    
    try:
        client = Cerebras(api_key=api_key)
        
        # Prepare extraction prompt
        prompt = f"""You are an expert at extracting verification information from emails.

FROM: {from_addr}
SUBJECT: {email_subject}
BODY: {email_body[:2000]}

Task: Analyze this email and extract:
1. Service/company name (the brand sending the email)
2. Verification code (4-8 digit OTP or alphanumeric code)
3. Verification link (magic link/sign-in button URL)

Rules:
- Return ONLY valid JSON with this format:
  {{"service": "ServiceName", "code": "123456", "link": "https://..."}}
- Include "code" if there's an OTP/verification code
- Include "link" if there's a verification/magic link URL
- DO NOT include unsubscribe links or homepage links
- Service should be the brand name (e.g., "Google", "GitHub", not domain)
- If you cannot determine service, use "Unknown"
- If no verification method found, return null for that field

Response (JSON only):"""
        
        # Call Cerebras API
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise data extraction assistant. Return only valid JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model="gpt-oss-120b",
            stream=False,
            max_completion_tokens=250,
            temperature=0.2,  # Lower temperature for deterministic output
        )
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON (handle markdown code blocks)
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            # Validate and clean result
            service = result.get('service')
            code = result.get('code')
            link = result.get('link')
            
            # Clean null/None values
            if isinstance(service, str) and service.lower() in ('null', 'none'):
                service = None
            if isinstance(code, str) and code.lower() in ('null', 'none'):
                code = None
            if isinstance(link, str) and link.lower() in ('null', 'none'):
                link = None
            
            # Return if we found something meaningful
            if service or code or link:
                return {
                    'service': str(service).strip() if service else None,
                    'code': str(code).strip() if code else None,
                    'link': str(link).strip() if link else None,
                }
        
        return None
    
    except Exception:
        # Silently fail - AI is a fallback, not critical
        return None


def enhance_service_identification(
    detected_service: str,
    email_subject: str,
    email_body: str,
    from_addr: str,
) -> str:
    """Enhances service identification using AI.
    
    Used when initial regex-based detection returns "Unknown".
    
    Args:
        detected_service: Currently detected service name
        email_subject: Email subject
        email_body: Email body
        from_addr: Sender address
        
    Returns:
        Enhanced service name or original if AI fails
    """
    if detected_service != "Unknown" or not is_ai_available():
        return detected_service
    
    result = extract_with_ai(email_subject, email_body, from_addr)
    if result and result.get('service'):
        service = result['service']
        if service and service.lower() not in ('unknown', 'null', 'none'):
            return service
    
    return detected_service

