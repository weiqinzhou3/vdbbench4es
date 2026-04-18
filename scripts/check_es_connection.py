import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from elasticsearch import Elasticsearch
from scripts.es_connection_options import build_elasticsearch_options

def check_connection():
    options = build_elasticsearch_options()

    print(f"Connecting to ES hosts: {options['hosts']} as user: {os.getenv('ES_USER', 'elastic')}")
    
    try:
        client = Elasticsearch(**options)
        
        info = client.info()
        print("Successfully connected to Elasticsearch!")
        print(f"Cluster Info: {info}")
        
        # Test index creation
        index_name = "vdbbench_smoke_test_connection"
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
        
        client.indices.create(index=index_name)
        print(f"Successfully created test index: {index_name}")
        
        client.indices.delete(index=index_name)
        print(f"Successfully deleted test index: {index_name}")
        
        return True
    except Exception as e:
        print(f"Failed to connect or perform operations: {e}")
        return False

if __name__ == "__main__":
    if not check_connection():
        sys.exit(1)
