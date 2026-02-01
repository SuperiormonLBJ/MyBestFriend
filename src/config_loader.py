import yaml
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_path: Path = Path('../config.yaml')):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)

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