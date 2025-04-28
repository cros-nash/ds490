import os
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from code_generator_graph import CodeGeneratorGraph

# Define the configuration for th`e scraping pipeline
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


class Function(BaseModel):
    name: str = Field(description="Name of the item")
    description: str = Field(description="Description of the item")
    price: float = Field(description="The current price of the item")
class Functions(BaseModel):
    functions: List[Function]

code_generator_graph = CodeGeneratorGraph(
    prompt="Give me the details of every computer/laptop on the first and second page",
    source="https://webscraper.io/test-sites/e-commerce/static/computers/laptops",
    schema=Functions,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)