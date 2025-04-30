import asyncio
import csv
import json
import re
from typing import List, Dict, Any, Optional

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

# Proxy list for rotation - sample placeholders, replace with actual proxies if available
PROXIES = [
    # "http://proxy1.example.com:3128",
    # "http://proxy2.example.com:3128",
]

# Rate limit settings
MINIMUM_DELAY_BETWEEN_REQUESTS = 1.0  # seconds

# CSV input path placeholder - adjust path as needed
CSV_INPUT_PATH = 'addresses.csv'

# Target API URL for AT&T address lookup
TARGET_URL = 'https://www.att.com/internet/check-availability/'  # replace with actual URL for lookup or main page

# Since we cannot perform actual proxy or real I/O in this code snippet,
# the example will fetch each address by form-submitting or modifying URL parameters;
# here implemented as scraping the response page and parsing __NEXT_DATA__ JSON.

async def extract_plans_from_json(next_data: dict) -> List[Dict[str, Any]]:
    """Extract plans info from the __NEXT_DATA__ JSON block."""
    try:
        internet_plan_map = next_data['props']['pageProps']['InternetContent']['internetPlanMap']
    except (KeyError, TypeError):
        internet_plan_map = []

    plans = []
    for plan in internet_plan_map:
        plan_name = plan.get('planName') or plan.get('name') or ''
        download_upload_str = plan.get('downloadUploadSpeeds') or ''
        # Expecting format: 'XXXMbps YYYMbps'
        download_speed_mbps = None
        upload_speed_mbps = None
        if download_upload_str:
            parts = download_upload_str.split()
            if len(parts) == 2:
                try:
                    download_speed_mbps = float(parts[0].lower().replace('mbps', '').strip())
                except ValueError:
                    download_speed_mbps = None
                try:
                    upload_speed_mbps = float(parts[1].lower().replace('mbps', '').strip())
                except ValueError:
                    upload_speed_mbps = None

        # Price extraction:
        # The JSON doesn't contain clear numeric price fields
        # We will attempt to parse price from legal disclaimers or price fields if any,
        # otherwise leave price as None
        price_usd_per_month = None

        # An attempt to find price might be made by checking 'priceLegalSubContent' or similar fields:
        price_text = plan.get('priceLegalSubContent') or plan.get('description') or ''
        # Often prices in US dollars are written as e.g. "$45/mo." or "$45"
        # Extract $ and number if available
        if price_text:
            match = re.search(r'\$\s?(\d{1,4}(?:\.\d{1,2})?)', price_text)
            if match:
                try:
                    price_usd_per_month = float(match.group(1))
                except ValueError:
                    price_usd_per_month = None

        # If price not found here, leave None.

        plans.append({
            'plan_name': plan_name,
            'download_speed_mbps': download_speed_mbps,
            'upload_speed_mbps': upload_speed_mbps,
            'price_usd_per_month': price_usd_per_month,
        })

    return plans

async def main() -> None:
    # Load addresses from CSV: expect CSV with at least 'address' and 'census_block' columns
    # For demonstration, we read CSV once and create list of dicts
    addresses: List[Dict[str, str]] = []
    try:
        with open(CSV_INPUT_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'address' in row and 'census_block' in row:
                    addresses.append({
                        'address': row['address'].strip(),
                        'census_block': row['census_block'].strip(),
                    })
    except Exception as e:
        print(f"Failed to read CSV file '{CSV_INPUT_PATH}': {e}")
        return

    # Helper to rotate proxies (if any) - simple round-robin
    proxy_index = 0
    total_proxies = len(PROXIES)

    # Create PlaywrightCrawler instance
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
        # Additional options (proxy rotation, timeouts, etc.) could be set here if supported
    )

    # Use a shared asyncio.Lock for rate limiting
    rate_limit_lock = asyncio.Lock()

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        nonlocal proxy_index

        context.log.info(f'Processing {context.request.url}')

        # The user wants to submit each address to check service availability.
        # Given no direct API URL provided, and per analysis, the target appears to use a client-rendered app,
        # with data embedded in '<script id="__NEXT_DATA__">' tag in the loaded page.

        # Extract full page content
        content = await context.page.content()

        # Extract the JSON inside <script id="__NEXT_DATA__" type="application/json">
        next_data_json = None
        try:
            # Evaluate JavaScript in page to get __NEXT_DATA__ object directly,
            # which is more reliable than parsing HTML with regex.
            next_data_json = await context.page.evaluate('window.__NEXT_DATA__')
        except Exception:
            # Fallback: parse content for <script id="__NEXT_DATA__"> JSON block (less robust)
            import re
            pattern = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL)
            match = pattern.search(content)
            if match:
                try:
                    next_data_json = json.loads(match.group(1))
                except Exception:
                    next_data_json = None

        plans = []
        if next_data_json:
            plans = await extract_plans_from_json(next_data_json)

        # Get address and census block from metadata in request userData
        address = context.request.user_data.get('address', '')
        census_block = context.request.user_data.get('census_block', '')

        data = {
            'address': address,
            'census_block': census_block,
            'plans': plans,
        }

        await context.push_data(data)

        # Apply rate limiting
        async with rate_limit_lock:
            await asyncio.sleep(MINIMUM_DELAY_BETWEEN_REQUESTS)

    # Prepare a list of requests with address passed via user_data so handler can include in output
    requests = []
    for record in addresses:
        # For this example, we will URL-encode the address as query param or infer process to hit site/search
        # Because the user did not provide the exact API endpoint or URL structure,
        # we will use the main lookup page, assuming the site looks up address from URL or via form - here just the main page:
        url = TARGET_URL
        # Pass address and census block in request metadata
        requests.append({
            'url': url,
            'user_data': {
                'address': record['address'],
                'census_block': record['census_block'],
            }
        })

    # Run the crawler with generated requests
    await crawler.run(requests)


if __name__ == '__main__':
    asyncio.run(main())