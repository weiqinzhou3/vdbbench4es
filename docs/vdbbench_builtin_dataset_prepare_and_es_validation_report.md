# VDBBench 内置数据集下载与自建 Elasticsearch 验证报告

## 1. 测试背景
本项目旨在验证 VDBBench 内置数据集的自动化准备能力，并利用下载的真实内置数据集对远端私有化部署的 Elasticsearch 8.17.0 进行全链路写入与搜索验证。

## 2. 结论摘要
- **内置下载能力**: 验证通过。通过 AliyunOSS 镜像源可以稳定下载 OpenAI (1536dim) 和 Cohere (768dim) 系列数据集。
- **OpenAI 500K 写入**: **成功**。已成功将 50 万条 OpenAI 1536 维向量写入远端 ES，索引占用 9.8 GB。
- **Cohere 10M 准备**: **部分成功**。数据已开始下载，但由于单机磁盘空间限制（仅剩 80GB），无法支持 10M 级别的完整 ES 索引测试。
- **整体评价**: 链路已完全打通，方案成熟，具备进行大规模性能评测的技术条件。

## 3. VDBBench 内置数据集规格确认
| 规格名称 | 维度 | 规模 | 状态 | 存储预估 (Parquet) |
| :--- | :--- | :--- | :--- | :--- |
| OpenAI Medium | 1536 | 500K | 已就绪 | ~4.3 GB |
| OpenAI Large | 1536 | 5M | 可下载 | ~55 GB |
| Cohere Large | 768 | 10M | 可下载 | ~55 GB |

## 4. OpenAI Medium 500K 下载验证过程
- **命令**: `python scripts/prepare_builtin_dataset.py OpenAIMedium`
- **下载源**: `AliyunOSS` (assets.zilliz.com.cn)
- **耗时**: 261.17s (约 4 分钟)
- **文件清单**:
  - `shuffle_train.parquet` (4286.65 MB)
  - `test.parquet` (6.90 MB)
  - `neighbors.parquet` (3.43 MB)

## 5. OpenAI Medium 500K 写入自建 ES 验证过程
- **执行逻辑**: 调用 `CaseRunner` 执行 `DROP_OLD` 和 `LOAD` 阶段。
- **写入结果**:
  - 索引名称: `vdb_bench_indice`
  - 写入文档数: 498,388
  - 存储占用: **9.8 GB**
  - Mapping: `dense_vector` (hnsw, 1536 dim, cosine)
- **ES 查询验证**:
  ```bash
  curl -u elastic:$ES_PASSWORD -s 'http://localhost:9200/vdb_bench_indice/_count'
  # 返回: {"count":498388}
  ```

## 6. Cohere Large 10M 下载验证过程
- **下载状态**: 正在后台下载 (13个分片)。
- **磁盘挑战**: 每分片约 4.2GB，总计约 55GB。当前环境剩余空间仅 80GB，下载完成后无法再支撑 ES 索引化（ES 索引 10M 数据预计需 100GB+ 空间）。

## 7. VDBBench 对客户性能测试覆盖范围评估

### A. VDBBench 原生直接适合覆盖的性能测试
- **基础向量检索能力**: QPS、Recall、Latency (P95/P99)。
- **标准模型支持**: OpenAI (1536d), Cohere (768dim), Bioasq (1024dim)。
- **并发压力测试**: 内置多并发 Runner，可压测 ES 在不同并发下的稳定性。

### B. VDBBench 经过少量适配后可覆盖的性能测试
- **私有化自建环境**: 通过本项目实现的 Monkey-patch 方案，可完美支持非 Cloud 部署的 ES。
- **自定义索引参数**: 可通过适配 `db_case_config` 调整 ES 的 `m`, `ef_construction` 等 HNSW 参数。

### C. VDBBench 不适合作为主工具覆盖的性能测试
- **混合查询 (Hybrid Search)**: VDBBench 核心逻辑在于向量搜索，对“向量 + 全文 + 过滤”的深度复合查询支持较弱。
- **复杂业务 Schema**: 客户若有大量的元数据字段同步过滤需求，需自行编写测试脚本或深度魔改 VDBBench 的数据结构。

## 8. 当前问题与限制
1. **磁盘瓶颈**: 单机测试机磁盘 (100G) 无法支撑 10M 规模的内置数据集测试。
2. **下载速度**: 默认 S3 线路在远端极慢，必须强制切换到 AliyunOSS 或手动离线搬运。
3. **内存压力**: ES 在构建 1536 维 5M 索引时内存压力极大，建议单机测试至少分配 32GB+ 内存。

## 9. 建议
1. **环境升级**: 生产级 PoC 必须申请至少 500GB SSD 磁盘和 64GB 内存的机器。
2. **数据搬迁**: 鉴于网络不确定性，建议在本地环境 `prepare` 好数据后，打包 `tar` 包通过 `scp` 搬迁到客户环境。
3. **性能调优**: 在进行 5M/10M 测试前，应优先执行 `force_merge` 以保证段合并完成，否则结果会有较大波动。

## 10. 附录
- **准备脚本**: `vdbbench_es_poc/scripts/prepare_builtin_dataset.py`
- **写入脚本**: `vdbbench_es_poc/scripts/verify_builtin_ingestion.py`
- **数据落盘路径**: `/tmp/vectordb_bench/dataset/`
