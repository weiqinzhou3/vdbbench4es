# VDBBench 自建 Elasticsearch 测试执行手册

版本：V2.1（按两套内置数据集重组，支持 Load / Search 解耦）

文档属性：执行版 / 使用说明版 / 客户现场复用版

---

## 1. 编制说明

### 1.1 文档目的
本手册用于指导测试人员基于 `vdbbench_es_poc` 项目，对**自建私有化 Elasticsearch** 执行向量检索测试。文档重点不是解释 VDBBench 原理，而是帮助执行人员按步骤完成：

1. 环境检查
2. 数据集准备
3. 只做 Load
4. 只做 Search
5. 基础性能测试
6. 索引类型对比测试
7. 参数单变量对比测试
8. 高并发查询测试
9. 条件性测试（过滤 / Streaming）

### 1.2 当前适用范围
本轮文档**只围绕两套内置数据集**组织，不再沿用旧版 Rally 文档中的 512/1024/2048、1000w/5000w 口径：

- **OpenAI 1536维 5M**
- **Cohere 768维 10M**

### 1.3 当前工具链说明
当前项目采用 `scripts/vdb_es_cli.py` 作为执行入口。它的本质是：

- 保留官方 `vectordbbench` CLI 的子命令、参数结构与执行逻辑
- 通过 monkey-patch 将原本偏向 Elastic Cloud 的连接方式替换为**自建 ES 的 host/port/basic auth**
- 因此命令行中仍会看到 `--cloud-id` 和 `--password` 为必填，但它们在本项目中只是**占位参数**
- 真实连接信息来自 `.env`

### 1.4 占位参数说明
命令中统一保留：

```bash
--cloud-id x --password x
```

这两个值只用于通过 CLI 参数校验，不代表真实连接凭证。

---

## 2. 环境说明

- **服务器**：Ubuntu 22.04（或兼容 Linux 发行版）
- **软件栈**：Python 3.11+ / Elasticsearch 8.x / 可选 Kibana
- **核心工具**：`scripts/vdb_es_cli.py`
- **配置文件**：项目根目录 `.env`
- **关键环境变量**：
  - `ES_HOSTS`
  - `ES_USER`
  - `ES_PASSWORD`
  - `ES_VERIFY_CERTS`
  - `ES_COMPAT_VERSION`
  - `VDB_DATASET_DIR`（可选，自定义数据集目录）

### 2.1 启动前最低检查
执行任何测试前，至少确认：

1. `.env` 已存在
2. `python3` 可用
3. 虚拟环境已激活（如项目要求）
4. Elasticsearch 可访问
5. 数据集目录存在

---

## 3. 本轮测试范围与不纳入范围

### 3.1 本轮纳入范围（VDBBench 主线能力）

#### A. 原生适合做的
1. **OpenAI 1536维 5M 基础搜索性能**
2. **Cohere 768维 10M 基础搜索性能**
3. **不同索引类型对比**
   - `elasticcloudhnsw`
   - `elasticcloudhnswint8`
   - `elasticcloudhnswint4`
   - `elasticcloudhnswbbq`
4. **参数单变量对比**
   - `M`
   - `ef-construction`
   - `num-candidates`
   - `k`
   - `num-concurrency`
5. **高并发查询测试**

#### B. 条件性纳入（须先验证当前 patch 链路）
6. **过滤搜索测试**
7. **边写边搜 / Streaming 测试**

### 3.2 本轮不纳入范围（不以 VDBBench 为主工具）
1. 单线程 / 多线程纯写入对比
2. update/delete 干扰查询
3. 512/1024/2048 三档同源维度对比
4. 1000w/5000w 1024维资源占用专项
5. 关键字 + 向量 + 标量过滤的 ES 业务化混合检索

### 3.3 当前已确认可执行的 Case（按两套数据集重组）

| 分类 | 核心 Case / 命令路线 | 当前状态 | 说明 |
|---|---|---|---|
| 基础性能 | `Performance1536D5M`、`Performance768D10M` | 已确认 | 两套正式数据集主线 case |
| 索引对比 | `elasticcloudhnsw`、`elasticcloudhnswint8`、`elasticcloudhnswint4`、`elasticcloudhnswbbq` | 已确认 | 通过切换子命令实现 |
| 元数据过滤 | `Performance1536D5M1P`、`Performance1536D5M99P`（或对应 Cohere case） | 条件确认 | 需先验证当前 patch 下是否可直接执行 |
| 边写边搜 | `StreamingPerformanceCase` | 条件确认 | 需实测 patch 链路 |
| 参数对比 | `M`、`ef-construction`、`num-candidates`、`k`、`num-concurrency` | 已确认 | 通过 CLI 传参实现 |

