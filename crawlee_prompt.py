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

**Crawlee documentation reference (generated from langchain similarity_search)**:
{crawlee_snippet}
```

**Backbone Code**:
```python
import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {{context.request.url}}')
        
        {{ SCRAPING LOGIC }}
        
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
5. The `max_requests_per_crawl` must always be set to 500.
6. If the page uses <select> dropdowns to filter results, do not try to emulate clicks. Instead, extract the <option> values and programmatically build the corresponding URLs (e.g. by plugging each option into the query string) and crawl those.
7. Do not try to import additional modules
8. When you need combinations of filters (e.g. multiple dropdowns), use `itertools.product` to generate Cartesian products of option values.

*If a placeholder is not needed, delete the whole `{{ … }}` token and leave that spot blank.*

**Output ONLY the Python code WITHOUT ANY ADDITIONAL TEXT.**
In your code do not include backticks.
'''