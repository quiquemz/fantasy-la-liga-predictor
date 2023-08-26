import os
import json

# Defining Cache Manager
class CacheManager:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir

        # creaete cache dir if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def get_from_cache(self, cache_file):
        cache_path = os.path.join(self.cache_dir, cache_file)
        if os.path.isfile(cache_path):
            with open(cache_path) as f:
                return json.load(f)
        return None

    def write_to_cache(self, cache_file, data):
        cache_path = os.path.join(self.cache_dir, cache_file)
        with open(cache_path, 'w') as f:
            f.write(json.dumps(data))