---

## 4. 两套数据集与 case_type 映射表

| 目标规格 | 内置数据集名 | case_type 参数名 | 维度 | 规模 | 用途 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenAI Large** | `OpenAILarge` | `Performance1536D5M` | 1536 | 5,000,000 | 正式主线 |
| **Cohere Large** | `CohereLarge` | `Performance768D10M` | 768 | 10,000,000 | 正式主线 |
| **OpenAI Medium** | `OpenAIMedium` | `Performance1536D500K` | 1536 | 500,000 | 中档 rehearsal / 验证用 |

### 4.1 为什么只需要一个 `case_type`
`case_type` 在 VDBBench 中不是一个普通开关，而是一套**预定义测试剧本**。它已经决定了：

- 使用哪套数据规格
- 默认执行哪些 stages
- 默认的 `k`
- 默认的串行搜索 / 并发搜索逻辑
- 结果输出结构

因此，下面这条命令：

```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D500K \
  --cloud-id x --password x
```

意思并不是“只有一个参数”，而是：

> 用 HNSW 路线，执行一套已经定义好的 **1536维 / 50万规模 / 端到端加载 + 查询** 的性能剧本。

---

## 5. 通用命令清单

### 5.1 环境连通性自检
```bash
python3 scripts/check_es_connection.py
```

**作用**：验证 `.env` 中配置的 ES 地址、用户名、密码是否有效，并检查是否可进行基本索引操作。  
**结果查看位置**：终端直接输出。  
**失败排查位置**：优先检查 `.env`、ES 服务状态和网络连通性。

### 5.2 数据集准备（只需执行一次）
```bash
# 下载 OpenAI 5M 数据
python3 scripts/prepare_builtin_dataset.py OpenAILarge

# 下载 Cohere 10M 数据
python3 scripts/prepare_builtin_dataset.py CohereLarge
```

**作用**：将 VDBBench 内置大数据集准备到本地目录。  
**结果查看位置**：终端输出 + 数据目录。  
**默认落盘目录**：`/tmp/vectordb_bench/dataset/`。  
**可选目录控制**：通过 `.env` 中的 `VDB_DATASET_DIR` 指定。

### 5.3 查看命令帮助
```bash
python3 scripts/vdb_es_cli.py --help
python3 scripts/vdb_es_cli.py elasticcloudhnsw --help
python3 scripts/vdb_es_cli.py elasticcloudhnswint8 --help
python3 scripts/vdb_es_cli.py elasticcloudhnswint4 --help
python3 scripts/vdb_es_cli.py elasticcloudhnswbbq --help
```

**作用**：查看当前 patch 后 CLI 实际可用参数。  
**结果查看位置**：终端输出。  
**失败排查位置**：虚拟环境、`scripts/vdb_es_cli.py`、依赖安装情况。

### 5.4 通用执行模板
```bash
python3 scripts/vdb_es_cli.py [子命令/索引类型] \
  --case-type [Case名] \
  --cloud-id x --password x \
  [其他参数]
```

**作用**：所有正式命令都基于这一模板展开。  
**特别说明**：`--cloud-id` 与 `--password` 只做占位，真实连接由 `.env` 提供。

### 5.5 查看测试结果目录
```bash
find . -type f | grep -E 'result_.*\.json|report|outputs|logs'
```

**作用**：快速定位运行后生成的结果文件。  
**结果查看位置**：终端输出文件路径。  
**失败排查位置**：项目根目录、`outputs/`、`logs/`、虚拟环境日志目录。

### 5.6 查看 ES 中测试索引
```bash
curl -s -u "$ES_USER:$ES_PASSWORD" "$ES_HOSTS/_cat/indices?v"
```

**作用**：查看当前集群中已创建的测试索引。  
**结果查看位置**：终端表格输出。  
**失败排查位置**：`.env`、ES 认证、网络。

### 5.7 查看 ES 中文档数
```bash
curl -s -u "$ES_USER:$ES_PASSWORD" "$ES_HOSTS/<index_name>/_count?pretty"
```

**作用**：验证 load 阶段是否真的写入成功。  
**结果查看位置**：终端 JSON 输出。  
**失败排查位置**：索引名是否正确、写入阶段是否执行成功。

