import os
from typing import List

from pydantic import BaseModel, Field

from graphs.code_generator_graph import CodeGeneratorGraph

# Define the configuration for the scraping pipeline
graph_config = {
    "llm": {
        "api_key": os.getenv('OPENAI_API_KEY'),
        "model": "openai/gpt-4o-mini",
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

class Item(BaseModel):
    """
    Represents a single computer or laptop item with its key attributes.
    """
    name: str = Field(..., description="The full name/title of the computer or laptop item.")
    description: str = Field(..., description="A detailed description or specifications of the item.")
    price: float = Field(..., description="The price of the item in numerical format (e.g., 599.99).")

class ItemList(BaseModel):
    """
    A collection of all computer and laptop items extracted from the website.
    """
    items: List[Item]

code_generator_graph = CodeGeneratorGraph(
    prompt="Scrape and return the complete details (name, description, and price) for every computer and laptop listed on *BOTH* the first and second pages.",
    source="https://webscraper.io/test-sites/e-commerce/static/computers/laptops",
    schema=ItemList,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)