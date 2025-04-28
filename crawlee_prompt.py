DEFAULT_CRAWLEE_TEMPLATE = '''\
**Task**  
You are given a *pre-written backbone script* that already imports everything, declares functions, and contains
clearly delimited **Jinja-style placeholders** (e.g. {{ EXTRACTION_LOGIC }}).

Your job is **NOT** to regenerate the whole file.  
Your job is to **replace each placeholder with the required Python code** while leaving every
other character in the file **unchanged**.

---

**User's Request**:
{user_input}

**Desired JSON Output Schema**:
```json
{json_schema}
```

**Initial Task Analysis**:
{initial_analysis}

**HTML Code**:
```html
{html_code}
```

**HTML Structure Analysis**:
{html_analysis}

**Crawlee API Reference (Playwright Mode)**:
```python
Core Crawlers
-------------

PlaywrightCrawler: Headless browser crawler for JS-rendered sites.
Example:
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
crawler = PlaywrightCrawler()
@crawler.router.default_handler
async def handler(context): await context.enqueue_links(); await context.push_data({{'url': context.request.url}})
await crawler.run(['https://example.com'])

BasicCrawler: Low-level crawling with full control.
BeautifulSoupCrawler: Fast crawler using BeautifulSoup (no JS).
ParselCrawler: Scrapy-style crawler using Parsel.

Configuration
-------------

Configuration class: Manages global runtime settings.
Fields: available_memory_ratio, default_dataset_id, headless, log_level, storage_dir
Method: get_global_configuration()

Request Handling
----------------

Request: Represents a crawl request.
Fields: url, method, headers, payload, label, unique_key, user_data
Methods:
- from_url(url, **kwargs)
- get_query_param_from_url(param, default=None)

Data Storage
------------

Dataset: Append-only structured store.
Methods:
- push_data(data)
- get_data(**kwargs)
- export_to(key, content_type, ...)

Link Enqueuing
--------------

enqueue_links(context): Auto-discovers and enqueues links.
Params: selector, label, strategy, include, exclude, transform_request_function
Example:
await context.enqueue_links(selector='a.link', label='DETAIL', strategy='same-domain')

Routing
-------

Router: Manages route labels and handlers.
Usage:
from crawlee.router import Router
router = Router()
@router.default_handler async def d(ctx): ...
@router.handler('LABEL') async def l(ctx): ...

Utilities
---------

Config: get_configuration(), set_configuration()
Events: get_event_manager(), set_event_manager()
Storage: get_storage_client(), set_cloud_storage_client(), set_local_storage_client()
```

**Backbone Code**:
```python
import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=100,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {{context.request.url}}')
        # {{ WAIT_FOR_CATEGORY_SELECTOR }}
        # Example: await context.page.wait_for_selector('.product-item > a')

        # {{ ENQUEUE_DETAIL_LINKS }}
        # Example: await context.enqueue_links(selector='.product-item > a', label='LABEL')

        # {{ PAGINATION_LOGIC }}
        # Pattern 1: Click "Next" button (e.g. JS-based button)
        next_button = await context.page.query_selector('button.next')
        if next_button:
            await next_button.click()
            await context.page.wait_for_timeout(1000)  # wait for page to load

        # Pattern 2: Classic link-based pagination
        await context.enqueue_links(selector='a.pagination__next', label='DETAIL')

        # Pattern 3: Infinite scroll (optional fallback)
        # for _ in range(3):
        #     await context.page.mouse.wheel(0, 10000)
        #     await context.page.wait_for_timeout(1500)
        
        data = {{ DICTIONARY MATCHING JSON SCHEMA }}
        
        await context.push_data(data)
        
    await crawler.run(['{{ SOURCE_URL }}'])


if __name__ == '__main__':
    asyncio.run(main())

```
---

### What to do
1. Locate every `{{ ... }}` placeholder in **Backbone Code**. Replace `SOURCE_URL` with the source url from the user's request.
2. Insert concise, working Python that
    • extracts the required data from the HTML / network response  
    • produces a dict that exactly matches the JSON schema.
3. **Do not** reformat or rewrite lines outside the placeholders.
4. **Return *only* the fully-filled Python file** (no back-ticks, headings, or commentary).

*If a placeholder is not needed, delete the whole `{{ … }}` token and leave that spot blank.*

**Output ONLY the Python code WITHOUT ANY IMPORTS OR ADDITIONAL TEXT.**
In your code do not include backticks.
'''