### 5.8 清理测试索引
```bash
curl -s -u "$ES_USER:$ES_PASSWORD" -X DELETE "$ES_HOSTS/<index_name>?pretty"
```

**作用**：删除当前测试索引，便于切换下一种索引类型继续测试。  
**结果查看位置**：终端 JSON 输出。  
**注意**：生产环境禁止误删。

---

## 6. 参数作用解释（必须看懂再调）

| 参数 | 人话解释 | 调大后的典型影响 | 调小时的典型影响 |
|---|---|---|---|
| `--m` | HNSW 图中每个节点保留的邻居数 | Recall 可能更高，建索引更慢、占用更大 | 建索引更轻，但 Recall 可能下降 |
| `--ef-construction` | 建索引时搜索候选范围 | 索引质量更好，建索引更慢 | 建索引更快，但图质量可能变差 |
| `--num-candidates` | 查询时候选集大小 | Recall 通常更高，但查询更慢 | 查询更快，但 Recall 可能下降 |
| `--k` | 返回的 top-k 数量 | 返回结果更多，后处理可能更重 | 返回更少，结果更轻 |
| `--num-concurrency` | 并发查询线程/连接数列表 | 可观察高并发下 QPS 与延迟拐点 | 更适合看低并发基线 |
| `--use-force-merge` | load 后是否强制段合并优化 | 更接近稳定查询状态，但 load 时间更长 | 更快结束 load，但索引未优化 |

### 6.1 参数调优原则
1. **固定数据集和 case_type**
2. **每次只改一个参数**
3. **其余参数全部保持一致**
4. **每次都记录 run_id、命令、结果路径**

---

## 7. 分步骤执行总流程（推荐照此顺序）

### 阶段 1：环境检查
1. 激活虚拟环境
2. 执行 `check_es_connection.py`
3. 查看 `elasticcloudhnsw --help`

### 阶段 2：数据集准备
1. `prepare_builtin_dataset.py OpenAILarge`
2. `prepare_builtin_dataset.py CohereLarge`
3. 确认数据目录和文件存在

### 阶段 3：先只做 Load（解耦）
1. 先把目标数据集写入 ES
2. 不做任何搜索测试
3. 只验证索引存在、文档数正确

### 阶段 4：再只做 Search
1. 跳过 drop-old
2. 跳过 load
3. 直接复用已有索引跑串行/并发查询

### 阶段 5：基础性能测试
1. 先跑 OpenAI 5M
2. 再跑 Cohere 10M

### 阶段 6：索引类型对比
1. HNSW
2. INT8
3. INT4
4. BBQ

### 阶段 7：参数单变量对比
1. M
2. ef-construction
3. num-candidates
4. k
5. num-concurrency

### 阶段 8：高并发测试
在已有索引上只做并发查询。

### 阶段 9：条件性测试
1. 过滤搜索
2. Streaming / 边写边搜

---

## 8. 只做 Load（不做任何性能测试）

这是本轮新增的重要执行模式：

> **可以先只做 load，不做任何性能测试。**

### 8.1 OpenAI 1536 5M：只做 Load
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-search-serial \
  --skip-search-concurrent
```

### 8.2 Cohere 768 10M：只做 Load
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance768D10M \
  --cloud-id x --password x \
  --skip-search-serial \
  --skip-search-concurrent
```

### 8.3 可选：连优化阶段也不做
如果你只想纯攒数据，不想执行最后的索引优化，可再加：

```bash
--use-force-merge False
```

**不建议作为默认方式。**
因为未优化的向量索引查询性能通常会明显偏差。

### 8.4 Load 完成后必须做的验证
1. 查看索引是否存在
2. 查看 `_count`
3. 记录结果文件路径
4. 记录 run_id

---

## 9. 只做 Search（复用已写入索引）

当你已经完成 load，希望后续只做查询压测时，可以使用下面的方式：

### 9.1 OpenAI 1536 5M：只做 Search
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old \
  --skip-load
```

### 9.2 Cohere 768 10M：只做 Search
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance768D10M \
  --cloud-id x --password x \
  --skip-drop-old \
  --skip-load
```

### 9.3 这两个参数的作用
- `--skip-drop-old`：跳过删除旧索引/旧数据
- `--skip-load`：跳过数据写入阶段

这组命令是你后续做：
- 参数调优
- 高并发测试
- 同一索引多轮复测

时最重要的复用方式。

---

## 10. 基础性能测试步骤

### 10.1 OpenAI 1536 5M 基础性能
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x
```

### 10.2 Cohere 768 10M 基础性能
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance768D10M \
  --cloud-id x --password x
```

