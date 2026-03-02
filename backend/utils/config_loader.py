import yaml
from pathlib import Path
class ConfigLoader:
    def __init__(self, config_path: Path = None):
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'config.yaml'
        self.config_path = Path(config_path)
        self._load()

    def _load(self):
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def reload(self):
        """Reload config from disk."""
        self._load()

    def get_config(self):
        """Get the full config dictionary."""
        return self.config
    
    # Provide easy access to specific config values for other modules
    def get_chunk_size(self):
        return self.config.get('CHUNK_SIZE')
    
    def get_overlap(self):
        return self.config.get('OVERLAP')
    
    def get_top_k(self):
        return self.config.get('TOP_K')
    
    def get_similarity_threshold(self):
        return self.config.get('SIMILARITY_THRESHOLD')
    
    def get_embedding_model(self):
        return self.config.get('EMBEDDING_MODEL')
    
    def get_llm_model(self):
        return self.config.get('LLM_MODEL')
    
    def get_vector_db(self):
        return self.config.get('VECTOR_DB')
    
    def get_db_name(self):
        return self.config.get('DB_NAME')
    
    def get_data_dir(self):
        return self.config.get('DATA_DIR')
    
    def get_generator_model(self):
        return self.config.get('GENERATOR_MODEL')
        
    def get_evaluator_model(self):
        return self.config.get('EVALUATOR_MODEL')

    def get_frontend_config(self) -> dict:
        """Return frontend-facing config (safe to expose via API)."""
        default = {
            "app_name": "MyBestFriend",
            "chat_title": "Digital Twin",
            "chat_subtitle": "Ask anything about me — career, projects, hobbies, or daily life",
            "input_placeholder": "Ask anything about me...",
            "empty_state_hint": "Type a question or use the microphone for voice input",
            "empty_state_examples": 'Try: "What is Beiji\'s experience at UOB?" or "Tell me about his hobbies"',
        }
        frontend = self.config.get("frontend") or {}
        return {**default, **frontend}

    def get_models_config(self) -> dict:
        """Return model selection config."""
        return {
            "embedding_model": self.config.get("EMBEDDING_MODEL", "text-embedding-3-large"),
            "generator_model": self.config.get("GENERATOR_MODEL", "gpt-4o-mini"),
            "llm_model": self.config.get("LLM_MODEL", "gpt-4o-mini"),
            "evaluator_model": self.config.get("EVALUATOR_MODEL", "gpt-4o-mini"),
        }

    def get_full_config(self) -> dict:
        """Return full editable config (frontend + models) for settings UI."""
        return {
            **self.get_frontend_config(),
            **self.get_models_config(),
        }

    def update_and_save(self, updates: dict) -> None:
        """
        Merge updates into config and persist to config.yaml.
        Accepts frontend.* keys and EMBEDDING_MODEL, GENERATOR_MODEL, LLM_MODEL, EVALUATOR_MODEL.
        """
        frontend_updates = {}
        model_keys = {"EMBEDDING_MODEL", "GENERATOR_MODEL", "LLM_MODEL", "EVALUATOR_MODEL"}
        frontend_key_map = {
            "app_name": "app_name",
            "chat_title": "chat_title",
            "chat_subtitle": "chat_subtitle",
            "input_placeholder": "input_placeholder",
            "empty_state_hint": "empty_state_hint",
            "empty_state_examples": "empty_state_examples",
        }
        model_key_map = {
            "embedding_model": "EMBEDDING_MODEL",
            "generator_model": "GENERATOR_MODEL",
            "llm_model": "LLM_MODEL",
            "evaluator_model": "EVALUATOR_MODEL",
        }

        for k, v in updates.items():
            if v is None or v == "":
                continue
            if k in frontend_key_map:
                frontend_updates[k] = v
            elif k in model_key_map:
                self.config[model_key_map[k]] = v
            elif k in model_keys:
                self.config[k] = v

        if frontend_updates:
            frontend = self.config.get("frontend") or {}
            frontend.update(frontend_updates)
            self.config["frontend"] = frontend

        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        self._load()