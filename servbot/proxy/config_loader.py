from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import ProviderConfig


def load_provider_configs(path: str | Path) -> List[ProviderConfig]:
    """Load ProviderConfig list from a JSON file.

    Example JSON structure:
    {
      "providers": [
        {
          "name": "static-us",
          "type": "static_list",
          "price_per_gb": 0.0,
          "options": {"entries": "user:pass@1.2.3.4:8000, 5.6.7.8:9000"}
        },
        {
          "name": "brightdata-resi",
          "type": "brightdata",
          "price_per_gb": 12.0,
          "options": {
            "host": "zproxy.lum-superproxy.io",
            "port": "22225",
            "username": "env:BRIGHTDATA_USERNAME",
            "password": "env:BRIGHTDATA_PASSWORD",
            "country": "US"
          }
        }
      ]
    }
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    providers = []
    for item in data.get("providers", []):
        providers.append(
            ProviderConfig(
                name=item["name"],
                type=item["type"],
                price_per_gb=item.get("price_per_gb"),
                concurrency_limit=item.get("concurrency_limit"),
                options=item.get("options"),
            )
        )
    return providers
