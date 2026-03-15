import yaml
from pathlib import Path


class ConfigLoader:
    def __init__(self, config_path: Path = None):
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'config.yaml'
        self.config_path = Path(config_path)
        # Load YAML as baseline defaults, then overlay with Supabase.
        # If no Supabase rows exist yet, seed them from the YAML values.
        self._load_yaml()
        self._init_from_supabase()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_yaml(self) -> None:
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _config_to_rows(self) -> list[dict]:
        """
        Flatten self.config into individual {key, value} rows for Supabase.
        Frontend subkeys are stored as 'frontend.<key>' (e.g. 'frontend.app_name').
        Each value is stored as-is (Supabase jsonb preserves types).
        """
        rows = []
        for k, v in self.config.items():
            if k == "frontend" and isinstance(v, dict):
                for fk, fv in v.items():
                    rows.append({"key": f"frontend.{fk}", "value": fv})
            else:
                rows.append({"key": k, "value": v})
        return rows

    def _rows_to_config(self, rows: list[dict]) -> dict:
        """
        Reconstruct a config dict from a list of {key, value} Supabase rows.
        'frontend.*' keys are nested back under config['frontend'].
        """
        config: dict = {}
        frontend: dict = {}
        for row in rows:
            k = row["key"]
            v = row["value"]
            if k.startswith("frontend."):
                frontend[k[len("frontend."):]] = v
            else:
                config[k] = v
        if frontend:
            config["frontend"] = frontend
        return config

    def _apply_remote(self, remote: dict) -> None:
        """Merge a remote config dict over self.config in-place."""
        for k, v in remote.items():
            if k == "frontend" and isinstance(v, dict):
                local_fe = self.config.get("frontend") or {}
                local_fe.update(v)
                self.config["frontend"] = local_fe
            else:
                self.config[k] = v

    # ------------------------------------------------------------------
    # Supabase sync
    # ------------------------------------------------------------------

    def _init_from_supabase(self) -> None:
        """
        Pull all key-value rows from Supabase and overlay on YAML defaults.
        If the table is empty, seed it from the current YAML values.
        Non-fatal — falls back to YAML-only if Supabase is unreachable.
        """
        try:
            from utils.supabase_client import supabase_client
            result = supabase_client.table("app_config").select("key, value").execute()
            rows = result.data or []
            if rows:
                self._apply_remote(self._rows_to_config(rows))
            else:
                seed_rows = self._config_to_rows()
                supabase_client.table("app_config").upsert(
                    seed_rows, on_conflict="key"
                ).execute()
                print("[config_loader] Seeded Supabase app_config from config.yaml")
        except Exception as e:
            print(f"[config_loader] Supabase init warning (non-fatal, using YAML): {e}")

    def _push_to_supabase(self) -> None:
        """Upsert all config key-value rows to Supabase. Non-fatal."""
        try:
            from utils.supabase_client import supabase_client
            rows = self._config_to_rows()
            supabase_client.table("app_config").upsert(
                rows, on_conflict="key"
            ).execute()
        except Exception as e:
            print(f"[config_loader] Supabase push warning (non-fatal): {e}")

    def reload(self) -> None:
        """Reload YAML baseline, then overlay latest rows from Supabase."""
        self._load_yaml()
        try:
            from utils.supabase_client import supabase_client
            result = supabase_client.table("app_config").select("key, value").execute()
            rows = result.data or []
            if rows:
                self._apply_remote(self._rows_to_config(rows))
        except Exception as e:
            print(f"[config_loader] Supabase reload warning (non-fatal): {e}")

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        return self.config

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

    def get_rewrite_model(self):
        return self.config.get('REWRITE_MODEL', 'gpt-4o-mini')

    def get_reranker_model(self):
        return self.config.get('RERANKER_MODEL', 'gpt-4o-mini')

    def get_data_dir(self):
        return self.config.get('DATA_DIR')

    def get_generator_model(self):
        return self.config.get('GENERATOR_MODEL')

    def get_evaluator_model(self):
        return self.config.get('EVALUATOR_MODEL')

    def get_recipient_email(self) -> str:
        return self.config.get('RECIPIENT_EMAIL', '')

    def get_hybrid_search_enabled(self) -> bool:
        return bool(self.config.get('HYBRID_SEARCH_ENABLED', True))

    def get_lexical_weight(self) -> float:
        return float(self.config.get('LEXICAL_WEIGHT', 0.3))

    def get_metadata_filter_enabled(self) -> bool:
        return bool(self.config.get('METADATA_FILTER_ENABLED', True))

    def get_self_check_enabled(self) -> bool:
        return bool(self.config.get('SELF_CHECK_ENABLED', False))

    def get_multi_step_enabled(self) -> bool:
        return bool(self.config.get('MULTI_STEP_ENABLED', False))

    def get_use_graph(self) -> bool:
        return bool(self.config.get('USE_GRAPH', False))

    def get_admin_api_key(self) -> str:
        return str(self.config.get('ADMIN_API_KEY', ''))

    def get_owner_id(self) -> str:
        """
        Logical owner identifier — used as a namespace for multi-tenant deployments.
        Defaults to 'default' so single-owner setups require no changes.
        """
        return str(self.config.get('OWNER_ID', 'default'))

    def get_cover_letter_word_limit(self) -> int:
        """Default word limit for cover letter generation. Defaults to 400."""
        val = self.config.get('COVER_LETTER_WORD_LIMIT', 400)
        try:
            return max(100, min(1500, int(val)))
        except (TypeError, ValueError):
            return 400

    def get_frontend_config(self) -> dict:
        """Return frontend-facing config (safe to expose via API)."""
        default = {
            "app_name": "MyBestFriend",
            "owner_name": "Beiji",
        }
        frontend = self.config.get("frontend") or {}
        return {**default, **frontend}

    def get_models_config(self) -> dict:
        return {
            "embedding_model": self.config.get("EMBEDDING_MODEL", "text-embedding-3-large"),
            "generator_model": self.config.get("GENERATOR_MODEL", "gpt-4o-mini"),
            "llm_model": self.config.get("LLM_MODEL", "gpt-4o-mini"),
            "rewrite_model": self.config.get("REWRITE_MODEL", "gpt-4o-mini"),
            "reranker_model": self.config.get("RERANKER_MODEL", "gpt-4o-mini"),
            "evaluator_model": self.config.get("EVALUATOR_MODEL", "gpt-4o-mini"),
        }

    def get_retrieval_config(self) -> dict:
        return {
            "hybrid_search_enabled": self.get_hybrid_search_enabled(),
            "lexical_weight": self.get_lexical_weight(),
            "metadata_filter_enabled": self.get_metadata_filter_enabled(),
            "self_check_enabled": self.get_self_check_enabled(),
            "multi_step_enabled": self.get_multi_step_enabled(),
            "use_graph": self.get_use_graph(),
        }

    def get_full_config(self) -> dict:
        """Return full editable config (frontend + models) for settings UI."""
        return {
            **self.get_frontend_config(),
            **self.get_models_config(),
            **self.get_retrieval_config(),
            "recipient_email": self.get_recipient_email(),
        }

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------

    def update_and_save(self, updates: dict) -> None:
        """
        Merge updates into the in-memory config and persist individual rows to Supabase.
        Accepts frontend.* keys, model keys, and recipient_email.
        config.yaml is NOT modified — Supabase is the source of truth at runtime.
        """
        frontend_keys = {"app_name", "owner_name"}
        model_key_map = {
            "embedding_model": "EMBEDDING_MODEL",
            "generator_model": "GENERATOR_MODEL",
            "llm_model": "LLM_MODEL",
            "rewrite_model": "REWRITE_MODEL",
            "reranker_model": "RERANKER_MODEL",
            "evaluator_model": "EVALUATOR_MODEL",
        }
        retrieval_key_map = {
            "hybrid_search_enabled": "HYBRID_SEARCH_ENABLED",
            "lexical_weight": "LEXICAL_WEIGHT",
            "metadata_filter_enabled": "METADATA_FILTER_ENABLED",
            "self_check_enabled": "SELF_CHECK_ENABLED",
            "multi_step_enabled": "MULTI_STEP_ENABLED",
            "use_graph": "USE_GRAPH",
            "admin_api_key": "ADMIN_API_KEY",
        }

        frontend_updates: dict = {}
        for k, v in updates.items():
            if v is None or v == "":
                continue
            if k in frontend_keys:
                frontend_updates[k] = v
            elif k in model_key_map:
                self.config[model_key_map[k]] = v
            elif k in retrieval_key_map:
                self.config[retrieval_key_map[k]] = v
            elif k == "recipient_email":
                self.config["RECIPIENT_EMAIL"] = v

        if frontend_updates:
            frontend = self.config.get("frontend") or {}
            frontend.update(frontend_updates)
            self.config["frontend"] = frontend

        self._push_to_supabase()
