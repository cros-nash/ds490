import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from graphs.code_generator_graph import CodeGeneratorGraph

load_dotenv()

# Define the configuration for the scraping pipeline
graph_config = {
    "llm": {
        "api_key": os.getenv('OPENAI_API_KEY'),
        "model": "openai/gpt-4o",
        "temperature" : 1,
        "top_p" : 1,
    },
    "verbose": True,
    "headless": False,
    "reduction": 2,
    "output_file_name": "extracted_data.py",
}


class Table(BaseModel):
    title: str = Field(description="Label indicating the group of candidates (e.g., Presidential, House, Senate)")
    party: str = Field(description="Name of the political party (e.g., Dems, Repubs, All)")
    cycle: str = Field(description="Election year corresponding to the financial data (e.g., 2024, 2022, ... 1990)")
    cands: str = Field(description="Number of candidates from the given party in the specified election cycle")
    total_raised: str = Field(description="Total amount of money raised by the party's candidates in this cycle")
    total_spent: str = Field(description="Total amount of money spent by the party's candidates in this cycle")
    total_cash: str = Field(description="Total cash on hand at the end of the reporting period for the party's candidates")
    total_pacs: str = Field(description="Total contributions received from Political Action Committees (PACs) by the party's candidates")
    total_individuals: str = Field(description="Total contributions received from individual donors by the party's candidates")
    
class Tables(BaseModel):
    tables: List[Table]

code_generator_graph = CodeGeneratorGraph(

    prompt="Scrape financial summary tables from https://www.opensecrets.org/elections-overview for each election cycle from 1990 to 2024 using the \"Select a Cycle\" dropdown, and return for each cycle the number of candidates, total raised, total spent, total cash on hand, total from PACs, and total from individuals for All, Democrats, and Republicans. Each cycle should be saved in its own JSON file.",
    source="https://www.opensecrets.org/elections-overview",
    schema=Tables,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)