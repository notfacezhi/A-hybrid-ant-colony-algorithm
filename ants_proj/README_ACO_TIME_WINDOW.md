# 带时间窗约束的蚁群算法 (ACO with Time Windows)

## 概述

实现了带时间窗约束的蚁群算法，用于解决旅游路线规划问题。支持软时间窗机制和自动修复策略。

## 核心特性

### 1. 软时间窗ACO算法
- **早到等待**: 不惩罚，但占用时间
- **晚到惩罚**: 违反时间窗 +9999 惩罚
- **时间窗紧迫度启发**: 优先选择即将关闭的景点
- **信息素引导**: 历史经验累积

### 2. 修复策略（针对数学无解情况）
- **检测违规节点**: 自动识别违反时间窗的位置
- **替换策略**: 用时间窗更宽的备选景点替换
- **局部ACO优化**: 对剩余部分重新优化
- **迭代修复**: 最多5次修复尝试

## 文件说明

### `aco_time_window.py` - 核心算法
包含4个核心类：
- `Edge`: 边，存储通勤时间和信息素
- `TimeWindowWorld`: 问题空间，管理时间窗、通勤时间矩阵
- `Ant`: 单只蚂蚁，构建路径
- `AntColonySystem`: 蚁群系统，管理优化过程
- `TimeWindowRepair`: 修复策略，处理无解情况

### `test_aco_travel.py` - 测试脚本
包含4个测试场景：
1. **正常情况**: 所有节点满足时间窗
2. **等待场景**: 早到需要等待
3. **违反时间窗**: 晚到超出关闭时间
4. **数学无解**: 无论如何排列都会违反（含修复策略）

## 使用方法

### 基本使用

```python
from aco_time_window import TimeWindowWorld, AntColonySystem

# 定义问题
travel_times = [
    [0, 30, 45, 60],
    [30, 0, 20, 40],
    [45, 20, 0, 25],
    [60, 40, 25, 0]
]
time_windows = [
    (480, 1200),   # 起点: 8:00-20:00
    (540, 1080),   # 景点1: 9:00-18:00
    (600, 1140),   # 景点2: 10:00-19:00
    (540, 1200)    # 景点3: 9:00-20:00
]
service_times = [0, 60, 90, 45]  # 游玩时间（分钟）
start_time = 480  # 8:00出发

# 创建问题空间
world = TimeWindowWorld(travel_times, time_windows, service_times, start_time)

# 创建蚁群系统
aco = AntColonySystem(world, n_ants=20, n_iterations=50)

# 优化
aco.optimize(verbose=True)

# 获取结果
solution = aco.get_best_solution()
print(f"最佳成本: {solution['cost']}")
print(f"访问顺序: {solution['visited']}")
```

### 使用修复策略

```python
from aco_time_window import TimeWindowWorld, AntColonySystem, TimeWindowRepair

# ... 创建world和运行ACO ...

# 如果存在违规
if solution['cost'] >= 9999:
    # 定义备选景点
    alternative_nodes = [
        {
            'node_id': 4,
            'time_window': (540, 840),  # 9:00-14:00
            'service_time': 30
        },
        {
            'node_id': 5,
            'time_window': (600, 960),  # 10:00-16:00
            'service_time': 45
        }
    ]
    
    # 创建修复器
    repair = TimeWindowRepair(world, alternative_nodes, max_repair_iterations=5)
    
    # 执行修复
    repaired_visited = repair.repair_solution(solution['visited'], verbose=True)
    
    # 验证结果
    violations = repair.detect_violations(repaired_visited)
    if not violations:
        print("✅ 修复成功！")
```

## 运行测试

```bash
cd d:\application\code\A-hybrid-ant-colony-algorithm\ants_proj
python test_aco_travel.py
```

## 参数说明

### AntColonySystem 参数
- `n_ants`: 蚂蚁数量（默认20）
- `n_iterations`: 迭代次数（默认50）
- `alpha`: 信息素权重（默认1）
- `beta`: 启发函数权重（默认3）
- `evaporation_rate`: 信息素挥发率（默认0.2）
- `pheromone_deposit`: 信息素沉积量（默认1.0）
- `elite_ratio`: 精英蚂蚁比例（默认0.3）

### TimeWindowRepair 参数
- `alternative_nodes_info`: 备选景点信息列表
- `max_repair_iterations`: 最大修复次数（默认5）

## 算法流程

### ACO主流程
1. 初始化信息素
2. 每只蚂蚁构建路径：
   - 计算候选边概率（信息素 + 启发函数）
   - 轮盘赌选择下一个节点
   - 检查时间窗约束
   - 更新成本
3. 更新信息素（所有蚂蚁 + 精英蚂蚁）
4. 信息素挥发
5. 重复2-4直到收敛

### 修复策略流程
1. 检测违规节点位置
2. 找到时间窗更宽的备选景点
3. 创建扩展问题空间（包含备选节点）
4. 对剩余部分运行局部ACO（10只蚂蚁，20轮）
5. 如果成功，更新路径；否则删除违规节点
6. 重复1-5直到无违规或达到最大次数

## 设计亮点

1. **局部优化策略**: 只优化违规节点及之后的部分，保持前面满足约束的路径
2. **动态问题空间**: 自动扩展问题空间以包含备选节点
3. **小规模局部ACO**: 快速验证修复方案的可行性
4. **智能替换**: 优先选择时间窗最宽的备选景点
5. **失败回退**: 修复失败时返回原路径，保证鲁棒性

## 注意事项

1. 备选节点的通勤时间默认为25分钟，实际使用时应提供准确数据
2. 修复策略适用于部分节点违规的情况，全局无解时效果有限
3. 局部ACO的规模（10只蚂蚁，20轮）可根据实际情况调整
4. 时间单位统一为分钟，时间窗格式为 (开始时间, 结束时间)

## 扩展建议

1. 添加更多启发函数（如考虑景点评分、拥挤度等）
2. 支持多日行程规划
3. 添加可视化功能（路线图、时间甘特图）
4. 支持动态调整备选节点的通勤时间
5. 添加更多修复策略（如2-opt局部搜索）
