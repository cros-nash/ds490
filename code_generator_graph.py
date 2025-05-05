"""
SmartScraperGraph Module
"""

from typing import Optional, Type

from pydantic import BaseModel

from scrapegraphai.nodes import (
    FetchNode,
    GenerateAnswerNode,
    HtmlAnalyzerNode,
    ParseNode,
    PromptRefinerNode,
)

from generate_crawlee_code_node import GenerateCodeNode
from crawlee_rag_node import RAGNode

from scrapegraphai.utils.save_code_to_file import save_code_to_file
from scrapegraphai.graphs.abstract_graph import AbstractGraph
from scrapegraphai.graphs.base_graph import BaseGraph

from langchain_openai import OpenAIEmbeddings
from defaults import NODE_DEFAULTS

class CodeGeneratorGraph(AbstractGraph):
    """
    CodeGeneratorGraph is a script generator pipeline that generates
    the function extract_data(html: str) -> dict() for
    extracting the wanted information from a HTML page.
    The code generated is in Python and uses the library BeautifulSoup.
    It requires a user prompt, a source URL, and an output schema.

    Attributes:
        prompt (str): The prompt for the graph.
        source (str): The source of the graph.
        config (dict): Configuration parameters for the graph.
        schema (BaseModel): The schema for the graph output.
        llm_model: An instance of a language model client, configured for generating answers.
        embedder_model: An instance of an embedding model client,
        configured for generating embeddings.
        verbose (bool): A flag indicating whether to show print statements during execution.
        headless (bool): A flag indicating whether to run the graph in headless mode.
        library (str): The library used for web scraping (beautiful soup).

    Args:
        prompt (str): The prompt for the graph.
        source (str): The source of the graph.
        config (dict): Configuration parameters for the graph.
        schema (BaseModel): The schema for the graph output.

    Example:
        >>> code_gen = CodeGeneratorGraph(
        ...     "List me all the attractions in Chioggia.",
        ...     "https://en.wikipedia.org/wiki/Chioggia",
        ...     {"llm": {"model": "openai/gpt-3.5-turbo"}}
        ... )
        >>> result = code_gen.run()
        )
    """

    def __init__(
        self,
        prompt: str,
        source: str,
        config: dict,
        schema: Optional[Type[BaseModel]] = None,
    ):
        super().__init__(prompt, config, source, schema)

        self.input_key = "url" if source.startswith("http") else "local_dir"

    def _create_graph(self) -> BaseGraph:
        """
        Creates the graph of nodes representing the workflow for web scraping.

        Returns:
            BaseGraph: A graph instance representing the web scraping workflow.
        """

        if self.schema is None:
            raise KeyError("The schema is required for CodeGeneratorGraph")

        fetch_node = FetchNode(
            input="url| local_dir",
            output=["doc"],
            node_config={
                "llm_model": self.llm_model,
                "force": self.config.get("force", False),
                "cut": self.config.get("cut", True),
                "loader_kwargs": self.config.get("loader_kwargs", {}),
                "browser_base": self.config.get("browser_base"),
                "scrape_do": self.config.get("scrape_do"),
                "storage_state": self.config.get("storage_state"),
            },
        )
        parse_node = ParseNode(
            input="doc",
            output=["parsed_doc"],
            node_config={"llm_model": self.llm_model, "chunk_size": self.model_token},
        )

        generate_validation_answer_node = GenerateAnswerNode(
            input="user_prompt & (relevant_chunks | parsed_doc | doc)",
            output=["answer"],
            node_config={
                "llm_model": self.llm_model,
                "additional_info": self.config.get("additional_info"),
                "schema": self.schema,
            },
        )

        prompt_refier_node = PromptRefinerNode(
            input="user_prompt",
            output=["refined_prompt"],
            node_config={
                "llm_model": self.llm_model,
                "chunk_size": self.model_token,
                "schema": self.schema,
            },
        )

        html_analyzer_node = HtmlAnalyzerNode(
            input="refined_prompt & original_html",
            output=["html_info", "reduced_html"],
            node_config={
                "llm_model": self.llm_model,
                "additional_info": self.config.get("additional_info"),
                "schema": self.schema,
                "reduction": self.config.get("reduction", 0),
            },
        )
        
        rag_node = RAGNode(
            input=None,
            output=["vectorial_db"],
            node_config={
            "llm_model":    self.llm_model,
            "embedder_model": self.config.get("embedder_model", OpenAIEmbeddings()),
            "client_type":  "local_db",
            "verbose":      self.config.get("verbose", False),
            },
        )

        llm_params = self.config.get("llm", {}) or {}
        retrieval_params = self.config.get("retrieval", NODE_DEFAULTS["retrieval"])
        max_iter = self.config.get("max_iterations", NODE_DEFAULTS["max_iterations"])
        generate_code_node = GenerateCodeNode(
            input="user_prompt & refined_prompt & html_info & reduced_html & vectorial_db & answer",
            output=["generated_code"],
            node_config={
                "llm_model": self.llm_model,
                **llm_params,
                "retrieval": retrieval_params,
                "max_iterations": max_iter,
                "additional_info": self.config.get("additional_info"),
                "schema": self.schema,
                "embedder_model": self.config.get("embedder_model", OpenAIEmbeddings()),
            },
        )

        return BaseGraph(
            nodes=[
                fetch_node,
                parse_node,
                generate_validation_answer_node,
                prompt_refier_node,
                html_analyzer_node,
                rag_node,
                generate_code_node,
            ],
            edges=[
                (fetch_node, parse_node),
                (parse_node, generate_validation_answer_node),
                (generate_validation_answer_node, prompt_refier_node),
                (prompt_refier_node, html_analyzer_node),
                (html_analyzer_node, rag_node),
                (rag_node, generate_code_node),
            ],
            entry_point=fetch_node,
            graph_name=self.__class__.__name__,
        )

    def run(self) -> str:
        """
        Executes the scraping process and returns the generated code.

        Returns:
            str: The generated code.
        """
        
        '''
        inputs = {"user_prompt": self.prompt, self.input_key: self.source}
        self.final_state, self.execution_info = self.graph.execute(inputs)

        generated_code = self.final_state.get("generated_code", "No code created.")

        if self.config.get("filename") is None:
            filename = "extracted_data.py"
        elif ".py" not in self.config.get("filename"):
            filename += ".py"
        else:
            filename = self.config.get("filename")

        save_code_to_file(generated_code, filename)

        return generated_code
        '''
        
        import os, json, hashlib
        from langchain_core.documents import Document

        # 1) prepare cache directory & key
        cache_dir = self.config.get("node_cache_dir", ".node_cache")
        os.makedirs(cache_dir, exist_ok=True)
        key_source = f"{self.prompt}||{self.source}"
        cache_key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()
        cache_file = os.path.join(cache_dir, cache_key + ".json")
        use_cache = os.path.isfile(cache_file) and not self.config.get("force", False)

        if use_cache:
            # Load cached state (excluding vector DB) and rehydrate
            print("CACHE IS BEING USED :)")
            with open(cache_file, "r") as f:
                cached = json.load(f)
            original_html = [
                Document(page_content=d["page_content"], metadata=d["metadata"])
                for d in cached.get("original_html", [])
            ]
            state = {
                "user_prompt":    self.prompt,
                self.input_key:   self.source,
                "original_html":  original_html,
                "refined_prompt": cached.get("refined_prompt"),
                "html_info":      cached.get("html_info"),
                "reduced_html":   cached.get("reduced_html"),
                "answer":         cached.get("answer"),
            }
            # Restore vector DB client from persistent store
            try:
                from qdrant_client import QdrantClient
            except ImportError:
                raise ImportError("qdrant_client is required to restore vector DB. Install via 'pip install qdrant-client'.")
            state["vectorial_db"] = QdrantClient(path=self.config.get("client_path", "databases/crawlee_db"))

        else:
            # First run: execute all upstream nodes and cache intermediate results
            print("CACHE IS BEING CREATED")
            state = {"user_prompt": self.prompt, self.input_key: self.source}
            upstream_nodes = self.graph.nodes[:-1]
            for node in upstream_nodes:
                state = node.execute(state)

            # Serialize original HTML docs and other serializable state
            orig = state.get("original_html", [])
            serialized = [
                {"page_content": doc.page_content, "metadata": doc.metadata}
                for doc in orig
            ]
            to_cache = {
                "original_html":  serialized,
                "refined_prompt": state.get("refined_prompt"),
                "html_info":      state.get("html_info"),
                "reduced_html":   state.get("reduced_html"),
                "answer":         state.get("answer"),
            }
            # Write cache (exclude non-serializable vector DB client)
            with open(cache_file, "w") as f:
                json.dump(to_cache, f)

        # 3) run only GenerateCodeNode
        gen_node = next(
            n for n in self.graph.nodes if isinstance(n, GenerateCodeNode)
        )
        final_state = gen_node.execute(state)

        # 4) persist generated code as before
        generated_code = final_state.get("generated_code", "No code created.")
        if self.config.get("filename") is None:
            filename = "extracted_data.py"
        elif ".py" not in self.config.get("filename"):
            filename = self.config.get("filename") + ".py"
        else:
            filename = self.config.get("filename")

        save_code_to_file(generated_code, filename)
        return generated_code