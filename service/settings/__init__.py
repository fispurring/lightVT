# settings.py
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import partial

# 默认配置常量
DEFAULT_CONFIG = {
    "last_input_path": "",
    "last_output_path": "",
    "last_model_path": "",
    "last_source_lang": "auto",
    "last_target_lang": "zh-CN",
    "last_gpu_layers": -1,
    "window_geometry": "750x650",
    "appearance_mode": "系统",
    "reflection_enabled": True,
    "processing_mode": "translate",
}

# 默认配置文件路径
DEFAULT_CONFIG_FILE = "config.json"

# 模块内部状态 - 不对外公开
_config: Dict[str, Any] = {}
_config_file: str = DEFAULT_CONFIG_FILE
_initialized: bool = False

# 内部工具函数
def _get_config_path(config_file: Optional[str] = None) -> Path:
    """获取配置文件路径"""
    return Path(config_file or _config_file)

def _read_json_file(file_path: Path) -> Dict[str, Any]:
    """读取JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"读取配置文件失败: {e}")
        return {}

def _write_json_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """写入JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False

def _merge_configs(default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
    """合并配置，确保所有默认键都存在"""
    return {**default, **loaded}

def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证并修复配置"""
    validated = DEFAULT_CONFIG.copy()
    
    for key, default_value in DEFAULT_CONFIG.items():
        if key in config:
            if type(config[key]) == type(default_value):
                validated[key] = config[key]
            else:
                print(f"配置项 {key} 类型不匹配，使用默认值")
                validated[key] = default_value
        else:
            validated[key] = default_value
    
    return validated

def _ensure_initialized():
    """确保配置已初始化"""
    global _config, _initialized
    if not _initialized:
        initialize()

def _load_from_file() -> Dict[str, Any]:
    """从文件加载配置"""
    config_path = _get_config_path()
    
    if config_path.exists():
        loaded_config = _read_json_file(config_path)
        return _merge_configs(DEFAULT_CONFIG, loaded_config)
    else:
        return DEFAULT_CONFIG.copy()

def _save_to_file() -> bool:
    """保存配置到文件"""
    config_path = _get_config_path()
    return _write_json_file(config_path, _config)

# 公共API函数
def initialize(config_file: Optional[str] = None) -> None:
    """初始化配置模块"""
    global _config, _config_file, _initialized
    
    if config_file:
        _config_file = config_file
    
    _config = _validate_config(_load_from_file())
    _initialized = True

def get_value(key: str, default: Any = None) -> Any:
    """获取配置值"""
    _ensure_initialized()
    return _config.get(key, default)

def set_value(key: str, value: Any) -> bool:
    """设置配置值"""
    global _config
    _ensure_initialized()
    
    if key in DEFAULT_CONFIG:
        # 类型检查
        expected_type = type(DEFAULT_CONFIG[key])
        if expected_type != type(None) and not isinstance(value, expected_type):
            print(f"警告: {key} 期望类型 {expected_type.__name__}，得到 {type(value).__name__}")
            return False
        
        _config = {**_config, key: value}
        save()
        return True
    else:
        print(f"警告: 未知配置项 {key}")
        return False

def update_values(updates: Dict[str, Any]) -> bool:
    """批量更新配置值"""
    global _config
    _ensure_initialized()
    
    valid_updates = {}
    for key, value in updates.items():
        if key in DEFAULT_CONFIG:
            expected_type = type(DEFAULT_CONFIG[key])
            if expected_type != type(None) and not isinstance(value, expected_type):
                print(f"警告: {key} 类型不匹配，跳过")
                continue
            valid_updates[key] = value
        else:
            print(f"警告: 未知配置项 {key}，跳过")
    
    if valid_updates:
        _config = {**_config, **valid_updates}
        return True
    return False

def save() -> bool:
    """保存当前配置到文件"""
    _ensure_initialized()
    return _save_to_file()

def reset() -> bool:
    """重置配置为默认值"""
    global _config
    _config = DEFAULT_CONFIG.copy()
    return _save_to_file()

def reload() -> None:
    """重新加载配置文件"""
    global _config
    _config = _validate_config(_load_from_file())

def get_last_directory(path_key: str) -> str:
    """获取上次使用的目录"""
    _ensure_initialized()
    last_path = get_value(path_key, "")
    if last_path and os.path.exists(last_path):
        return str(Path(last_path).parent)
    return ""

def auto_set_output_path(input_path: str, target_lang: str) -> str:
    """自动设置输出路径"""
    if not input_path:
        return ""
    
    input_path_obj = Path(input_path)
    suffix = f".{target_lang}.srt"
    output_path = input_path_obj.parent / f"{input_path_obj.stem}{suffix}"
    
    return str(output_path)

def apply_language_preset(preset_name: str) -> bool:
    """应用语言预设"""
    presets = {
        "中英": {"last_source_lang": "英语", "last_target_lang": "简体中文"},
        "英中": {"last_source_lang": "简体中文", "last_target_lang": "英语"},
        "日中": {"last_source_lang": "日语", "last_target_lang": "简体中文"},
        "韩中": {"last_source_lang": "韩语", "last_target_lang": "简体中文"}
    }
    
    if preset_name in presets:
        return update_values(presets[preset_name])
    return False

# 便捷函数
def get_input_path() -> str:
    """获取输入路径"""
    return get_value("last_input_path", "")

def set_input_path(path: str) -> bool:
    """设置输入路径"""
    return set_value("last_input_path", path)

def get_output_path() -> str:
    """获取输出路径"""
    return get_value("last_output_path", "")

def set_output_path(path: str) -> bool:
    """设置输出路径"""
    return set_value("last_output_path", path)

def get_model_path() -> str:
    """获取模型路径"""
    return get_value("last_model_path", "")

def set_model_path(path: str) -> bool:
    """设置模型路径"""
    return set_value("last_model_path", path)

def get_source_language() -> str:
    """获取源语言"""
    return get_value("last_source_lang", "auto")

def set_source_language(lang: str) -> bool:
    """设置源语言"""
    return set_value("last_source_lang", lang)

def get_target_language() -> str:
    """获取目标语言"""
    return get_value("last_target_lang", "zh-CN")

def set_target_language(lang: str) -> bool:
    """设置目标语言"""
    return set_value("last_target_lang", lang)

def get_gpu_layers() -> int:
    """获取GPU层数"""
    return get_value("last_gpu_layers", 0)

def set_gpu_layers(layers: int) -> bool:
    """设置GPU层数"""
    return set_value("last_gpu_layers", layers)

def get_window_geometry() -> str:
    """获取窗口几何信息"""
    return get_value("window_geometry", "750x650")

def set_window_geometry(geometry: str) -> bool:
    """设置窗口几何信息"""
    return set_value("window_geometry", geometry)

def get_appearance_mode() -> str:
    """获取外观模式"""
    return get_value("appearance_mode", "系统")

def set_appearance_mode(mode: str) -> bool:
    """设置外观模式"""
    return set_value("appearance_mode", mode)

def get_reflection_enabled():
    """获取反思设置"""
    return get_value("reflection_enabled", True)

def set_reflection_enabled(enabled: bool):
    """设置反思开关"""
    return set_value("reflection_enabled", enabled)

def get_interface_language() -> str:
    """获取界面语言"""
    return get_value("interface_language", "English")
def set_interface_language(language: str) -> bool:
    """设置界面语言"""
    return set_value("interface_language", language)

def get_processing_mode() -> str:
    """获取处理模式"""
    return get_value("processing_mode", "translate")

def set_processing_mode(mode: str) -> bool:
    """设置处理模式"""
    return set_value("processing_mode", mode)

# 高级功能
def create_backup(backup_file: str) -> bool:
    """创建配置备份"""
    _ensure_initialized()
    backup_path = Path(backup_file)
    return _write_json_file(backup_path, _config)

def restore_from_backup(backup_file: str) -> bool:
    """从备份恢复配置"""
    global _config
    backup_path = Path(backup_file)
    if backup_path.exists():
        backup_config = _read_json_file(backup_path)
        _config = _validate_config(backup_config)
        return save()
    return False

def export_config() -> Dict[str, Any]:
    """导出配置的副本（只读）"""
    _ensure_initialized()
    return _config.copy()

def get_config_info() -> Dict[str, Any]:
    """获取配置信息"""
    _ensure_initialized()
    config_path = _get_config_path()
    return {
        "config_file": str(config_path),
        "file_exists": config_path.exists(),
        "initialized": _initialized,
        "total_keys": len(_config),
        "default_keys": len(DEFAULT_CONFIG)
    }

# 导出的公共API
__all__ = [
    'initialize',
    'get_value', 'set_value', 'update_values',
    'save', 'reset', 'reload',
    'get_last_directory', 'auto_set_output_path', 'apply_language_preset',
    'get_input_path', 'set_input_path',
    'get_output_path', 'set_output_path', 
    'get_model_path', 'set_model_path',
    'get_source_language', 'set_source_language',
    'get_target_language', 'set_target_language',
    'get_gpu_layers', 'set_gpu_layers',
    'get_window_geometry', 'set_window_geometry',
    'get_appearance_mode', 'set_appearance_mode',
    'create_backup', 'restore_from_backup',
    'export_config', 'get_config_info'
]