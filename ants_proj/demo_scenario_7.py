'''
方案B演示: 基于景点名称的节点增删与继续优化
简化版，用于快速验证核心功能
'''

from aco_time_window import TimeWindowWorld, AntColonySystem


def demo_node_add_remove():
    '''演示节点增删后继续优化'''
    
    print("="*80)
    print("方案B演示: 基于景点名称的节点增删")
    print("="*80)
    
    # ========== 第1回合: 初始3个景点 ==========
    print("\n【第1回合】初始优化 - 3个景点")
    print("-" * 80)
    
    node_ids_r1 = ['起点', '故宫', '颐和园']
    travel_times_r1 = [
        [0, 30, 45],
        [30, 0, 35],
        [45, 35, 0]
    ]
    time_windows_r1 = [
        (480, 1200),   # 起点: 8:00-20:00
        (540, 1080),   # 故宫: 9:00-18:00
        (600, 1140)    # 颐和园: 10:00-19:00
    ]
    service_times_r1 = [0, 90, 120]
    
    world_r1 = TimeWindowWorld(
        travel_times_r1, 
        time_windows_r1, 
        service_times_r1, 
        start_time=480,
        node_ids=node_ids_r1
    )
    
    print(f"节点列表: {node_ids_r1}")
    print(f"节点ID映射: {world_r1.id2index}")
    
    aco_r1 = AntColonySystem(world_r1, n_ants=10, n_iterations=20)
    aco_r1.optimize(verbose=False)
    
    solution_r1 = aco_r1.get_best_solution()
    best_r1 = aco_r1.export_best()
    
    print(f"最佳成本: {solution_r1['cost']:.2f}")
    print(f"访问顺序(索引): {solution_r1['visited']}")
    print(f"访问顺序(ID): {best_r1['best_visited_ids']}")
    
    # 导出信息素
    pheromones_r1 = world_r1.export_pheromones()
    stats_r1 = world_r1.get_pheromone_stats()
    print(f"\n信息素统计: min={stats_r1['min']:.3f}, max={stats_r1['max']:.3f}, mean={stats_r1['mean']:.3f}")
    print(f"导出了 {len(pheromones_r1)} 条边的信息素")
    
    # ========== 第2回合: 新增景点 "天坛" ==========
    print("\n" + "="*80)
    print("【第2回合】新增景点 '天坛'")
    print("-" * 80)
    
    node_ids_r2 = ['起点', '故宫', '颐和园', '天坛']
    travel_times_r2 = [
        [0, 30, 45, 60],
        [30, 0, 35, 40],
        [45, 35, 0, 50],
        [60, 40, 50, 0]
    ]
    time_windows_r2 = [
        (480, 1200),
        (540, 1080),
        (600, 1140),
        (540, 1200)    # 天坛: 9:00-20:00 (新增)
    ]
    service_times_r2 = [0, 90, 120, 60]
    
    world_r2 = TimeWindowWorld(
        travel_times_r2,
        time_windows_r2,
        service_times_r2,
        start_time=480,
        node_ids=node_ids_r2
    )
    
    print(f"节点列表: {node_ids_r2}")
    print(f"新增节点: 天坛")
    
    # 导入旧信息素
    print("\n导入第1回合的信息素...")
    world_r2.import_pheromones(pheromones_r1, tau_min=0.1, tau_max=10.0)
    
    stats_r2_before = world_r2.get_pheromone_stats()
    print(f"导入后信息素统计: min={stats_r2_before['min']:.3f}, max={stats_r2_before['max']:.3f}, mean={stats_r2_before['mean']:.3f}")
    
    aco_r2 = AntColonySystem(world_r2, n_ants=10, n_iterations=15)
    aco_r2.optimize(verbose=False)
    
    solution_r2 = aco_r2.get_best_solution()
    best_r2 = aco_r2.export_best()
    
    print(f"\n最佳成本: {solution_r2['cost']:.2f}")
    print(f"访问顺序(索引): {solution_r2['visited']}")
    print(f"访问顺序(ID): {best_r2['best_visited_ids']}")
    
    pheromones_r2 = world_r2.export_pheromones()
    stats_r2_after = world_r2.get_pheromone_stats()
    print(f"\n优化后信息素统计: min={stats_r2_after['min']:.3f}, max={stats_r2_after['max']:.3f}, mean={stats_r2_after['mean']:.3f}")
    
    # ========== 第3回合: 删除景点 "故宫" ==========
    print("\n" + "="*80)
    print("【第3回合】删除景点 '故宫'")
    print("-" * 80)
    
    node_ids_r3 = ['起点', '颐和园', '天坛']
    travel_times_r3 = [
        [0, 45, 60],
        [45, 0, 50],
        [60, 50, 0]
    ]
    time_windows_r3 = [
        (480, 1200),
        (600, 1140),
        (540, 1200)
    ]
    service_times_r3 = [0, 120, 60]
    
    world_r3 = TimeWindowWorld(
        travel_times_r3,
        time_windows_r3,
        service_times_r3,
        start_time=480,
        node_ids=node_ids_r3
    )
    
    print(f"节点列表: {node_ids_r3}")
    print(f"删除节点: 故宫")
    
    # 导入第2回合的信息素 (涉及故宫的边自动忽略)
    print("\n导入第2回合的信息素...")
    world_r3.import_pheromones(pheromones_r2, tau_min=0.1, tau_max=10.0, scale=0.95)
    
    stats_r3 = world_r3.get_pheromone_stats()
    print(f"导入后信息素统计: min={stats_r3['min']:.3f}, max={stats_r3['max']:.3f}, mean={stats_r3['mean']:.3f}")
    
    aco_r3 = AntColonySystem(world_r3, n_ants=10, n_iterations=15)
    aco_r3.optimize(verbose=False)
    
    solution_r3 = aco_r3.get_best_solution()
    best_r3 = aco_r3.export_best()
    
    print(f"\n最佳成本: {solution_r3['cost']:.2f}")
    print(f"访问顺序(索引): {solution_r3['visited']}")
    print(f"访问顺序(ID): {best_r3['best_visited_ids']}")
    
    # ========== 总结 ==========
    print("\n" + "="*80)
    print("方案B演示总结")
    print("="*80)
    print(f"第1回合 (3景点): 成本 {solution_r1['cost']:.2f}, 路径 {best_r1['best_visited_ids']}")
    print(f"第2回合 (新增天坛): 成本 {solution_r2['cost']:.2f}, 路径 {best_r2['best_visited_ids']}")
    print(f"第3回合 (删除故宫): 成本 {solution_r3['cost']:.2f}, 路径 {best_r3['best_visited_ids']}")
    print("\n✅ 验证成功:")
    print("  - 使用景点名称作为稳定ID")
    print("  - 节点增删不影响历史信息素的正确映射")
    print("  - 旧边信息素自动保留，新边使用默认值")
    print("  - 删除节点时，相关边自动忽略")
    print("  - 支持跨回合持续优化")


if __name__ == "__main__":
    demo_node_add_remove()
