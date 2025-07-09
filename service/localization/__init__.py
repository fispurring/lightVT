import json
from typing import Dict, Any
from utils import get_resource_path

_lang = "en"
_config_dir = get_resource_path("assets/localization")
_translations: Dict[str,Any] = None
_default_translations: Dict[str, Any] = None

def init(lang: str = "en", config_dir: str = get_resource_path("assets/localization")) -> None:
    """初始化本地化模块"""
    global _lang, _config_dir, _translations, _default_translations
    _lang = lang
    _config_dir = config_dir
    _translations = load_translations()
    _default_translations = load_default_translations()

def load_translations() -> Dict[str, Any]:
    """加载指定语言的本地化配置文件"""
    global _lang, _config_dir
    try:
        file_path = f"{_config_dir}/{_lang}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"本地化配置文件未找到: {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"本地化配置文件解析失败: {file_path}")
        return {}

def load_default_translations() -> Dict[str, Any]:
    """加载默认语言（英语）的本地化配置文件"""
    global _config_dir
    try:
        file_path = f"{_config_dir}/en.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"默认语言配置文件未找到: {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"默认语言配置文件解析失败: {file_path}")
        return {}

def set_language(lang: str) -> None:
    """设置语言"""
    global _lang, _translations
    _lang = lang
    _translations = load_translations()
    
def get_current_language() -> str:
    """获取当前语言"""
    global _lang
    return _lang

def get(key: str) -> str:
    """获取本地化文本，保底使用英语"""
    global _translations, _default_translations
    return _translations.get(key, _default_translations.get(key, key))

__all__ = [
    "init",
    "set_language",
    "get_current_language",
    "localize"
]