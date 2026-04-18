import os
import sys
import logging
import json
from pathlib import Path
from pydantic import SecretStr
from dotenv import load_dotenv

# Ensure project root is discoverable
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vectordb_bench.backend.clients.elastic_cloud.config import ElasticCloudConfig
from vectordb_bench.backend.clients.elastic_cloud.config import ElasticCloudIndexConfig, ESElementType
from vectordb_bench.backend.clients import DB
from vectordb_bench.backend.cases import CaseType, PerformanceCustomDataset
from vectordb_bench.models import TaskConfig, CaseConfig, TaskStage
from vectordb_bench.backend.task_runner import CaseRunner, RunningStatus
from vectordb_bench.backend.data_source import DatasetSource
from vectordb_bench.backend.clients.api import IndexType
from scripts.es_connection_options import build_elasticsearch_options

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vdbbench_smoke")

def monkey_patch_elastic_config():
    from pydantic import SecretStr
    from vectordb_bench.backend.clients.elastic_cloud.config import ElasticCloudConfig
    
    def to_dict(self) -> dict:
        load_dotenv()
        return build_elasticsearch_options()
    
    ElasticCloudConfig.to_dict = to_dict
    
    # Also patch __init__ to avoid cloud_id validation if possible, 
    # but pydantic might still complain if cloud_id is missing and it is required.
    # In 1.0.20, we can just pass a dummy cloud_id.
    
    logger.info("Monkey-patched ElasticCloudConfig.to_dict for self-hosted ES")

def run_smoke_test(dim, name):
    logger.info(f"Starting smoke test for {name} (dim={dim})")
    
    db_config = ElasticCloudConfig(
        db_label=f"smoke_{name}",
        cloud_id=SecretStr("fake"), # Required by pydantic but ignored by our patch
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
    
    dataset_dir = PROJECT_ROOT / "datasets" / "smoke" / name
    
    custom_case_params = {
        "name": f"Smoke Test {name}",
        "description": "A minimal smoke test",
        "load_timeout": 600,
        "optimize_timeout": 600,
        "dataset_config": {
            "name": name,
            "dir": str(dataset_dir.absolute()),
            "size": 100,
            "dim": dim,
            "metric_type": "cosine",
            "file_count": 1,
            "use_shuffled": False,
            "with_gt": True,
            "train_name": "train",
            "test_name": "test",
            "gt_name": "neighbors",
            "train_id_name": "id",
            "train_col_name": "emb",
            "test_col_name": "emb",
            "gt_col_name": "neighbors_id",
            "scalar_labels_name": "scalar_labels"
        }
    }
    
    task_config = TaskConfig(
        db=DB.ElasticCloud,
        db_config=db_config,
        db_case_config=db_case_config,
        case_config=CaseConfig(
            case_id=CaseType.PerformanceCustomDataset,
            custom_case=custom_case_params,
            k=10
        ),
        stages=[TaskStage.DROP_OLD, TaskStage.LOAD, TaskStage.SEARCH_SERIAL]
    )
    
    case_instance = PerformanceCustomDataset(**custom_case_params)
    
    runner = CaseRunner(
        run_id="smoke_run",
        config=task_config,
        ca=case_instance,
        status=RunningStatus.PENDING,
        dataset_source=DatasetSource.S3 # Ignored for custom dataset
    )
    
    logger.info("Runner initialized. Executing...")
    try:
        metric = runner.run(drop_old=True)
        logger.info(f"Smoke test successful! Metric: {metric}")
        return metric
    except Exception as e:
        logger.error(f"Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    monkey_patch_elastic_config()
    
    results = {}
    # Run only one for smoke test efficiency, or all if requested
    results["cohere_768"] = run_smoke_test(768, "cohere_768")
    
    # Save results
    output_path = PROJECT_ROOT / "outputs" / "results" / "smoke_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        # Hand-serialize Metric object since it might not have .dict()
        def serialize_metric(m):
            if m is None: return None
            # Standard Python attribute access
            return {
                "load_duration": float(getattr(m, 'load_duration', 0)),
                "recall": float(getattr(m, 'recall', 0)),
                "serial_latency_p99": float(getattr(m, 'serial_latency_p99', 0)),
                "qps": float(getattr(m, 'qps', 0))
            }
        
        json.dump({k: serialize_metric(v) for k, v in results.items()}, f, indent=2)
    
    print(f"\nSmoke test results saved to {output_path}")
