"""
GenerateCodeNode Module
"""

import ast
import json
import re
import sys
from io import StringIO
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from jsonschema import ValidationError as JSONSchemaValidationError
from jsonschema import validate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser

from langchain_openai import OpenAIEmbeddings
from src.defaults import NODE_DEFAULTS

from scrapegraphai.prompts import TEMPLATE_SEMANTIC_COMPARISON
from prompts.crawlee_prompt import DEFAULT_CRAWLEE_TEMPLATE
from scrapegraphai.utils import (
    are_content_equal,
    execution_focused_analysis,
    execution_focused_code_generation,
    extract_code,
    semantic_focused_analysis,
    semantic_focused_code_generation,
    syntax_focused_analysis,
    syntax_focused_code_generation,
    transform_schema,
    validation_focused_analysis,
    validation_focused_code_generation,
)
from scrapegraphai.nodes.base_node import BaseNode
import tempfile, subprocess, os, sys

class GenerateCodeNode(BaseNode):
    """
    A node that generates Python code for a function that extracts data
    from HTML based on a output schema.

    Attributes:
        llm_model: An instance of a language model client, configured for generating answers.
        verbose (bool): A flag indicating whether to show print statements during execution.

    Args:
        input (str): Boolean expression defining the input keys needed from the state.
        output (List[str]): List of output keys to be updated in the state.
        node_config (dict): Additional configuration for the node.
        node_name (str): The unique identifier name for the node, defaulting to "GenerateAnswer".
    """

    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "GenerateCode",
    ):
        super().__init__(node_name, "node", input, output, 2, node_config)

        self.llm_model = node_config.get("llm_model")
        
        for _param in ("temperature", "top_p", "max_tokens", "seed"):
            if _param in node_config and hasattr(self.llm_model, _param):
                setattr(self.llm_model, _param, node_config[_param])

        if isinstance(node_config["llm_model"], ChatOllama):
            self.llm_model.format = "json"

        self.verbose = (
            True if node_config is None else node_config.get("verbose", False)
        )
        self.force = False if node_config is None else node_config.get("force", False)
        self.script_creator = (
            False if node_config is None else node_config.get("script_creator", False)
        )
        self.is_md_scraper = (
            False if node_config is None else node_config.get("is_md_scraper", False)
        )

        self.additional_info = node_config.get("additional_info")

        defaults = NODE_DEFAULTS
        retrieval_cfg = node_config.get("retrieval", defaults["retrieval"])
        self.initial_k = retrieval_cfg.get("initial_k", defaults["retrieval"]["initial_k"])
        self.execution_k = retrieval_cfg.get("execution_k", defaults["retrieval"]["execution_k"])
        self.validation_k = retrieval_cfg.get("validation_k", defaults["retrieval"]["validation_k"])
        self.max_iterations = node_config.get("max_iterations", defaults["max_iterations"])

        self.output_schema = node_config.get("schema")
        self.embedder = node_config.get("embedder_model")

    def execute(self, state: dict) -> dict:
        """
        Generates Python code for a function that extracts data from HTML based on a output schema.

        Args:
            state (dict): The current state of the graph. The input keys will be used
                            to fetch the correct data from the state.

        Returns:
            dict: The updated state with the output key containing the generated answer.

        Raises:
            KeyError: If the input keys are not found in the state, indicating
                      that the necessary information for generating an answer is missing.
            RuntimeError: If the maximum number of iterations is
            reached without obtaining the desired code.
        """

        self.logger.info(f"--- Executing {self.node_name} Node ---")

        user_prompt = state.get("user_prompt")
        refined_prompt = state.get("refined_prompt")
        html_info = state.get("html_info")
        reduced_html = state.get("reduced_html")
        vectorial_db = state.get("vectorial_db")
        answer = state.get("answer")
        self.raw_html = state.get("original_html", [None])[0].page_content if state.get("original_html") else None

        simplefied_schema = str(transform_schema(self.output_schema.schema()))

        reasoning_state = {
            "user_input":       user_prompt,
            "json_schema":      simplefied_schema,
            "initial_analysis": refined_prompt,
            "html_code":        reduced_html,
            "html_analysis":    html_info,
            "vectorial_db":     vectorial_db,
            "generated_code":   "",
            "execution_result": None,
            "reference_answer": answer,
            "errors":           {"syntax": [], "execution": [], "validation": [], "semantic": []},
            "iteration":        0,
        }

        final_state = self.overall_reasoning_loop(reasoning_state)

        state.update({self.output[0]: final_state["generated_code"]})
        return state

    def overall_reasoning_loop(self, state: dict) -> dict:
        """
        Executes the overall reasoning loop to generate and validate the code.

        Args:
            state (dict): The current state of the reasoning process.

        Returns:
            dict: The final state after the reasoning loop.

        Raises:
            RuntimeError: If the maximum number of iterations
            is reached without obtaining the desired code.
        """
        self.logger.info("--- (Generating Code) ---")
        state["generated_code"] = self.generate_initial_code(state)
        state["generated_code"] = extract_code(state["generated_code"])

        while state["iteration"] < self.max_iterations["overall"]:
            state["iteration"] += 1
            if self.verbose:
                self.logger.info(f"--- Iteration {state['iteration']} ---")

            self.logger.info("--- (Checking Code Syntax) ---")
            state = self.syntax_reasoning_loop(state)
            if state["errors"]["syntax"]:
                continue

            self.logger.info("--- (Executing the Generated Code) ---")
            state = self.execution_reasoning_loop(state)
            if state["errors"]["execution"]:
                continue

            # self.logger.info("--- (Validate the Code Output Schema) ---")
            # state = self.validation_reasoning_loop(state)
            # if state["errors"]["validation"]:
            #     continue

            # self.logger.info(
            #     """--- (Checking if the informations exctrcated are the ones Requested) ---"""
            # )
            # state = self.semantic_comparison_loop(state)
            # if state["errors"]["semantic"]:
            #     continue
            break

        if state["iteration"] == self.max_iterations["overall"] and (
            state["errors"]["syntax"]
            or state["errors"]["execution"]
            or state["errors"]["validation"]
            or state["errors"]["semantic"]
        ):
            raise RuntimeError(
                "Max iterations reached without obtaining the desired code."
            )

        self.logger.info("--- (Code Generated Correctly) ---")

        return state

    def syntax_reasoning_loop(self, state: dict) -> dict:
        """
        Executes the syntax reasoning loop to ensure the generated code has correct syntax.

        Args:
            state (dict): The current state of the reasoning process.

        Returns:
            dict: The updated state after the syntax reasoning loop.
        """
        for _ in range(self.max_iterations["syntax"]):
            syntax_valid, syntax_message = self.syntax_check(state["generated_code"])
            if syntax_valid:
                state["errors"]["syntax"] = []
                return state

            state["errors"]["syntax"] = [syntax_message]
            self.logger.info(f"--- (Synax Error Found: {syntax_message}) ---")
            analysis = syntax_focused_analysis(state, self.llm_model)
            self.logger.info(
                """--- (Regenerating Code
                             to fix the Error) ---"""
            )
            state["generated_code"] = syntax_focused_code_generation(
                state, analysis, self.llm_model
            )
            state["generated_code"] = extract_code(state["generated_code"])
        return state

    def execution_reasoning_loop(self, state: dict) -> dict:
        """
        Executes the execution reasoning loop to ensure the generated code runs without errors.
        """
        for _ in range(self.max_iterations["execution"]):
            code = state["generated_code"]
            
            try:
                with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
                    tmp.write(code)
                    tmp_path = tmp.name

                proc = subprocess.Popen(
                    [sys.executable, tmp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                try:
                    output_lines = []
                    for line in proc.stdout:
                        output_lines.append(line)
                    
                    proc.wait(timeout=60)

                except subprocess.TimeoutExpired:
                    proc.kill()
                    state["errors"]["execution"] = ["Execution timed out."]
                    self.logger.info("--- (Code Execution Error: Execution timed out) ---")
                    continue

                full_output = ''.join(output_lines)

                if proc.returncode == 0:
                    if "ERROR" in full_output:
                        err = full_output.strip()
                        state["errors"]["execution"] = [err]
                        self.logger.info(f"--- (Code Execution Error) ---")
                    else:
                        state["execution_result"] = full_output.strip()
                        state["errors"]["execution"] = []
                        return state  # SUCCESS
                else:
                    err = full_output.strip()
                    state["errors"]["execution"] = [err]
                    self.logger.info(f"--- (Code Execution Error) ---")

            except Exception as exc:
                err = str(exc)
                state["errors"]["execution"] = [err]
                self.logger.info(f"--- (Code Execution Exception) ---")

            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            execution_error_text = "\n".join(state["errors"]["execution"])

            query_rewrite_prompt = PromptTemplate(
                template=(
                    '''
                    Given the following context:\n\n
                    - html analysis: \n{html_analysis}\n
                    - execution error: \n{execution_error}\n\n
                    Write a concise technical query (max 1-2 sentences) that retrieves relevant documentation or code examples \
                    from a vector database that stores Python web scraping library (Crawlee) documentation. This will be used to help a LLM resolve an error that occured during execution. \
                    The query must be Only return the prompt as it will be directly used as a query for the database.
                    '''
                ),
                partial_variables={
                    "html_analysis": state["html_analysis"],
                    "execution_error": execution_error_text,
                },
            )

            chain = query_rewrite_prompt | self.llm_model | StrOutputParser()
            vector_query = chain.invoke({})

            embedder = self.node_config.get("embedder_model") or OpenAIEmbeddings()
            query_vector = embedder.embed_query(vector_query)
            client = state["vectorial_db"]
            hits = client.search(
                collection_name="vectorial_collection",
                query_vector=query_vector,
                limit=self.execution_k,
            )
            snippets = [h.payload.get("text", "") for h in hits]

            crawlee_snippet = (
                f"\n\n*HITS FROM VECTOR DATABASE (QUERY: '{vector_query}')*:\n"
                + "\n\n".join(snippets)
            )

            analysis_text = execution_focused_analysis(state, self.llm_model)
            analysis = f"{crawlee_snippet}\n\n{analysis_text}"

            self.logger.info("--- (Regenerating Code to fix the Error) ---")
            state["generated_code"] = execution_focused_code_generation(state, analysis, self.llm_model)
            state["generated_code"] = extract_code(state["generated_code"])

        return state


    def validation_reasoning_loop(self, state: dict) -> dict:
        """
        Executes the validation reasoning loop to ensure the
        generated code's output matches the desired schema.
        """
        storage_dir = os.path.join(os.getcwd(), "storage", "datasets", "default")
        try:
            files = [
                f for f in os.listdir(storage_dir)
                if f.endswith(".json") and f != "__metadata__.json"
            ]
        except Exception as e:
            state["errors"]["validation"] = [f"Failed to list output files: {e}"]
            return state

        if not files:
            state["errors"]["validation"] = ["No output files found in dataset"]
            return state

        data_items: List[Any] = []
        for fname in files:
            try:
                with open(os.path.join(storage_dir, fname), "r") as f:
                    data_items.append(json.load(f))
            except Exception as e:
                state["errors"]["validation"] = [f"Failed to load '{fname}': {e}"]
                return state

        result_data = data_items[0] if len(data_items) == 1 else data_items
        state["execution_result"] = result_data

        for _ in range(self.max_iterations["validation"]):
            validation, errors = self.validate_dict(
                state["execution_result"], self.output_schema.schema()
            )
            if validation:
                state["errors"]["validation"] = []
                return state

            state["errors"]["validation"] = errors
            self.logger.info(
                "--- (Code Output not compliant to the desired Output Schema) ---"
            )
            
            validation_error_text = "\n".join(state["errors"]["validation"])

            query_rewrite_prompt = PromptTemplate(
                template=(
                    '''
                    Given the following context:\n\n
                    - html analysis: \n{html_analysis}\n
                    - validation error: \n{validation_error}\n\n
                    Write a concise technical query (max 1-2 sentences) that retrieves relevant documentation or code examples \
                    from a vector database that stores Python web scraping library (Crawlee) documentation. This will be used to help a LLM resolve an error that occured during execution. \
                    The query must be Only return the prompt as it will be directly used as a query for the database.
                    '''
                ),
                partial_variables={
                    "html_analysis": state["html_analysis"],
                    "validation_error": validation_error_text,
                },
            )
            
            chain = query_rewrite_prompt | self.llm_model | StrOutputParser()
            vector_query = chain.invoke({})

            embedder = self.node_config.get("embedder_model") or OpenAIEmbeddings()
            query_vector = embedder.embed_query(vector_query)
            client = state["vectorial_db"]
            hits = client.search(
                collection_name="vectorial_collection",
                query_vector=query_vector,
                limit=self.validation_k,
            )
            snippets = [h.payload.get("text", "") for h in hits]

            crawlee_snippet = (
                f"\n\n*HITS FROM VECTOR DATABASE (QUERY: '{vector_query}')*:\n"
                + "\n\n".join(snippets)
            )
            
            analysis = validation_focused_analysis(state, self.llm_model)
            # analysis = f"{crawlee_snippet}\n\n{analysis_text}"

            self.logger.info(
                "--- (Regenerating Code to make the Output compliant) ---"
            )
            state["generated_code"] = validation_focused_code_generation(
                state, analysis, self.llm_model
            )
            state["generated_code"] = extract_code(state["generated_code"])

        return state

    def semantic_comparison_loop(self, state: dict) -> dict:
        """
        Executes the semantic comparison loop to ensure the generated code's
          output is semantically equivalent to the reference answer.

        Args:
            state (dict): The current state of the reasoning process.

        Returns:
            dict: The updated state after the semantic comparison loop.
        """
        for _ in range(self.max_iterations["semantic"]):
            comparison_result = self.semantic_comparison(
                state["execution_result"], state["reference_answer"]
            )
            if comparison_result["are_semantically_equivalent"]:
                state["errors"]["semantic"] = []
                return state

            state["errors"]["semantic"] = comparison_result["differences"]
            self.logger.info(
                """--- (The informations exctrcated
                             are not the all ones requested) ---"""
            )
            analysis = semantic_focused_analysis(
                state, comparison_result, self.llm_model
            )
            self.logger.info(
                """--- (Regenerating Code to
                                obtain all the infromation requested) ---"""
            )
            state["generated_code"] = semantic_focused_code_generation(
                state, analysis, self.llm_model
            )
            state["generated_code"] = extract_code(state["generated_code"])
        return state

    def generate_initial_code(self, state: dict) -> str:
        """
        Generates the initial code based on the provided state, using LLM-assisted query rewriting for vector search.
        """

        query_rewrite_prompt = PromptTemplate(
            template=(
                '''
                Given the following:\n\n
                - user prompt: \n{user_input}\n
                - html analysis: \n{html_analysis}\n
                - json schema: \n{json_schema}\n\n
                Write a concise technical query (max 1-2 sentences) that retrieves relevant documentation or code examples \
                from a vector database that stores Python web scraping library (Crawlee) documentation. This will be used to help a LLM generate a scraping function. \
                The query must be Only return the prompt as it will be directly used as a query for the database.
                '''
            ),
            partial_variables={
                "user_input"        : state["user_input"], 
                "html_analysis"     : state["html_analysis"], 
                "json_schema"       : state["json_schema"]
                },
        )
        
        output_parser = StrOutputParser()
        chain = query_rewrite_prompt | self.llm_model | output_parser
        vector_query = chain.invoke({})
        
        embedder = self.node_config.get("embedder_model") or OpenAIEmbeddings()
        query_vector = embedder.embed_query(vector_query)
        client = state["vectorial_db"]
        hits = client.search(
            collection_name="vectorial_collection",
            query_vector=query_vector,
            limit=self.initial_k,
        )
        snippets = [h.payload.get("text", "") for h in hits]

        crawlee_snippet = (
            "\n\n*HITS FROM VECTOR DATABASE (QUERY: '{}')*:\n".format(vector_query)
            + "\n\n".join(snippets)
        )

        prompt = PromptTemplate(
            template=DEFAULT_CRAWLEE_TEMPLATE,
            partial_variables={
                "user_input":       state["user_input"],
                "json_schema":      state["json_schema"],
                "initial_analysis": state["initial_analysis"],
                "html_code":        state["html_code"],
                "html_analysis":    state["html_analysis"],
                "crawlee_snippet":  crawlee_snippet,
            },
        )
        output_parser = StrOutputParser()
        chain = prompt | self.llm_model | output_parser
        generated_code = chain.invoke({})

        return generated_code


    def semantic_comparison(
        self, generated_result: Any, reference_result: Any
    ) -> Dict[str, Any]:
        """
        Performs a semantic comparison between the generated result and the reference result.

        Args:
            generated_result (Any): The result generated by the code.
            reference_result (Any): The reference result for comparison.

        Returns:
            Dict[str, Any]: A dictionary containing the comparison result,
            differences, and explanation.
        """
        reference_result_dict = self.output_schema(**reference_result).dict()
        if are_content_equal(generated_result, reference_result_dict):
            return {
                "are_semantically_equivalent": True,
                "differences": [],
                "explanation": "The generated result and reference result are exactly equal.",
            }

        response_schemas = [
            ResponseSchema(
                name="are_semantically_equivalent",
                description="""Boolean indicating if the
                           results are semantically equivalent""",
            ),
            ResponseSchema(
                name="differences",
                description="""List of semantic differences
                           between the results, if any""",
            ),
            ResponseSchema(
                name="explanation",
                description="""Detailed explanation of the
                           comparison and reasoning""",
            ),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

        prompt = PromptTemplate(
            template=TEMPLATE_SEMANTIC_COMPARISON,
            input_variables=["generated_result", "reference_result"],
            partial_variables={
                "format_instructions": output_parser.get_format_instructions()
            },
        )

        chain = prompt | self.llm_model | output_parser
        return chain.invoke(
            {
                "generated_result": json.dumps(generated_result, indent=2),
                "reference_result": json.dumps(reference_result_dict, indent=2),
            }
        )

    def syntax_check(self, code):
        """
        Checks the syntax of the provided code.

        Args:
            code (str): The code to be checked for syntax errors.

        Returns:
            tuple: A tuple containing a boolean indicating if the syntax is correct and a message.
        """
        try:
            ast.parse(code)
            return True, "Syntax is correct."
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"

    def create_sandbox_and_execute(self, function_code):
        """
        Creates a sandbox environment and executes the provided function code.

        Args:
            function_code (str): The code to be executed in the sandbox.

        Returns:
            tuple: A tuple containing a boolean indicating if
            the execution was successful and the result or error message.
        """
        sandbox_globals = {
            "BeautifulSoup": BeautifulSoup,
            "re": re,
            "__builtins__": __builtins__,
        }

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            exec(function_code, sandbox_globals)

            extract_data = sandbox_globals.get("extract_data")

            if not extract_data:
                raise NameError(
                    "Function 'extract_data' not found in the generated code."
                )

            result = extract_data(self.raw_html)
            return True, result
        except Exception as e:
            return False, f"Error during execution: {str(e)}"
        finally:
            sys.stdout = old_stdout

    def validate_dict(self, data: dict, schema):
        """
        Validates the provided data against the given schema.

        Args:
            data (dict): The data to be validated.
            schema (dict): The schema against which the data is validated.

        Returns:
            tuple: A tuple containing a boolean indicating
            if the validation was successful and a list of errors if any.
        """
        try:
            validate(instance=data, schema=schema)
            return True, None
        except JSONSchemaValidationError as e:
            errors = [e.message]
            return False, errors
