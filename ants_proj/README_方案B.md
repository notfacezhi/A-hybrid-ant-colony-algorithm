# 方案B: 基于节点ID的动态图优化

## 概述

方案B通过引入稳定的节点ID（如景点名称），实现了节点增删后信息素的正确映射和持续优化。这使得蚁群算法可以与Agent系统结合，支持跨回合的学习延续。

## 核心改动

### 1. TimeWindowWorld 增强

#### 新增属性
- `node_ids`: 节点ID列表（如 `['起点', '故宫', '颐和园']`）
- `id2index`: ID到索引的映射字典
- `index2id`: 索引到ID的映射字典

#### 新增方法
- `export_pheromones()`: 导出所有边的信息素
  - 返回: `[{'from_id': X, 'to_id': Y, 'pheromone': v}, ...]`
  
- `import_pheromones(records, tau_min=None, tau_max=None, scale=1.0)`: 导入信息素
  - `records`: 信息素记录列表
  - `tau_min/tau_max`: 信息素边界（防止饱和/过小）
  - `scale`: 缩放因子（用于温和重置，如0.95）
  
- `get_pheromone_stats()`: 获取信息素统计
  - 返回: `{'min': x, 'max': y, 'mean': z, 'median': w}`

### 2. AntColonySystem 增强

#### 新增方法
- `export_best()`: 导出最佳解摘要
  - 返回: `{'best_cost': x, 'best_visited_ids': [...], 'best_path': [...], 'cost_history': [...]}`
  
- `import_best(summary)`: 导入最佳解（可选，用于展示）
  
- `continue_optimize(n_more_iterations, verbose=True)`: 继续优化
  - 不重置信息素和最佳解
  - 适合跨回合增量优化

## 使用示例

### 场景1: 初始优化

```python
from aco_time_window import TimeWindowWorld, AntColonySystem

# 定义节点ID（使用景点名称）
node_ids = ['起点', '故宫', '颐和园', '天坛']

# 创建问题空间
world = TimeWindowWorld(
    travel_times, 
    time_windows, 
    service_times, 
    start_time=480,
    node_ids=node_ids  # 关键参数
)

# 优化
aco = AntColonySystem(world, n_ants=20, n_iterations=50)
aco.optimize(verbose=True)

# 导出信息素和最佳解
pheromones = world.export_pheromones()
best_solution = aco.export_best()

# 保存到文件或数据库
import json
with open('pheromones.json', 'w') as f:
    json.dump(pheromones, f)
```

### 场景2: 新增节点后继续优化

```python
# 新增景点 "鸟巢"
node_ids_new = ['起点', '故宫', '颐和园', '天坛', '鸟巢']

# 扩展矩阵和配置
travel_times_new = [
    [0, 30, 45, 60, 40],
    [30, 0, 35, 40, 25],
    [45, 35, 0, 50, 30],
    [60, 40, 50, 0, 45],
    [40, 25, 30, 45, 0]
]
# ... 扩展 time_windows_new 和 service_times_new

# 创建新的问题空间
world_new = TimeWindowWorld(
    travel_times_new,
    time_windows_new,
    service_times_new,
    start_time=480,
    node_ids=node_ids_new
)

# 导入旧信息素（旧边保留，新边使用默认值）
world_new.import_pheromones(pheromones, tau_min=0.1, tau_max=10.0)

# 继续优化
aco_new = AntColonySystem(world_new, n_ants=20, n_iterations=30)
aco_new.optimize(verbose=True)
```

### 场景3: 删除节点后继续优化

