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
        "model": "openai/gpt-4o-mini",
        "temperature" : 0.5,
        "top_p" : 1,
    },
    "verbose": True,
    "headless": False,
    "reduction": 2,
    "output_file_name": "extracted_data.py",
}

class idea(BaseModel):
    street: str = Field(..., description="Address of the property")
    price: str = Field(..., description="price of the property")
    link: str = Field(..., description="Link to the zillow listing")


class Properties(BaseModel):
    properties: List[idea] = Field(..., description="List of all the properties found")

code_generator_graph = CodeGeneratorGraph(

    prompt="I need Python code to look for the top 10 most expensive properties in Boston. Please look up Boston in the search bar, and then scrape the 10 most expensive properties.",
    source="https://www.zillow.com/",
    schema=Properties,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)