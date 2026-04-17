# vdbbench4es — VDBBench for Self-Hosted Elasticsearch

基于 [VDBBench](https://github.com/zilliztech/VectorDBBench) 的适配层，使其支持对**自建私有化 Elasticsearch** 进行向量检索性能测试。

## 项目简介

### 这个项目是什么

VDBBench 是 Zilliz 开源的向量数据库 Benchmark 工具，内置支持 Milvus、Qdrant、Weaviate、Elastic Cloud 等多种数据库。但它对 Elasticsearch 的支持**仅限于 Elastic Cloud**（需要 `cloud-id`），无法直接连接自建的私有化 ES 实例。

本项目通过 **运行时 Monkey-patch**（不修改 VDBBench 源码）解决了这一问题，使你可以用 VDBBench 的完整测试能力（数据加载、索引构建、向量搜索、Recall/QPS/Latency 度量）来评估自建 ES 的向量检索性能。

### 解决了什么问题

1. **连接适配**：将 VDBBench 原本只认 `cloud-id` 的 Elastic Cloud 连接方式，替换为 `host:port` + Basic Auth
2. **版本兼容**：解决 `elasticsearch-py` 客户端与 ES 服务端版本握手不匹配（如 9.x 客户端连 8.x 服务端）的 `Accept` header 报错
3. **数据集目录**：支持自定义数据集落盘路径，适配离线环境或磁盘规划
4. **索引命名**：支持自定义 ES 索引名称（可选）

### 适用场景

- 对自建 Elasticsearch 8.x 做向量检索性能评测
- 对比不同 HNSW 索引类型（float / int8 / int4 / bbq）的性能差异
- 对比不同参数（M / ef_construction / num_candidates）下的 Recall-QPS 表现
- 评估不同并发档位下的 QPS 和尾延迟

### 不适用场景

- Elasticsearch 7.x 或更早版本（未测试）
- 混合查询（向量 + 全文 + 标量过滤的复合业务检索）
- 写入性能评测（VDBBench 侧重搜索评测）
- 需要自定义 ES DSL 的高级查询场景

## 功能特性

- **支持自建 ES**：通过 `.env` 配置 host/port/user/password 即可连接任意 ES 实例
- **零修改安装**：不需要 fork 或修改 VDBBench 源码，通过 monkey-patch 在运行时注入
- **完整 Benchmark 能力**：复用 VDBBench 的数据加载、索引优化、串行搜索、并发搜索、Recall/QPS/Latency 计算
- **多索引类型**：支持 HNSW float32 / int8 / int4 / BBQ 四种量化方式对比
- **参数调优**：支持 M、ef-construction、num-candidates、k、并发数等单变量对比
- **内置数据集**：可直接下载 VDBBench 内置的 OpenAI 1536d / Cohere 768d 等标准数据集
- **Smoke 数据集**：自带小规模随机数据集，用于快速验证链路连通性
- **Load/Search 解耦**：支持先只做数据加载，再只做搜索测试

### 已验证可用的能力

| 能力 | 状态 |
|------|------|
| ES 8.x 连接与认证 | 已验证 |
| 小规模 Smoke 数据集全链路 | 已验证 |
| OpenAI 1536d 500K 写入 + 搜索 | 已验证 |
| HNSW float32 索引类型 | 已验证 |
| HNSW int8 / int4 / BBQ | 可用（通过切换子命令） |
| 参数调优对比 | 可用 |
| 高并发搜索测试 | 可用 |
| 过滤搜索 / Streaming | 条件性可用，需实测确认 |

## 项目结构

```
vdbbench4es/
├── scripts/                  # 核心脚本（用户主要关注这里）
│   ├── vdb_es_cli.py         # ★ 主入口：带 monkey-patch 的 VDBBench CLI 包装
│   ├── check_es_connection.py  # ES 连接验证
│   ├── prepare_builtin_dataset.py  # 下载 VDBBench 内置数据集
│   ├── smoke_prepare_dataset.py    # 生成小规模 smoke 数据集
│   ├── run_vdbbench_smoke.py       # Smoke 全链路测试（API 方式调用）
│   ├── run_vdbbench_smoke.sh       # Smoke 测试一键脚本
│   ├── summarize_results.py        # 汇总 smoke 测试结果
│   └── verify_builtin_ingestion.py # 内置数据集写入验证
├── datasets/smoke/           # 预生成的 smoke 小数据集（768d/1536d/2048d）
├── docs/                     # 测试报告和详细执行手册
├── .env.example              # 环境变量配置模板
├── requirements.txt          # Python 依赖
├── LICENSE                   # MIT 许可证
└── README.md
```

**用户需要关注的入口：**
- 日常使用：`scripts/vdb_es_cli.py`（命令行方式，推荐）
- 链路验证：`scripts/check_es_connection.py`
- 快速烟测：`scripts/run_vdbbench_smoke.sh`

## 安装指南

### 前提条件

- **Python**: 3.11 或更高版本（VDBBench 1.0.20 要求）
- **Elasticsearch**: 8.x（已部署并可访问）
- **操作系统**: Linux / macOS（Windows 未测试）
- **磁盘空间**: Smoke 测试 < 100MB；500K 数据集约 5GB；5M/10M 数据集约 60GB+

### 步骤 1：克隆仓库

```bash
git clone https://github.com/weiqinzhou3/vdbbench4es.git
cd vdbbench4es
```

### 步骤 2：创建虚拟环境

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

> 如果 `python3.11` 不可用，在 Ubuntu 上可通过 `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.11 python3.11-venv` 安装。

### 步骤 3：安装依赖

```bash
pip install -r requirements.txt
```

这会安装：
- `vectordb-bench[elastic]` — VDBBench 核心 + Elasticsearch 客户端支持
- `elasticsearch` — ES Python 客户端
- `polars` / `pandas` / `pyarrow` / `numpy` — 数据处理
- `python-dotenv` — 环境变量加载

> **注意**：如果你的 ES 版本是 8.x，但 pip 安装了 `elasticsearch` 9.x 客户端，可能会出现握手报错。此时请降级：
> ```bash
> pip install 'elasticsearch>=8.0,<9.0'
> ```
> 或者确保 `.env` 中设置了 `ES_COMPAT_VERSION=8`（本项目的 patch 会自动处理兼容头）。

### 步骤 4：配置 Elasticsearch 连接

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 ES 连接信息：

```bash
ES_HOSTS=http://your-es-host:9200
ES_USER=elastic
ES_PASSWORD=your_password_here
ES_VERIFY_CERTS=false
ES_COMPAT_VERSION=8
```

### 步骤 5：验证连接

```bash
python3 scripts/check_es_connection.py
```

看到 `Successfully connected to Elasticsearch!` 说明配置正确。

## 快速开始

### 最小可运行示例：Smoke 测试

这个示例会用 100 条随机向量数据验证"连接 → 写入 → 搜索"的完整链路。

```bash
# 1. 确保已完成上面的安装步骤并激活虚拟环境
source .venv/bin/activate

# 2. 运行 smoke 测试
bash scripts/run_vdbbench_smoke.sh
```

**成功后你会看到：**
- Phase 1: `Successfully connected to Elasticsearch!`
- Phase 2: `Created cohere_768 in ...`（数据生成）
- Phase 3: `Smoke test successful! Metric: ...`（向量搜索完成）
- Phase 4: 汇总表格（包含 load_duration、recall、p99 latency、qps）

**输出结果位置：** `outputs/results/smoke_results.json`

> **注意**：Smoke 数据集是随机生成的，Recall 值很低是正常的（随机数据没有语义邻近性）。它的作用是验证链路，不是评估性能。

### 使用 CLI 执行正式 Benchmark

这是推荐的日常使用方式，复用 VDBBench 的完整 CLI 能力：

```bash
# 1. 下载内置数据集（首次执行，约需数分钟到数十分钟）
python3 scripts/prepare_builtin_dataset.py OpenAIMedium  # 500K, ~4GB

# 2. 执行基础性能测试（OpenAI 1536d 500K）
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D500K \
  --cloud-id x --password x
```

> **关于 `--cloud-id x --password x`**：这两个参数是占位符，仅用于通过 VDBBench CLI 的必填参数校验。真实的 ES 连接凭证来自 `.env` 文件，不是这里的 `x`。

## Elasticsearch 使用说明

### 连接参数

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `ES_HOSTS` | ES 地址，多个用逗号分隔 | `http://10.0.0.1:9200,http://10.0.0.2:9200` |
| `ES_USER` | 认证用户名 | `elastic` |
| `ES_PASSWORD` | 认证密码 | `your_password` |
| `ES_VERIFY_CERTS` | 是否验证 TLS 证书 | `false` |
| `ES_COMPAT_VERSION` | 兼容版本号（解决握手报错） | `8` |
| `VDB_DATASET_DIR` | 数据集存储目录 | `/data/vdbbench_data` |
| `ES_INDEX_NAME` | 自定义索引名（可选） | `my_bench_index` |

### 索引类型子命令

| 子命令 | 索引类型 | 说明 |
|--------|----------|------|
| `elasticcloudhnsw` | HNSW float32 | 标准精度，基线 |
| `elasticcloudhnswint8` | HNSW int8 | 8-bit 量化 |
| `elasticcloudhnswint4` | HNSW int4 | 4-bit 量化 |
| `elasticcloudhnswbbq` | HNSW BBQ | Binary Quantization |

### 常用操作

**先 Load 后 Search（解耦执行）：**

```bash
# 只做 Load（写入数据 + 索引优化）
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-search-serial --skip-search-concurrent

# 只做 Search（复用已有索引）
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load
```

**参数调优：**

```bash
# 调整 M（每个节点的邻居数）
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load \
  --m 32

# 调整并发档位
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load \
  --num-concurrency 1,10,20,40
```

### 数据集规格

| 数据集 | case_type | 维度 | 规模 | 用途 |
|--------|-----------|------|------|------|
| OpenAI Medium | `Performance1536D500K` | 1536 | 500K | 快速验证 |
| OpenAI Large | `Performance1536D5M` | 1536 | 5M | 正式测试 |
| Cohere Large | `Performance768D10M` | 768 | 10M | 正式测试 |

### 结果关键指标

| 指标 | 含义 |
|------|------|
| `qps` | 每秒查询数（主吞吐指标） |
| `recall` | 召回率（搜索准确性） |
| `serial_latency_p99` | 串行查询 P99 延迟 |
| `load_duration` | 数据加载 + 索引优化总耗时 |
| `conc_qps_list` | 各并发档位下的 QPS |
| `conc_latency_p99_list` | 各并发档位下的 P99 延迟 |

## 常见问题 / Troubleshooting

### 1. `pip install` 时 VDBBench 安装失败

VDBBench 1.0.20 要求 Python >= 3.11。确认你的 Python 版本：

```bash
python3 --version
```

如果低于 3.11，需要安装新版本。

### 2. 连接 ES 报 `AuthenticationException` 或 401

检查 `.env` 中的 `ES_USER` 和 `ES_PASSWORD` 是否正确。可以先用 curl 验证：

```bash
curl -u elastic:your_password http://your-es-host:9200
```

### 3. 报错 `Accept found 9` 或版本握手失败

这是 `elasticsearch-py` 客户端版本与 ES 服务端版本不匹配导致的。两种解决方式：

- **方式 A**：在 `.env` 中设置 `ES_COMPAT_VERSION=8`（推荐，patch 会自动加兼容头）
- **方式 B**：降级客户端 `pip install 'elasticsearch>=8.0,<9.0'`

### 4. Monkey-patch 没生效 / 仍然要求 `cloud-id`

确保你使用的是 `scripts/vdb_es_cli.py` 作为入口，而不是直接运行 `vectordbbench` 命令。Patch 逻辑在 `vdb_es_cli.py` 的 import 阶段执行。

### 5. 数据集下载失败 / 速度极慢

VDBBench 内置数据集存放在 S3 / AliyunOSS。如果在国内网络环境下：
- `prepare_builtin_dataset.py` 默认使用 AliyunOSS 镜像，速度较快
- 如果完全离线，可在有网的机器上先 `prepare`，再将数据目录打包搬运，并在目标机器上通过 `VDB_DATASET_DIR` 指定路径

### 6. 5M/10M 数据集写入时内存不足

大规模数据集写入 ES 时内存压力大。建议：
- ES 节点至少 32GB 内存
- 磁盘空间：5M 数据集约需 50-100GB，10M 约需 100-200GB

### 7. `force_merge` 阶段特别慢

这是正常的。ES 的段合并是 I/O 密集操作。如果只想快速看写入结果，可以临时跳过：

```bash
--use-force-merge False
```

但未经优化的索引搜索性能会明显偏差，正式测试时不建议跳过。

### 8. 结果中 Recall 很低

- 如果是 Smoke 数据集：正常，因为是随机数据
- 如果是正式数据集：检查 `num-candidates` 参数（调大通常能提升 Recall）、检查数据集是否完整下载

## 当前限制

1. **仅支持 ES 8.x**：未在 7.x 或更早版本测试
2. **依赖 VDBBench 1.0.20**：不同版本的 VDBBench 内部 API 可能变化，patch 可能需要调整
3. **过滤搜索和 Streaming 未充分验证**：这两类 case 在当前 patch 链路下仅条件性可用
4. **不支持混合查询**：VDBBench 核心逻辑是纯向量搜索，不支持 keyword + vector + filter 的复合查询
5. **写入性能评测有限**：VDBBench 侧重搜索评测，写入部分只是 load 阶段
6. **单机测试**：未对多节点 ES 集群做专门优化

## 开发说明

### 本地开发

```bash
# 克隆并安装
git clone https://github.com/weiqinzhou3/vdbbench4es.git
cd vdbbench4es
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env 填入你的 ES 信息

# 验证链路
python3 scripts/check_es_connection.py
bash scripts/run_vdbbench_smoke.sh
```

### 如何验证修改没有破坏现有功能

1. 运行 `check_es_connection.py` 确认连接正常
2. 运行 `run_vdbbench_smoke.sh` 确认全链路通过
3. 如果修改了 `vdb_es_cli.py` 中的 patch 逻辑，用 `--help` 确认 CLI 正常加载

### Monkey-patch 工作原理

`scripts/vdb_es_cli.py` 在 import VDBBench CLI 之前，依次执行以下 patch：

| Patch | 目标 | 作用 |
|-------|------|------|
| Patch A | `Elasticsearch.__init__` | 注入 `Accept` 兼容头，解决版本握手 |
| Patch B | `ElasticCloudConfig.to_dict` | 替换 cloud-id 连接为 host + basic_auth |
| Patch C | `config.DATASET_LOCAL_DIR` | 允许自定义数据集存储目录 |
| Patch D | `ElasticCloud.__init__` | 允许自定义 ES 索引名称 |

所有 patch 都是**运行时覆盖**，不修改 VDBBench 安装包的任何文件。

## 致谢

- [VDBBench (VectorDBBench)](https://github.com/zilliztech/VectorDBBench) — Zilliz 开源的向量数据库 Benchmark 工具
- [elasticsearch-py](https://github.com/elastic/elasticsearch-py) — Elasticsearch 官方 Python 客户端

## License

[MIT](LICENSE)