```python
# 删除景点 "天坛"
node_ids_reduced = ['起点', '故宫', '颐和园', '鸟巢']

# 缩减矩阵和配置
travel_times_reduced = [
    [0, 30, 45, 40],
    [30, 0, 35, 25],
    [45, 35, 0, 30],
    [40, 25, 30, 0]
]
# ... 缩减 time_windows 和 service_times

# 创建新的问题空间
world_reduced = TimeWindowWorld(
    travel_times_reduced,
    time_windows_reduced,
    service_times_reduced,
    start_time=480,
    node_ids=node_ids_reduced
)

# 导入信息素（涉及天坛的边自动忽略）
world_reduced.import_pheromones(pheromones_new, tau_min=0.1, tau_max=10.0, scale=0.95)

# 继续优化
aco_reduced = AntColonySystem(world_reduced, n_ants=20, n_iterations=30)
aco_reduced.optimize(verbose=True)
```

## 关键优势

### 1. 稳定性
- 使用业务ID（景点名称）而非数组索引
- 节点增删/重排不会破坏历史信息素的含义

### 2. 灵活性
- 支持任意节点增删
- 新增节点只影响与它相关的新边
- 删除节点仅清除与它相关的边

### 3. 持续学习
- 旧边的信息素自动保留
- 新边使用默认值或均值初始化
- 支持跨回合增量优化

### 4. 防止早熟
- `tau_min/tau_max` 裁剪信息素范围
- `scale` 参数支持温和重置（如0.95）
- 可配合 `evaporation_rate` 调整探索/开发平衡

## 与Agent结合的典型流程

```python
# Agent 第1回合
world_1 = TimeWindowWorld(..., node_ids=['起点', 'A', 'B'])
aco_1 = AntColonySystem(world_1, ...)
aco_1.optimize()
pheromones_1 = world_1.export_pheromones()
# 保存 pheromones_1 到持久化存储

# Agent 第2回合（用户新增景点C）
world_2 = TimeWindowWorld(..., node_ids=['起点', 'A', 'B', 'C'])
world_2.import_pheromones(pheromones_1)  # 复用历史学习
aco_2 = AntColonySystem(world_2, ...)
aco_2.optimize()
pheromones_2 = world_2.export_pheromones()
# 保存 pheromones_2

# Agent 第3回合（用户删除景点A）
world_3 = TimeWindowWorld(..., node_ids=['起点', 'B', 'C'])
world_3.import_pheromones(pheromones_2, scale=0.95)  # 温和重置
aco_3 = AntColonySystem(world_3, ...)
aco_3.continue_optimize(20)  # 继续优化20轮
```

## 参数建议

### 信息素边界
- `tau_min=0.1`: 防止信息素过小，保持探索
- `tau_max=10.0`: 防止信息素饱和，避免早熟

### 温和重置
- `scale=0.95`: 保留95%的历史信息素，注入5%的不确定性
- 适用于节点集变化较大时

### 挥发率调整
- 节点增加时：可临时提高 `evaporation_rate`（如0.3）鼓励探索
- 节点删除时：可保持或降低 `evaporation_rate`（如0.15）稳定收敛

## 测试文件

- `test_aco_travel.py`: 完整测试场景7（3个回合演示）
- `demo_scenario_7.py`: 简化演示脚本（快速验证）

## 运行测试

```bash
# 完整测试（包含详细输出）
python test_aco_travel.py

# 简化演示
python demo_scenario_7.py
```

## 注意事项

1. **节点ID唯一性**: 确保 `node_ids` 中的ID唯一且稳定
2. **矩阵一致性**: 新增/删除节点时，确保 `travel_times`、`time_windows`、`service_times` 的维度一致
3. **起点固定**: 通常第一个节点（索引0）为起点，建议保持不变
4. **信息素初始化**: 新边的信息素默认为 `init_pheromone`，也可用旧分布的均值
5. **最佳解失效**: 节点集变化后，旧的 `best_path` 可能失效，仅保留 `best_cost` 和 `cost_history` 用于监控

## 扩展方向

1. **自适应参数**: 根据节点集变化幅度自动调整 `scale` 和 `evaporation_rate`
2. **信息素迁移**: 为新增节点的边使用"相似节点"的信息素初始化
3. **早停策略**: 监控 `cost_history`，若连续N轮无改进则提前终止
4. **多目标优化**: 同时优化成本、时间窗违规数、路径平衡度等
