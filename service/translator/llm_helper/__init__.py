from . import subtitle
from . import plain_text
from typing import Dict, List, Callable, Any, Optional, Tuple, Any
from llama_cpp import Llama

def create_llm(model_path: str, n_gpu_layers: int = 0, n_ctx: int = 4096) -> Any:
    """创建并返回LLM模型实例"""
    return Llama(
        model_path=model_path,
        n_gpu_layers=n_gpu_layers,
        n_ctx=n_ctx
    )