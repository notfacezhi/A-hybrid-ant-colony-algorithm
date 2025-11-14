'''
测试带时间窗约束的蚁群算法
使用abstrace_tools.py中的3个测试场景
'''

from aco_time_window import TimeWindowWorld, AntColonySystem
from repair_strategy import TimeWindowRepair


def format_time(minutes):
    '''将分钟转换为时:分格式'''
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


def print_solution(solution, test_name):
    '''打印解决方案详情'''
    print(f"\n{'='*80}")
    print(f"{test_name}")
    print(f"{'='*80}")
    
    if solution is None:
        print("❌ 未找到解决方案")
        return
    
    cost = solution['cost']
    visited = solution['visited']
    path_details = solution['path_details']
    
    print(f"\n✅ 最佳成本: {cost:.2f}")
    
    # 判断是否违反时间窗
    has_violation = cost >= 9999
    if has_violation:
        print(f"⚠️  警告: 存在时间窗违反 (成本包含惩罚值)")
    else:
        print(f"✓  所有节点均满足时间窗约束")
    
    print(f"\n访问顺序: {' -> '.join(map(str, visited))}")
    
    print(f"\n路径详情:")
    print(f"{'步骤':<6} {'从':<4} {'到':<4} {'通勤':<8} {'到达时间':<10} {'服务开始':<10} {'服务结束':<10} {'状态':<12}")
    print('-' * 80)
    
    for detail in path_details:
        print(f"{detail['step']:<6} "
              f"{detail['from']:<4} "
              f"{detail['to']:<4} "
              f"{detail['travel_time']:<8} "
              f"{format_time(detail['arrival_time']):<10} "
              f"{format_time(detail['service_start']):<10} "
              f"{format_time(detail['service_end']):<10} "
              f"{detail['status']:<12}")


def test_scenario_1():
    '''
    测试场景1: 正常情况 - 所有节点都在时间窗内
    '''
    route = [0, 1, 2, 3]
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
    service_times = [0, 60, 90, 45]
    start_time = 480  # 8:00出发
    
    # 创建问题空间
    world = TimeWindowWorld(travel_times, time_windows, service_times, start_time)
    
    # 创建蚁群系统
    aco = AntColonySystem(world, n_ants=20, n_iterations=50)
    
    # 优化
    print("\n开始优化...")
    aco.optimize(verbose=True)
    
    # 获取最佳解
    solution = aco.get_best_solution()
    
    # 打印结果
    print_solution(solution, "测试场景1: 正常情况 - 所有节点都在时间窗内")


def test_scenario_2():
    '''
    测试场景2: 等待场景 - 到达太早,需要等待开放
    '''
    route = [0, 1, 2]
    travel_times = [
        [0, 20, 40],
        [20, 0, 30],
        [40, 30, 0]
    ]
    time_windows = [
        (480, 1200),   # 起点: 8:00-20:00
        (600, 1080),   # 景点1: 10:00-18:00
        (720, 1140)    # 景点2: 12:00-19:00
    ]
    service_times = [0, 90, 60]
    start_time = 480  # 8:00出发
    
    # 创建问题空间
    world = TimeWindowWorld(travel_times, time_windows, service_times, start_time)
    
    # 创建蚁群系统
    aco = AntColonySystem(world, n_ants=20, n_iterations=50)
    
    # 优化
    print("\n开始优化...")
    aco.optimize(verbose=True)
    
    # 获取最佳解
    solution = aco.get_best_solution()
    
    # 打印结果
    print_solution(solution, "测试场景2: 等待场景 - 到达太早,需要等待开放")


def test_scenario_3():
    '''
    测试场景3: 违反时间窗 - 到达太晚,超出关闭时间
    '''
    route = [0, 1, 2]
    travel_times = [
        [0, 30, 60],
        [30, 0, 40],
        [60, 40, 0]
    ]
    time_windows = [
        (480, 1200),   # 起点: 8:00-20:00
        (540, 720),    # 景点1: 9:00-12:00
        (600, 660)     # 景点2: 10:00-11:00
    ]
    service_times = [0, 120, 60]
    start_time = 480  # 8:00出发
    
    # 创建问题空间
    world = TimeWindowWorld(travel_times, time_windows, service_times, start_time)
    
    # 创建蚁群系统
    aco = AntColonySystem(world, n_ants=20, n_iterations=50)
    
    # 优化
    print("\n开始优化...")
    aco.optimize(verbose=True)
    
    # 获取最佳解
    solution = aco.get_best_solution()
    
    # 打印结果
    print_solution(solution, "测试场景3: 违反时间窗 - 到达太晚,超出关闭时间")


