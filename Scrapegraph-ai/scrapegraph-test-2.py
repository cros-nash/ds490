import os
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from scrapegraphai.graphs import CodeGeneratorGraph

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


class Article(BaseModel):
    title: str = Field(description="Name of the article")
    descripiton: str = Field(description="Description of the article")
    category: str = Field(description="Category of the article")
    content: str = Field(description="The content of the article")

class Articles(BaseModel):
    articles: List[Article]

code_generator_graph = CodeGeneratorGraph(
    prompt="Please give me the name, description, category, and content of every article currently present in the section: Today's Pocket Hits.",
    source="https://getpocket.com/home",
    schema=Articles,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)