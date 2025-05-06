"""
Default configuration values for nodes.
This file centralizes magic numbers such as retrieval limits and iteration counts.
"""

NODE_DEFAULTS = {
    # Retrieval settings for GenerateCodeNode
    "retrieval": {
        # number of top snippets to retrieve for initial code generation
        "initial_k": 2,
        # number of top snippets to retrieve for execution error analysis
        "execution_k": 12,
        # number of top snippets to retrieve for validation error analysis
        "validation_k": 4,
    },
    # Default iteration counts for reasoning loops
    "max_iterations": {
        "overall": 10,
        "syntax": 3,
        "execution": 3,
        "validation": 3,
        "semantic": 3,
    },
}