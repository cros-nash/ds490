"""
RAGNode Module
"""

from typing import List, Optional

from scrapegraphai.nodes.base_node import BaseNode

from langchain_community.document_loaders import DirectoryLoader

class RAGNode(BaseNode):
    """
    A node responsible for compressing the input tokens and storing the document
    in a vector database for retrieval. Relevant chunks are stored in the state.

    It allows scraping of big documents without exceeding the token limit of the language model.

    Attributes:
        llm_model: An instance of a language model client, configured for generating answers.
        verbose (bool): A flag indicating whether to show print statements during execution.

    Args:
        input (str): Boolean expression defining the input keys needed from the state.
        output (List[str]): List of output keys to be updated in the state.
        node_config (dict): Additional configuration for the node.
        node_name (str): The unique identifier name for the node, defaulting to "Parse".
    """

    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "RAG",
    ):
        super().__init__(node_name, "node", input, output, 2, node_config)

        self.llm_model = node_config["llm_model"]
        self.embedder_model = node_config.get("embedder_model", None)
        self.verbose = (
            False if node_config is None else node_config.get("verbose", False)
        )
        self.input = input

    def execute(self, state: dict) -> dict:
        self.logger.info(f"--- Executing {self.node_name} Node ---")

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, PointStruct, VectorParams
        except ImportError:
            raise ImportError(
                "qdrant_client is not installed. Please install it using 'pip install qdrant-client'."
            )

        if self.node_config.get("client_type") in ["memory", None]:
            client = QdrantClient(":memory:")
        elif self.node_config.get("client_type") == "local_db":
            client = QdrantClient(path="databases/crawlee_db")
        elif self.node_config.get("client_type") == "image":
            client = QdrantClient(url="http://localhost:6333")
        else:
            raise ValueError("client_type provided not correct")
        
        loader = DirectoryLoader("docs/crawlee", glob="**/*.mdx", show_progress=True)
        all_docs = loader.load()
        filtered_docs = []
        for doc in all_docs:
            src = None
            if hasattr(doc, "source"):
                src = doc.source
            elif hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                src = doc.metadata.get("source")
            if isinstance(src, str) and src.endswith(".mdx"):
                filtered_docs.append(doc)
        docs = [doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in filtered_docs]
        
        embedder = self.embedder_model
        if embedder is None:
            raise ValueError("No embedder_model provided for RAGNode.")
        vectors = embedder.embed_documents(docs)

        points = [
            PointStruct(id=i, vector=vec, payload={"text": doc})
            for i, (vec, doc) in enumerate(zip(vectors, docs), start=1)
        ]
        collection_name = "vectorial_collection"
        
        client.recreate_collection(
            collection_name,
            vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
        )
        
        client.upsert(collection_name=collection_name, points=points)

        state["vectorial_db"] = client
        return state