**作用**：完整执行默认性能剧本（drop_old + load + serial search + concurrent search）。  
**结果查看**：结果 JSON、终端输出、日志目录。  
**建议**：第一次先用 OpenAI 5M 验证链路，再做 Cohere 10M。

---

## 11. 不同索引类型对比测试步骤

### 11.1 通用原则
同一组数据、同一个 case_type 下，**只切换子命令**，不要同时改其他参数。

### 11.2 OpenAI 1536 5M 示例
```bash
# 1. Float32 / HNSW
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x

# 2. Int8
python3 scripts/vdb_es_cli.py elasticcloudhnswint8 \
  --case-type Performance1536D5M \
  --cloud-id x --password x

# 3. Int4
python3 scripts/vdb_es_cli.py elasticcloudhnswint4 \
  --case-type Performance1536D5M \
  --cloud-id x --password x

# 4. BBQ
python3 scripts/vdb_es_cli.py elasticcloudhnswbbq \
  --case-type Performance1536D5M \
  --cloud-id x --password x
```

### 11.3 Cohere 768 10M 示例
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw --case-type Performance768D10M --cloud-id x --password x
python3 scripts/vdb_es_cli.py elasticcloudhnswint8 --case-type Performance768D10M --cloud-id x --password x
python3 scripts/vdb_es_cli.py elasticcloudhnswint4 --case-type Performance768D10M --cloud-id x --password x
python3 scripts/vdb_es_cli.py elasticcloudhnswbbq --case-type Performance768D10M --cloud-id x --password x
```

### 11.4 推荐执行方式
为了节省时间与资源，建议：

1. 先用 `elasticcloudhnsw` 建基线索引并完成一轮 load/search
2. 记录结果
3. 删除该索引
4. 再执行 `int8` / `int4` / `bbq`

也就是说：

> **不同索引类型需要重新构建索引；但同一索引类型下做参数对比时，可以先 load 再 skip-load 复用。**

---

## 12. 参数调优对比测试步骤（单变量法）

### 12.1 调整 M
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load \
  --m 32
```

### 12.2 调整 ef-construction
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load \
  --ef-construction 200
```

### 12.3 调整 num-candidates
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load \
  --num-candidates 200
```

### 12.4 调整 k
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load \
  --k 50
```

### 12.5 调整并发档位
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old --skip-load \
  --num-concurrency 1,10,20,40 \
  --concurrency-duration 60
```

### 12.6 对比原则
- 每次只改一个参数
- 参数变化前后都记录 run_id
- 保留结果 JSON 路径
- 记录 QPS / Recall / P99 / P95

---

## 13. 高并发查询测试步骤

### 13.1 OpenAI 1536 5M
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M \
  --cloud-id x --password x \
  --skip-drop-old \
  --skip-load \
  --num-concurrency 1,10,50,100 \
  --concurrency-duration 60
```

### 13.2 Cohere 768 10M
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance768D10M \
  --cloud-id x --password x \
  --skip-drop-old \
  --skip-load \
  --num-concurrency 1,10,50,100 \
  --concurrency-duration 60
```

**作用**：验证并发梯度下的吞吐和延迟变化。  
**重点关注**：`conc_num_list`、`conc_qps_list`、`conc_latency_p99_list`。

---

## 14. 过滤搜索测试步骤（条件性执行）

只有在当前 patch 链路已验证支持时才执行。

### 14.1 OpenAI 1% 过滤
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M1P \
  --cloud-id x --password x
```

### 14.2 OpenAI 99% 过滤
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type Performance1536D5M99P \
  --cloud-id x --password x
```

### 14.3 执行前提醒
如果当前环境未验证通过，请在执行记录中写明：

> 当前环境暂未确认过滤搜索 case 可执行，本轮不作为必测项。

---

## 15. Streaming / 边写边搜测试步骤（条件性执行）

只有在当前 patch 链路已验证支持 `StreamingPerformanceCase` 时才执行。

### 15.1 示例命令
```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw \
  --case-type StreamingPerformanceCase \
  --dataset-with-size-type "Large OpenAI (1536dim, 5M)" \
  --cloud-id x --password x
```

### 15.2 执行前提醒
如果当前环境未实测通过，请在文档中标记为：

> 本轮暂不执行，仅保留命令模板。

---

## 16. 结果解读指南（必须看懂）

