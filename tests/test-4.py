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
        "temperature" : 0,
        "top_p" : 1,
    },
    "verbose": True,
    "headless": False,
    "reduction": 2,
    "max_iterations": {
        "overall": 3,
        "syntax": 3,
        "execution": 3,
        "validation": 3,
        "semantic": 3,
    },
    "output_file_name": "extracted_data.py",
}


class Event(BaseModel):
    title: str = Field(description="Title of the event")
    date: str = Field(description="Date or time period when the event occurs")
    location: str = Field(description="Location where the event is held")

class Events(BaseModel):
    events: List[Event]

code_generator_graph = CodeGeneratorGraph(
    prompt="Please extract the title, date, and location for upcoming tech events listed on this page.",
    source="https://techmeme.com/events",  # real-world structured but non-trivial page
    schema=Events,
    config=graph_config,
)

result = code_generator_graph.run()
print(result)