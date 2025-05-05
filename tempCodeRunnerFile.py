code_generator_graph = CodeGeneratorGraph(

    prompt="I need Python code to build a nationwide database of eviction court records by scraping county court websites. The code should: 1) Interface with the Oklahoma State Courts Network docket search system, 2) Systematically search for eviction/landlord-tenant/FED (forcible entry and detainer) cases across all available counties and date ranges, 3) Handle pagination of search results, 4) Extract comprehensive case details including case number, filing date, plaintiff/defendant names and addresses, judgment amounts, and case outcomes, 5) Follow links to detailed case information pages to extract complete case histories, 6) Normalize addresses to allow for geocoding and census tract matching, 7) Implement appropriate delays between requests to respect server resources, and 8) Store results in a database with a schema designed for geographic and temporal analysis of eviction patterns.",
    source="https://www.oscn.net/dockets/Search.aspx",
    schema=EvictionDatabase,
    config=graph_config,
)