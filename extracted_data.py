import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from lxml import html
import json
import os

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        html_content = await context.page.content()
        document = html.fromstring(html_content)

        cycles = document.xpath('//select[@class="js-customSelect"][1]/option')
        cycle_values = [cycle.text for cycle in cycles]
        
        for cycle_value in cycle_values:
            await context.page.select_option('//select[@class="js-customSelect"][1]', value=cycle_value)
            await context.page.wait_for_timeout(1000)
            
            html_content = await context.page.content()
            document = html.fromstring(html_content)
            data_tables = document.xpath('//table[contains(@class, "DataTable-Partial")]')
            tables_data = []

            for table in data_tables:
                title = table.xpath('./preceding-sibling::h2[1]/text()')[0].strip() if table.xpath('./preceding-sibling::h2[1]/text()') else ''
                
                rows = table.xpath('.//tbody/tr')
                
                for row in rows:
                    party = row.xpath('td[contains(@class, "color-category")]/text()')[0] if row.xpath('td[contains(@class, "color-category")]/text()') else ''
                    cands = row.xpath('td[contains(@class, "number")][1]/text()')[0] if row.xpath('td[contains(@class, "number")][1]/text()') else ''
                    total_raised = row.xpath('td[contains(@class, "number")][2]/text()')[0] if row.xpath('td[contains(@class, "number")][2]/text()') else ''
                    total_spent = row.xpath('td[contains(@class, "number")][3]/text()')[0] if row.xpath('td[contains(@class, "number")][3]/text()') else ''
                    total_cash = row.xpath('td[contains(@class, "number")][4]/text()')[0] if row.xpath('td[contains(@class, "number")][4]/text()') else ''
                    total_pacs = row.xpath('td[contains(@class, "number")][5]/text()')[0] if row.xpath('td[contains(@class, "number")][5]/text()') else ''
                    total_individuals = row.xpath('td[contains(@class, "number")][6]/text()')[0] if row.xpath('td[contains(@class, "number")][6]/text()') else ''

                    tables_data.append({
                        "title": title,
                        "party": party,
                        "cycle": cycle_value,
                        "cands": cands,
                        "total_raised": total_raised,
                        "total_spent": total_spent,
                        "total_cash": total_cash,
                        "total_pacs": total_pacs,
                        "total_individuals": total_individuals
                    })

            file_name = f"election_cycle_{cycle_value}.json"
            with open(file_name, 'w') as f:
                json.dump({"tables": tables_data}, f, indent=4)

    await crawler.run(['https://www.opensecrets.org/elections-overview'])

if __name__ == '__main__':
    asyncio.run(main())
