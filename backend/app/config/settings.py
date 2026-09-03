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

    arm_gcc_path: str = "arm-none-eabi-gcc"
    make_path: str = "make"


settings = Settings()