### 16.1 核心字段定义
| 字段 | 人话解释 | 关注点 |
| :--- | :--- | :--- |
| `run_id` | 本次运行唯一 ID | 用来定位本次结果和日志 |
| `insert_duration` | 纯写入 ES 耗时（秒） | 看数据灌入速度 |
| `optimize_duration` | 索引优化 / force merge 耗时 | 看段合并成本 |
| `load_duration` | 写入 + 优化总耗时 | 看总准备成本 |
| `qps` | 本轮主吞吐指标 | 核心性能指标 |
| `recall` | 召回率 | 是否达到预期 |
| `ndcg` | 排序质量 | 越接近 1 越好 |
| `serial_latency_p99` | 串行查询 p99 | 看最慢请求 |
| `serial_latency_p95` | 串行查询 p95 | 看尾延迟 |
| `conc_num_list` | 并发档位列表 | 看并发梯度 |
| `conc_qps_list` | 各并发档位 QPS | 看吞吐曲线 |
| `conc_latency_p99_list` | 各并发档位 p99 | 看高并发尾延迟 |
| `conc_latency_p95_list` | 各并发档位 p95 | 看延迟分布 |
| `conc_latency_avg_list` | 各并发档位平均延迟 | 看总体趋势 |
| `st_*` | Streaming 指标 | 非流式用例为空是正常现象 |

### 16.2 你之前那条 report 应该怎么理解
如果命令是：

```bash
python3 scripts/vdb_es_cli.py elasticcloudhnsw --case-type Performance1536D500K --cloud-id x --password x
```

那么它的意思是：

> 用 HNSW 路线执行一套 **1536维 / 500K / 默认参数** 的中档 rehearsal 性能 case。

其中：
- `case_type` 决定了数据规格和默认 stages
- 其他参数没写，表示走默认值
- 输出中的 `conc_*` 数组，就是不同并发档位的结果
- `st_*` 为空，说明当前不是 streaming case

### 16.3 常见异常判断
- `qps = 0`：检查 load 是否成功、索引中是否有数据
- `recall 很低`：优先检查 `num-candidates`、`M`、`ef-construction`
- `load_duration 很长`：看是否 force merge 耗时偏大
- `conc_qps 先升后降`：说明并发已到拐点，系统开始饱和

### 16.4 日志位置
优先检查：

```bash
find . -type f | grep -E 'log|result_.*json'
```

若项目已有固定日志目录，也记录在执行记录里。

---

## 17. 到客户现场如何复用

### 17.1 哪些命令原样可复用
- `check_es_connection.py`
- `prepare_builtin_dataset.py`
- `vdb_es_cli.py --help`
- 只要 `.env` 改好，大部分执行命令都可原样复用

### 17.2 哪些内容需要替换
1. `.env` 中的 ES 地址、用户名、密码
2. 数据集目录（如果客户环境离线搬迁）
3. 索引名前缀（如果客户要求隔离）

### 17.3 哪些命令只改少量参数
- 切换数据集：改 `case_type`
- 切换索引类型：改子命令
- 切换参数：改单个 CLI 参数

### 17.4 客户现场最小执行顺序
1. 配置 `.env`
2. `python3 scripts/check_es_connection.py`
3. 确认数据集目录
4. 先对 OpenAI 5M 执行 **只做 Load**
5. 再执行 **只做 Search**
6. 再做参数对比
7. 再做索引类型对比
8. 资源允许时再做 Cohere 10M

### 17.5 离线迁移策略
如果客户现场无法联网：
1. 在本地先执行 `prepare_builtin_dataset.py` 下载 parquet
2. 将整个数据目录打包
3. 搬迁到客户环境
4. 在客户环境中设置 `VDB_DATASET_DIR`

---

## 18. 本轮结论与建议

### 18.1 当前结论
1. 本轮只围绕 **OpenAI 1536 5M** 与 **Cohere 768 10M** 两套数据集组织
2. **基础性能 / 索引类型对比 / 参数对比 / 高并发** 是当前最稳的主线
3. **过滤搜索 / Streaming** 需要在当前 patch 链路下再确认
4. **可以先 load，再 search**，操作是可以解耦的
5. **不同索引类型切换时需要重建索引；同一索引下做参数对比时可以复用已加载索引**

### 18.2 执行建议
1. 第一次一定先跑 OpenAI 5M
2. 先用“只 load”打通，再做“只 search”
3. 参数对比时不要同时改多个参数
4. 结果一定要记录 run_id、命令、结果文件路径
5. 不要在生产环境直接使用默认同名索引执行

