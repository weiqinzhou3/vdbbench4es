import os
import sys
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from pydantic import SecretStr

# Ensure project root is discoverable
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

from vectordb_bench.backend.clients.elastic_cloud.config import ElasticCloudConfig, ElasticCloudIndexConfig, ESElementType
from vectordb_bench.backend.clients import DB
from vectordb_bench.backend.cases import CaseType, PerformanceCase
from vectordb_bench.models import TaskConfig, CaseConfig, TaskStage
from vectordb_bench.backend.task_runner import CaseRunner, RunningStatus
from vectordb_bench.backend.data_source import DatasetSource
from vectordb_bench.backend.clients.api import IndexType
from vectordb_bench.backend.dataset import DatasetWithSizeType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vdbbench_builtin_verify")

def monkey_patch_elastic_config():
    def to_dict(self) -> dict:
        load_dotenv()
        hosts = os.getenv("ES_HOSTS", "http://localhost:9200").split(",")
        user = os.getenv("ES_USER", "elastic")
        password = os.getenv("ES_PASSWORD", "")
        verify_certs = os.getenv("ES_VERIFY_CERTS", "False").lower() == "true"
        d = {"hosts": hosts, "verify_certs": verify_certs}
        if user and password:
            d["basic_auth"] = (user, password)
        return d
    ElasticCloudConfig.to_dict = to_dict
    logger.info("Monkey-patched ElasticCloudConfig.to_dict for self-hosted ES")

def run_builtin_validation(dataset_type: DatasetWithSizeType):
    logger.info(f"Starting validation for builtin dataset: {dataset_type.name}")
    
    # 1. Configs
    db_config = ElasticCloudConfig(
        db_label=f"builtin_verify_{dataset_type.name}",
        cloud_id=SecretStr("fake"),
        password=SecretStr("fake")
    )
    
    db_case_config = ElasticCloudIndexConfig(
        index=IndexType.ES_HNSW,
        M=16,
        efConstruction=100,
        num_candidates=100,
        element_type=ESElementType.float,
        number_of_shards=1,
        number_of_replicas=0
    )
    
    # 2. Case Instance
    manager = dataset_type.get_manager()
    # Create a performance case similar to Performance1536D5M
    class VerificationCase(PerformanceCase):
        case_id = CaseType.Custom
        dataset = manager
        name = f"Builtin Verification {dataset_type.name}"
        description = "Verification run with builtin dataset"

    case_instance = VerificationCase()
    
    # 3. Task Config
    task_config = TaskConfig(
        db=DB.ElasticCloud,
        db_config=db_config,
        db_case_config=db_case_config,
        case_config=CaseConfig(
            case_id=CaseType.Custom,
            k=10
        ),
        stages=[TaskStage.DROP_OLD, TaskStage.LOAD, TaskStage.SEARCH_SERIAL]
    )
    
    # 4. Runner
    runner = CaseRunner(
        run_id="builtin_verify_run",
        config=task_config,
        ca=case_instance,
        status=RunningStatus.PENDING,
        dataset_source=DatasetSource.S3
    )
    
    # Custom patch: We only want to verify a small subset to save time/resources
    # We will override the dataset size for the loader if possible, 
    # or just let it run if it's already downloaded.
    # For 5M, we might want to cap it.
    
    logger.info("Executing builtin verification...")
    try:
        # Note: This will attempt to load the FULL dataset if it exists.
        # To truly do a 'minimal' validation, we'd need to patch the dataset iterator.
        metric = runner.run(drop_old=True)
        logger.info(f"Validation successful! Metric: {metric}")
        return metric
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    load_dotenv()
    monkey_patch_elastic_config()
    
    # Test with OpenAI Medium 500K (since it's already downloaded)
    run_builtin_validation(DatasetWithSizeType.OpenAIMedium)