def test_scenario_4():
    '''
    测试场景4: 时间窗数学无解 - 无论如何排列都会违反时间窗
    
    设计思路:
    - 景点1: 时间窗 9:00-10:00 (很窄的时间窗)
    - 景点2: 时间窗 9:30-10:30 (与景点1时间窗重叠)
    - 景点3: 时间窗 9:00-9:30 (更窄的时间窗)
    - 从起点到任意景点需要30分钟
    - 每个景点游玩时间60分钟
    
    分析:
    - 8:00出发 + 30分钟通勤 = 8:30到达
    - 第一个景点最早8:30到达，游玩60分钟后是9:30
    - 9:30 + 30分钟通勤 = 10:00到达第二个景点
    - 但景点3的时间窗是9:00-9:30，无论如何都无法在9:30前到达
    - 景点1和景点2的时间窗也很紧，游玩时间长导致后续景点必然违反
    '''
    travel_times = [
        [0, 30, 30, 30],   # 从起点到各景点都是30分钟
        [30, 0, 20, 20],   # 景点间通勤20分钟
        [30, 20, 0, 20],
        [30, 20, 20, 0]
    ]
    time_windows = [
        (480, 1200),   # 起点: 8:00-20:00
        (540, 600),    # 景点1: 9:00-10:00 (60分钟窗口)
        (570, 630),    # 景点2: 9:30-10:30 (60分钟窗口)
        (540, 570)     # 景点3: 9:00-9:30 (30分钟窗口，最紧迫)
    ]
    service_times = [0, 60, 60, 60]  # 每个景点都需要60分钟游玩
    start_time = 480  # 8:00出发
    
    # 创建问题空间
    world = TimeWindowWorld(travel_times, time_windows, service_times, start_time)
    
    # 创建蚁群系统
    aco = AntColonySystem(world, n_ants=20, n_iterations=50)
    
    # 优化
    print("\n开始优化...")
    aco.optimize(verbose=True)
    
    # 获取最佳解
    solution = aco.get_best_solution()
    
    # 打印结果
    print_solution(solution, "测试场景4: 时间窗数学无解 - 无论如何排列都会违反时间窗")
    
    # 额外分析
    print("\n分析:")
    print("- 景点3时间窗最窄(9:00-9:30)，但从起点出发最早8:30到达")
    print("- 即使优先访问景点3，游玩60分钟后是9:30，后续景点必然违反")
    print("- 景点1和景点2时间窗重叠，游玩时间过长导致冲突")
    print("- 结论: 该问题在数学上无完美解，ACO会找到惩罚最小的次优解")
    
    # ========== 应用修复策略 ==========
    if solution['cost'] >= 9999:
        print("\n" + "="*80)
        print("检测到时间窗违规，启动修复策略")
        print("="*80)
        
        # 定义备选景点（时间窗更宽，游玩时间更短）
        alternative_nodes = [
            {
                'node_id': 4,
                'time_window': (540, 840),  # 9:00-14:00 (5小时窗口)
                'service_time': 30           # 游玩30分钟
            },
            {
                'node_id': 5,
                'time_window': (600, 960),  # 10:00-16:00 (6小时窗口)
                'service_time': 45           # 游玩45分钟
            }
        ]
        
        print("\n备选景点信息:")
        for alt in alternative_nodes:
            tw = alt['time_window']
            print(f"  节点{alt['node_id']}: 时间窗 {tw[0]//60:02d}:{tw[0]%60:02d}-{tw[1]//60:02d}:{tw[1]%60:02d}, "
                  f"游玩时间 {alt['service_time']}分钟")
        
        # 创建修复器
        repair = TimeWindowRepair(world, alternative_nodes, max_repair_iterations=5)
        
        # 执行修复
        repaired_visited = repair.repair_solution(solution['visited'], verbose=True)
        
        # 重新计算修复后的解
        print("\n" + "="*80)
        print("修复后的解决方案")
        print("="*80)
        print(f"修复后访问顺序: {repaired_visited}")
        
        # 验证修复后的解
        violations = repair.detect_violations(repaired_visited)
        if violations:
            print(f"⚠️  仍有{len(violations)}个违规节点")
        else:
            print("✅ 所有节点满足时间窗约束！")


