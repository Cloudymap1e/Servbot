import os

from servbot.proxy import load_provider_configs, ProxyManager


def main():
    # Ensure you set these env vars or put real creds in config/proxies.json
    # os.environ['BRIGHTDATA_USERNAME'] = 'your-zone-username'
    # os.environ['BRIGHTDATA_PASSWORD'] = 'your-password'

    configs = load_provider_configs('config/proxies.json')
    pm = ProxyManager(configs)

    ep = pm.acquire()  # cheapest by price_per_gb
    print('Requests proxies:', ep.as_requests_proxies())
    print('Playwright proxy:', ep.as_playwright_proxy())

    # Acquire explicitly by name
    ep2 = pm.acquire(name='brightdata-resi', region='US')
    print('BD user:', ep2.username)


if __name__ == '__main__':
    main()
