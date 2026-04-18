import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not found, environment variables might not be loaded.")

from scripts.es_connection_options import build_elasticsearch_options

# --- 核心适配补丁开始 ---

# 补丁 A: 解决 ES 客户端与服务端的版本握手报错
try:
    from elasticsearch import Elasticsearch
    original_init = Elasticsearch.__init__
    def new_init(self, *args, **kwargs):
        compat_version = os.getenv("ES_COMPAT_VERSION")
        if compat_version:
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']["Accept"] = f"application/vnd.elasticsearch+json; compatible-with={compat_version}"
        original_init(self, *args, **kwargs)
    Elasticsearch.__init__ = new_init
except ImportError:
    pass

# 补丁 B: 拦截配置类，让原本只支持 Elastic Cloud 的工具连接到私有 ES
try:
    from vectordb_bench.backend.clients.elastic_cloud.config import ElasticCloudConfig
    def patched_to_dict(self) -> dict:
        # 确保补丁内部也能拿到最新的环境变量
        return build_elasticsearch_options()
    ElasticCloudConfig.to_dict = patched_to_dict
except ImportError:
    pass

# 补丁 C: 拦截全局配置，自定义数据集落盘目录
try:
    from vectordb_bench import config
    custom_ds_dir = os.getenv("VDB_DATASET_DIR")
    if custom_ds_dir:
        config.DATASET_LOCAL_DIR = custom_ds_dir
except ImportError:
    pass

# 补丁 D: 允许自定义 ES 索引名称
# 必须在 original __init__ 调用之前注入 indice 参数，
# 否则 drop_old 逻辑仍会操作默认索引名 "vdb_bench_indice"。
try:
    from vectordb_bench.backend.clients.elastic_cloud.elastic_cloud import ElasticCloud
    custom_index_name = os.getenv("ES_INDEX_NAME")
    if custom_index_name:
        original_ec_init = ElasticCloud.__init__
        def new_ec_init(self, *args, **kwargs):
            kwargs.setdefault("indice", custom_index_name)
            original_ec_init(self, *args, **kwargs)
        ElasticCloud.__init__ = new_ec_init
except ImportError:
    pass

# --- 核心适配补丁结束 ---

if __name__ == "__main__":
    try:
        from vectordb_bench.cli.vectordbbench import cli
        cli()
    except ImportError as e:
        print(f"Error: Could not import VDBBench. Ensure dependencies are installed. {e}")
        sys.exit(1)