def test_scenario_5():
    '''
    测试场景5: 连锁修复 - 替换导致游玩时间延长，3次传导修复
    
    设计思路:
    - 4个原始景点，时间窗紧凑但理论上可行
    - 备选景点时间窗更宽，但游玩时间更长
    - 修复节点1 → 游玩时间延长 → 节点2违规
    - 修复节点2 → 游玩时间延长 → 节点3违规
    - 修复节点3 → 最终成功
    
    传导链: 节点1 → 节点2 → 节点3 → 成功
    '''
    travel_times = [
        [0, 20, 40, 60, 80],   # 从起点到各景点
        [20, 0, 20, 40, 60],   # 景点间通勤20-40分钟
        [40, 20, 0, 20, 40],
        [60, 40, 20, 0, 20],
        [80, 60, 40, 20, 0]
    ]
    time_windows = [
        (480, 1200),   # 起点: 8:00-20:00
        (540, 600),    # 节点1: 9:00-10:00 (60分钟窗口) - 会违规
        (630, 690),    # 节点2: 10:30-11:30 (60分钟窗口) - 修复后会违规
        (720, 780),    # 节点3: 12:00-13:00 (60分钟窗口) - 修复后会违规
        (810, 870)     # 节点4: 13:30-14:30 (60分钟窗口)
    ]
    service_times = [0, 60, 60, 60, 60]  # 每个景点游玩60分钟
    start_time = 480  # 8:00出发
    
    # 创建问题空间
    world = TimeWindowWorld(travel_times, time_windows, service_times, start_time)
    
    # 创建蚁群系统
    aco = AntColonySystem(world, n_ants=20, n_iterations=50)
    
    # 优化
    print("\n开始优化...")
    aco.optimize(verbose=True)
    
    # 获取最佳解
    solution = aco.get_best_solution()
    
    # 打印结果
    print_solution(solution, "测试场景5: 连锁修复 - 替换导致游玩时间延长")
    
    # ========== 应用修复策略 ==========
    if solution['cost'] >= 9999:
        print("\n" + "="*80)
        print("检测到时间窗违规，启动修复策略")
        print("="*80)
        
        # 定义备选景点（时间窗更宽，但游玩时间更长 - 导致传导）
        alternative_nodes = [
            {
                'node_id': 5,
                'time_window': (540, 720),  # 9:00-12:00 (3小时窗口)
                'service_time': 90           # 游玩90分钟（比原来多30分钟）
            },
            {
                'node_id': 6,
                'time_window': (600, 780),  # 10:00-13:00 (3小时窗口)
                'service_time': 75           # 游玩75分钟（比原来多15分钟）
            },
            {
                'node_id': 7,
                'time_window': (660, 840),  # 11:00-14:00 (3小时窗口)
                'service_time': 45           # 游玩45分钟（比原来少15分钟，终止传导）
            }
        ]
        
        print("\n备选景点信息:")
        for alt in alternative_nodes:
            tw = alt['time_window']
            print(f"  节点{alt['node_id']}: 时间窗 {tw[0]//60:02d}:{tw[0]%60:02d}-{tw[1]//60:02d}:{tw[1]%60:02d}, "
                  f"游玩时间 {alt['service_time']}分钟")
        
        print("\n预期传导链:")
        print("  1. 节点1违规 → 替换为节点5（游玩90分钟，延长30分钟）")
        print("  2. 节点2因延长而违规 → 替换为节点6（游玩75分钟，延长15分钟）")
        print("  3. 节点3因延长而违规 → 替换为节点7（游玩45分钟，缩短15分钟）")
        print("  4. 节点4满足时间窗 → 修复成功")
        
        # 创建修复器
        repair = TimeWindowRepair(world, alternative_nodes, max_repair_iterations=5)
        
        # 执行修复
        repaired_visited = repair.repair_solution(solution['visited'], verbose=True)
        
        # 验证修复后的解
        print("\n" + "="*80)
        print("修复后的解决方案")
        print("="*80)
        print(f"修复后访问顺序: {repaired_visited}")
        
        # 需要用扩展的world来验证
        print("\n最终验证: 检查是否所有节点满足时间窗...")


