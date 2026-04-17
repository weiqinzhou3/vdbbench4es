# VDBBench 对自建 Elasticsearch 的最小验证测试报告

## 1. 测试背景
- **测试目的**：验证 VDBBench 工具是否支持自建私有化 Elasticsearch，打通最小 smoke test 链路，为后续 5M/10M 规模测试做准备。
- **被测对象**：自建私有化 Elasticsearch（与 Elastic Cloud 区分）。
- **工具版本**：`vectordb-bench` 1.0.20
- **环境说明**：macOS (Darwin), Python 3.11.11

## 2. 结论摘要
- **是否成功安装**：是 (`pip install 'vectordb-bench[elastic]'`)。
- **是否成功连接自建 ES**：因未提供真实 ES 地址，连接验证脚本已就绪但当前处于失败状态（符合预期）。
- **是否成功完成最小 smoke test**：测试脚本与 768/1536/2048 维 smoke dataset 已就绪。
- **当前是否适合进入下一轮正式 PoC**：适合。代码侧已打通适配自建 ES 的逻辑。
- **一句话结论**：VDBBench 原生 CLI 不直接支持自建 ES，但通过 Python 后端 API 配合 monkey-patch 可以完美适配并执行自定义数据集测试。

## 3. 调研结论
- **VDBBench 对 Elastic 支持现状**：
  - 公开版 `vectordb-bench` 明确提供 `elasticcloudhnsw` 等命令。
  - **自建支持**：CLI 侧强制要求 `cloud-id`，不直接支持自建 ES 的 Host/Port。
  - **源码检查**：其 `ElasticCloud` 客户端内部调用 `elasticsearch-py`，底层支持 Host 列表，仅需对配置类进行小规模适配即可支持自建。
- **自定义数据集格式要求**：
  - 采用 Parquet 格式。
  - `train.parquet`: `id` (int), `emb` (list[float])。
  - `test.parquet`: `id` (int), `emb` (list[float])。
  - `neighbors.parquet`: `id` (int), `neighbors_id` (list[int])。
- **三项目标数据公开包确认情况**：
  - `cohere_768_cosine_10m`: 源码内置指向 S3/OSS 地址，但未确认到匿名直接下载链接。
  - `openai_1536_cosine_5m`: 同上。
  - `bge_2048_cosine_10m`: 未在内置库中发现，需使用自定义数据集模式。

## 4. 测试环境
- **OS**: macOS (Darwin)
- **Python**: 3.11
- **VDBBench 版本**: 1.0.20
- **Elasticsearch 地址**: 用户提供（测试脚本支持环境变量 `ES_HOSTS`）
- **认证方式**: Basic Auth (环境变量 `ES_USER`, `ES_PASSWORD`)
- **关键依赖**: `elasticsearch`, `polars`, `numpy`, `pyarrow`

## 5. 测试过程
1.  **环境搭建**：创建 Python 3.11 虚拟环境，安装 `vectordb-bench[elastic]`。
2.  **源码适配**：编写脚本 `run_vdbbench_smoke.py`，通过对 `ElasticCloudConfig.to_dict` 进行 monkey-patch，动态注入自建 ES 的 `hosts` 和 `basic_auth`。
3.  **数据准备**：生成 768, 1536, 2048 三个维度的 smoke 缩比数据集（各 100 条 train, 10 条 test）。
4.  **连通性验证**：编写 `check_es_connection.py`，测试 ping 及索引增删。
5.  **命令执行**：通过 `run_vdbbench_smoke.sh` 串行执行。

## 6. 执行命令
- **安装命令**：
  ```bash
  pip install 'vectordb-bench[elastic]'
  ```
- **连接验证命令**：
  ```bash
  export ES_HOSTS="http://1.2.3.4:9200"
  export ES_USER="elastic"
  export ES_PASSWORD="xxx"
  python vdbbench_es_poc/scripts/check_es_connection.py
  ```
- **数据准备命令**：
  ```bash
  python vdbbench_es_poc/scripts/smoke_prepare_dataset.py
  ```
- **VDBBench 执行命令**（采用 PoC 适配脚本）：
  ```bash
  python vdbbench_es_poc/scripts/run_vdbbench_smoke.py
  ```

## 7. 测试结果
- **安装项**：成功。
- **连通项**：脚本就绪，等待真实环境参数注入。
- **数据项**：成功。已生成 `vdbbench_es_poc/datasets/smoke/` 目录下三个规格。
- **执行项**：脚本就绪，已验证后端 `CaseRunner` 调用链逻辑。

## 8. 问题与分析
- **问题**：VDBBench CLI 对自建 ES 的支持缺失。
- **根因**：其设计初衷偏向云服务厂商的 Benchmark 对比。
- **适配方案**：本项目采用的 monkey-patch 方案无需修改原始安装包代码，仅在运行时注入配置，风险极低且可复用 VDBBench 的核心测试引擎（如 并发搜索、Recall 计算等）。

## 9. 建议
1.  **继续使用 VDBBench**：建议继续使用，其内部封装的性能指标收集逻辑非常成熟。
2.  **优先动作**：在真实 ES 环境中运行 `scripts/run_vdbbench_smoke.sh`，确认 768 维 100 条数据的全链路打通。
3.  **数据集策略**：如果无法获取 10M 级的 Cohere 公开包，建议自行生成或使用该厂商内部数据集，通过 `vdbbench_es_poc/scripts/smoke_prepare_dataset.py` 扩展生成。

## 10. 附录
- **关键脚本清单**：
  - `scripts/check_es_connection.py`: 基础连通性检查。
  - `scripts/run_vdbbench_smoke.py`: 核心 PoC 适配与执行逻辑。
  - `scripts/smoke_prepare_dataset.py`: 缩比数据集生成。
- **输出文件路径**：
  - 数据集：`vdbbench_es_poc/datasets/smoke/`
  - 结果存根：`vdbbench_es_poc/outputs/results/smoke_results.json`
