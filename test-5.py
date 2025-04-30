import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional

from code_generator_graph import CodeGeneratorGraph

load_dotenv()

# Define the configuration for the scraping pipeline
graph_config = {
    "llm": {
        "api_key": os.getenv('OPENAI_API_KEY'),
        "model": "openai/gpt-4.1-mini",
    },
    "verbose": True,
    "headless": False,
    "reduction": 2,
    "max_iterations": {
        "overall": 10,
        "syntax": 3,
        "execution": 3,
        "validation": 3,
        "semantic": 3,
    },
    "output_file_name": "extracted_data.py",
}

class CaseHistoryEvent(BaseModel):
    event_date: str = Field(..., description="Date of the case event, in ISO format if possible")
    event_description: str = Field(..., description="Description of the event in the case history")


class EvictionCase(BaseModel):
    case_number: str = Field(..., description="Unique case number assigned to the eviction case")
    filing_date: str = Field(..., description="Date when the eviction case was filed, in ISO format")
    plaintiff_name: str = Field(..., description="Full name of the plaintiff (landlord)")
    defendant_name: str = Field(..., description="Full name of the defendant (tenant)")
    case_outcome: str = Field(None, description="Outcome of the eviction case, e.g., 'dismissed', 'judgment for plaintiff'")
    case_history: List[CaseHistoryEvent] = Field(..., description="Chronological list of events in the case history")
    county: str = Field(..., description="County where the eviction case was filed")


class EvictionDatabase(BaseModel):
    cases: List[EvictionCase] = Field(..., description="List of all extracted eviction cases across counties")

code_generator_graph = CodeGeneratorGraph(

    prompt="I need Python code to build a nationwide database of eviction court records by scraping county court websites. The code should: 1) Interface with the Oklahoma State Courts Network docket search system, 2) Systematically search for eviction/landlord-tenant/FED (forcible entry and detainer) cases across all available counties and date ranges, 3) Handle pagination of search results, 4) Extract comprehensive case details including case number, filing date, plaintiff/defendant names and addresses, judgment amounts, and case outcomes, 5) Follow links to detailed case information pages to extract complete case histories, 6) Normalize addresses to allow for geocoding and census tract matching, 7) Implement appropriate delays between requests to respect server resources, and 8) Store results in a database with a schema designed for geographic and temporal analysis of eviction patterns.",
    source="https://www.oscn.net/dockets/Search.aspx",
    schema=EvictionDatabase,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)