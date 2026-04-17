import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from elasticsearch import Elasticsearch

def check_connection():
    hosts = os.getenv("ES_HOSTS", "http://localhost:9200").split(",")
    user = os.getenv("ES_USER", "elastic")
    password = os.getenv("ES_PASSWORD", "")
    verify_certs = os.getenv("ES_VERIFY_CERTS", "False").lower() == "true"

    print(f"Connecting to ES hosts: {hosts} as user: {user}")
    
    try:
        if user and password:
            client = Elasticsearch(
                hosts=hosts,
                basic_auth=(user, password),
                verify_certs=verify_certs
            )
        else:
            client = Elasticsearch(
                hosts=hosts,
                verify_certs=verify_certs
            )
        
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
