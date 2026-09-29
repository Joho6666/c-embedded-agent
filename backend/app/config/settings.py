from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    repo_root: Path = REPO_ROOT
    workspace_root: Path = REPO_ROOT / "workspaces"
    template_root: Path = REPO_ROOT / "templates" / "stm32f103_hal_official"
    knowledge_root: Path = REPO_ROOT / "knowledge_sources" / "stm32f103"
    max_agent_iterations: int = 8
    compile_timeout_sec: int = 90
    max_stdout_bytes: int = 200_000

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_max_retries: int = 3
    llm_timeout_sec: float = 90.0

    approval_timeout_sec: int = 3600
    serial_wait_sec: float = 8.0
    tool_result_max_chars: int = 8000
    old_tool_result_chars: int = 1500
    tool_history_keep: int = 4
    os_sync_ttl_sec: float = 30.0

    arm_gcc_path: str = "arm-none-eabi-gcc"
    make_path: str = "make"


settings = Settings()