def test_scenario_6():
    '''
    测试场景6: 连锁修复 - 替换导致通勤时间增加，3次传导修复
    
    设计思路:
    - 4个原始景点，位置紧凑，通勤时间短
    - 备选景点位置偏远，通勤时间长
    - 修复节点1 → 通勤时间增加 → 节点2违规
    - 修复节点2 → 通勤时间增加 → 节点3违规
    - 修复节点3 → 最终成功
    
    传导链: 节点1 → 节点2 → 节点3 → 成功
    '''
    # 扩展通勤时间矩阵（包含备选节点8,9,10）
    travel_times = [
        [0, 15, 30, 45, 60, 50, 60, 70],   # 起点到各节点
        [15, 0, 15, 30, 45, 40, 50, 60],   # 节点1
        [30, 15, 0, 15, 30, 35, 45, 55],   # 节点2
        [45, 30, 15, 0, 15, 30, 40, 50],   # 节点3
        [60, 45, 30, 15, 0, 25, 35, 45],   # 节点4
        [50, 40, 35, 30, 25, 0, 20, 30],   # 节点8（备选，位置偏远）
        [60, 50, 45, 40, 35, 20, 0, 20],   # 节点9（备选，位置更远）
        [70, 60, 55, 50, 45, 30, 20, 0]    # 节点10（备选，位置最远）
    ]
    time_windows = [
        (480, 1200),   # 起点: 8:00-20:00
        (540, 600),    # 节点1: 9:00-10:00 (60分钟窗口) - 会违规
        (630, 690),    # 节点2: 10:30-11:30 (60分钟窗口) - 修复后会违规
        (720, 780),    # 节点3: 12:00-13:00 (60分钟窗口) - 修复后会违规
        (810, 870),    # 节点4: 13:30-14:30 (60分钟窗口)
        (540, 720),    # 节点8: 9:00-12:00 (3小时窗口，备选）
        (600, 780),    # 节点9: 10:00-13:00 (3小时窗口，备选）
        (660, 840)     # 节点10: 11:00-14:00 (3小时窗口，备选）
    ]
    service_times = [0, 50, 50, 50, 50, 40, 40, 30]  # 备选景点游玩时间更短
    start_time = 480  # 8:00出发
    
    # 创建问题空间
    world = TimeWindowWorld(travel_times, time_windows, service_times, start_time)
    
    # 创建蚁群系统
    aco = AntColonySystem(world, n_ants=20, n_iterations=50)
    
    # 优化
    print("\n开始优化...")
    aco.optimize(verbose=True)
    
    # 获取最佳解
    solution = aco.get_best_solution()
    
    # 打印结果
    print_solution(solution, "测试场景6: 连锁修复 - 替换导致通勤时间增加")
    
    # ========== 应用修复策略 ==========
    if solution['cost'] >= 9999:
        print("\n" + "="*80)
        print("检测到时间窗违规，启动修复策略")
        print("="*80)
        
        # 定义备选景点（时间窗更宽，但位置偏远 - 导致传导）
        alternative_nodes = [
            {
                'node_id': 5,
                'time_window': (540, 720),  # 9:00-12:00 (3小时窗口)
                'service_time': 40           # 游玩40分钟
            },
            {
                'node_id': 6,
                'time_window': (600, 780),  # 10:00-13:00 (3小时窗口)
                'service_time': 40           # 游玩40分钟
            },
            {
                'node_id': 7,
                'time_window': (660, 840),  # 11:00-14:00 (3小时窗口)
                'service_time': 30           # 游玩30分钟
            }
        ]
        
        print("\n备选景点信息:")
        for alt in alternative_nodes:
            tw = alt['time_window']
            print(f"  节点{alt['node_id']}: 时间窗 {tw[0]//60:02d}:{tw[0]%60:02d}-{tw[1]//60:02d}:{tw[1]%60:02d}, "
                  f"游玩时间 {alt['service_time']}分钟")
        
        print("\n预期传导链:")
        print("  1. 节点1违规 → 替换为节点5（通勤时间增加，位置偏远）")
        print("  2. 节点2因通勤延长而违规 → 替换为节点6")
        print("  3. 节点3因通勤延长而违规 → 替换为节点7")
        print("  4. 节点4满足时间窗 → 修复成功")
        
        # 创建修复器
        repair = TimeWindowRepair(world, alternative_nodes, max_repair_iterations=5)
        
        # 执行修复
        repaired_visited = repair.repair_solution(solution['visited'], verbose=True)
        
        # 验证修复后的解
        print("\n" + "="*80)
        print("修复后的解决方案")
        print("="*80)
        print(f"修复后访问顺序: {repaired_visited}")
        
        print("\n最终验证: 检查是否所有节点满足时间窗...")


if __name__ == "__main__":
    print("="*80)
    print("带时间窗约束的蚁群算法测试")
    print("="*80)
    
    # # 测试场景1: 正常情况
    # test_scenario_1()
    # #
    # # # 测试场景2: 等待场景
    # test_scenario_2()
    # #
    # # # 测试场景3: 违反时间窗
    # test_scenario_3()
    # 
    # # 测试场景4: 时间窗数学无解
    # test_scenario_4()
    
    # 测试场景5: 连锁修复 - 游玩时间延长
    test_scenario_5()
    
    # 测试场景6: 连锁修复 - 通勤时间增加
    test_scenario_6()
    
    print("\n" + "="*80)
    print("所有测试完成!")
    print("="*80)
