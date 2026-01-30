import yaml
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_path: Path = Path('config.yaml')):
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
        return self.config.get('chunk_size')
    
    def get_overlap(self):
        return self.config.get('overlap')
    
    def get_top_k(self):
        return self.config.get('top_k')
    
    def get_similarity_threshold(self):
        return self.config.get('similarity_threshold')
    
    def get_embedding_model(self):
        return self.config.get('embedding_model')
    
    def get_llm_model(self):
        return self.config.get('llm_model')
    
    def get_vector_db(self):
        return self.config.get('vector_db')