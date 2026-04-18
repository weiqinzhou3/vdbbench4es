from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path

# Ensure project root is discoverable
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.builtin_dataset_dependencies import (
    BuiltinDatasetDependencyError,
    ensure_builtin_dataset_dependencies,
)
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

# --- 补丁：拦截全局配置，自定义数据集落盘目录 ---
try:
    from vectordb_bench import config
    custom_ds_dir = os.getenv("VDB_DATASET_DIR")
    if custom_ds_dir:
        config.DATASET_LOCAL_DIR = custom_ds_dir
        # print(f"DEBUG: Dataset directory redirected to {custom_ds_dir}")
except ImportError:
    pass
# --- 补丁结束 ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prepare_dataset")

def prepare_and_inspect(dataset_type: DatasetWithSizeType):
    logger.info(f"Starting prepare for: {dataset_type.value}")
    manager = dataset_type.get_manager()
    
    start_time = time.time()
    try:
        # Use AliyunOSS for faster download in CN
        manager.prepare(DatasetSource.AliyunOSS)
        duration = time.time() - start_time
        logger.info(f"Prepare completed in {duration:.2f} seconds")
        
        # Inspection
        # In 1.0.20, directories are often structured as /tmp/vectordb_bench/dataset/<name>/<config>
        # Let's try to infer it from the manager or use standard VDBBench path
        dataset_path = Path("/tmp/vectordb_bench/dataset")
        logger.info(f"Looking for dataset files in: {dataset_path}")
        
        # List all parquet files recursively to find where they landed
        all_parquet = list(dataset_path.glob("**/*.parquet"))
        logger.info(f"Found {len(all_parquet)} parquet files total.")
        
        for f in all_parquet:
            size_mb = f.stat().st_size / (1024 * 1024)
            logger.info(f"  - {f} ({size_mb:.2f} MB)")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to prepare dataset {dataset_type.name}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    load_dotenv()
    try:
        ensure_builtin_dataset_dependencies()
        from vectordb_bench.backend.dataset import DatasetWithSizeType
        from vectordb_bench.backend.data_source import DatasetSource
    except BuiltinDatasetDependencyError as e:
        logger.error(str(e))
        sys.exit(2)
    except ImportError as e:
        logger.error(
            "Failed to import VDBBench builtin dataset modules: %s. "
            "Install dependencies with: python3 -m pip install -r requirements.txt",
            e,
        )
        sys.exit(2)
    
    # 优先从命令行获取，如果没有则从环境变量获取，最后给一个默认值
    if len(sys.argv) > 1:
        ds_names = sys.argv[1:]
    else:
        env_ds = os.getenv("PREPARE_DATASETS", "OpenAIMedium")
        ds_names = [ds.strip() for ds in env_ds.split(",")]
        
    for ds_name in ds_names:
        try:
            logger.info(f"Processing dataset: {ds_name}")
            ds_type = DatasetWithSizeType[ds_name]
            prepare_and_inspect(ds_type)
        except KeyError:
            logger.error(f"Dataset {ds_name} not found in DatasetWithSizeType. Skip.")
            continue
