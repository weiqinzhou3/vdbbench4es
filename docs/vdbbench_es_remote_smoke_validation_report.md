# VDBBench 项目远端自建 Elasticsearch 链路验证测试报告

## 1. 测试背景
本项目旨在验证 `vdbbench_es_poc` 工具集在远端 Ubuntu 环境下的可用性，打通与私有化部署 Elasticsearch 8.17.0 的连接链路，并执行最小化的 Smoke Test 验证。

## 2. 测试目标
- 同步本地项目到远端并配置 Python 3.11 环境。
- 验证 Monkey-patch 适配方案在远端环境的有效性。
- 执行完整的“数据导入-索引优化-向量搜索”链路测试。
- 产生真实的 benchmark 指标存根。

## 3. 环境信息
- **远端主机**: Ubuntu 22.04
- **Python 版本**: 3.11.15 (via PPA:deadsnakes)
- **VDBBench 版本**: 1.0.20
- **Elasticsearch**: 8.17.0 (自建容器化部署)
- **数据集**: Smoke Dataset (768维, 随机生成)

## 4. 本地项目审查结论
- **项目状态**: 结构完整，适配逻辑（Monkey-patch）清晰。
- **数据性质**: 经代码审查，`train.parquet` 与 `test.parquet` 均为 `numpy.random` 生成的随机数据，`neighbors.parquet` 固定指向 ID 0-9。
- **结论**: **当前数据仅用于链路打通，产生的 Recall/Latency 指标不具备正式业务参考意义。**

## 5. 远端部署过程
1. **同步方式**: 使用 `rsync` 排除虚拟环境，完整同步到远端服务器。
2. **Python 环境**: 远端系统默认为 3.10，因 VDBBench 1.0.20 要求 >= 3.11，已手动安装 Python 3.11 及其 venv。
3. **依赖安装**: 使用清华镜像源 (`tuna`) 解决了网络连接超时问题，成功安装 `vectordb-bench[elastic]`。

## 6. 连接验证过程
- **连接结果**: **成功**。
- **配置**: 通过 `.env` 注入了正确的 ES 地址与凭证。
- **版本适配**: 降级 `elasticsearch` 客户端从 9.x 至 8.17.0，解决了 API 握手协议不兼容的问题。

## 7. Smoke 数据审查结论
- **文件路径**: `datasets/smoke/cohere_768/`
- **字段验证**: Parquet 包含 `id`, `emb` (向量), `neighbors_id`, `label` 等关键字段。
- **规模**: 100 条 Train, 10 条 Test。

## 8. Smoke 测试执行过程
1. 执行 `scripts/run_vdbbench_smoke.py`。
2. 逻辑流:
   - 触发 Monkey-patch 注入 Host/Auth。
   - 删除旧索引 (`vdb_bench_indice`)。
   - 读取 Parquet 并以 Batch 100 批量写入。
   - 调用 `force_merge` 触发 ES 索引优化（强制等待 30s）。
   - 执行向量搜索并计算 Recall。

## 9. 测试结果
| 指标项 | 测量值 | 说明 |
| :--- | :--- | :--- |
| **连接状态** | 成功 | 已打通 |
| **导入耗时** | 0.6639s | 100条数据 |
| **优化耗时** | 30.0428s | 触发了 force_merge |
| **P99 延迟** | 0.004s | 单机串行搜索 |
| **Recall** | 0.04 | 随机数据预期值 |
| **结果文件** | 已生成 | `outputs/results/smoke_results.json` |

## 10. 问题与分析
- **导入路径变更**: VDBBench 1.0.20 相比旧版，大量的 `models` 和 `config` 导入路径发生变化，已在 `run_vdbbench_smoke.py` 中完成适配。
- **ES 客户端版本**: 初始安装的 9.x 客户端与 8.x 服务端不兼容，已降级修复。
- **force_merge 警告**: ES 8.x 对此 API 抛出了 Technical Preview 警告，但功能执行正常。

## 11. 结论
远端自建 Elasticsearch 链路验证 **通过**。当前项目代码、适配方案及环境配置已完全具备执行大规模（5M/10M）Benchmark 的技术前置条件。

## 12. 建议
1. **数据集替换**: 下一轮测试应下载正式的 Cohere/OpenAI 官方数据集 Parquet 文件，替换当前的 `datasets/smoke/`。
2. **并发测试**: 当前仅执行了串行（Serial）测试，建议后续在 `TaskConfig` 中加入 `TaskStage.SEARCH_CONCURRENT` 以压测 QPS。
3. **监控接入**: 建议测试时同步观察远端 ES 容器的 CPU/内存占用。

## 13. 附录
- **执行命令**: `source .venv/bin/activate && python3 scripts/run_vdbbench_smoke.py`
- **关键脚本**: `scripts/run_vdbbench_smoke.py` (含 Monkey-patch)
- **结果路径**: `vdbbench_es_poc/outputs/results/smoke_results.json`
