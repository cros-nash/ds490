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


class Example(BaseModel):
    name: str = Field(description="Name of the example")
    description: str = Field(description="One sentence description of the example")
    url: str = Field(description="URL of the example")

class Examples(BaseModel):
    examples: List[Example]

code_generator_graph = CodeGeneratorGraph(

    prompt="Please give me the name, description, and URL for examples of crawlee applications that involve pagination",
    source="https://crawlee.dev/python/docs/examples",
    schema=Examples,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)