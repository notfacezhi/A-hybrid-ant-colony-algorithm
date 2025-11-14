'''
时间窗修复策略模块

将修复逻辑与ACO算法解耦，提供独立的修复功能
'''

import numpy as np
from aco_time_window import TimeWindowWorld, Ant


class TimeWindowRepair:
    '''
    时间窗修复策略
    
    针对时间窗数学无解的情况进行修复：
    1. 检测违规节点位置
    2. 替换为时间窗更宽的备选景点
    3. 对剩余部分运行局部ACO
    4. 循环直到无违规或达到最大修复次数
    '''
    
    def __init__(self, world, alternative_nodes_info, max_repair_iterations=5):
        '''
        参数:
        - world: TimeWindowWorld对象
        - alternative_nodes_info: 备选景点信息列表
          格式: [{'node_id': 4, 'time_window': (540, 840), 'service_time': 30}, ...]
        - max_repair_iterations: 最大修复次数 (默认5)
        '''
        self.world = world
        self.alternative_nodes_info = alternative_nodes_info
        self.max_repair_iterations = max_repair_iterations
    
    def detect_violations(self, visited, world=None):
        '''
        检测违规节点位置
        
        参数:
        - visited: 访问顺序列表 [0, 1, 2, 3]
        - world: 可选的问题空间，默认使用self.world
        
        返回:
        - violations: [(违规节点, 违规位置, 到达时间, 关闭时间), ...]
        '''
        if world is None:
            world = self.world
        
        violations = []
        current_time = world.start_time
        
        for i in range(1, len(visited)):  # 跳过起点
            from_node = visited[i - 1]
            to_node = visited[i]
            
            # 检查节点是否在范围内
            if from_node >= len(world.travel_times) or to_node >= len(world.travel_times):
                continue
            
            # 计算通勤时间和到达时间
            travel_time = world.travel_times[from_node][to_node]
            arrival_time = current_time + travel_time
            
            # 获取时间窗
            if to_node >= len(world.time_windows):
                continue
            open_time, close_time = world.time_windows[to_node]
            
            # 检查是否违规（晚到）
            if arrival_time > close_time:
                violations.append((to_node, i, arrival_time, close_time))
            
            # 更新当前时间
            service_start = max(arrival_time, open_time)
            if to_node < len(world.service_times):
                current_time = service_start + world.service_times[to_node]
            else:
                current_time = service_start
        
        return violations
    
    def get_window_width(self, node_id):
        '''获取节点的时间窗宽度'''
        open_time, close_time = self.world.time_windows[node_id]
        return close_time - open_time
    
    def find_replacement(self, violated_node, used_alternatives):
        '''
        找到时间窗更宽的备选景点
        
        参数:
        - violated_node: 违规节点
        - used_alternatives: 已使用的备选节点集合
        
        返回:
        - 备选节点信息 或 None
        '''
        original_width = self.get_window_width(violated_node)
        
        # 按时间窗宽度排序（从宽到窄）
        candidates = []
        for alt_info in self.alternative_nodes_info:
            alt_node = alt_info['node_id']
            if alt_node in used_alternatives:
                continue
            
            alt_width = alt_info['time_window'][1] - alt_info['time_window'][0]
            if alt_width > original_width:
                candidates.append((alt_width, alt_info))
        
        if not candidates:
            return None
        
        # 返回时间窗最宽的
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]
    
    def create_extended_world(self, original_visited, replacement_info):
        '''
        创建扩展的问题空间（包含备选节点）
        
        参数:
        - original_visited: 原始访问顺序
        - replacement_info: 备选节点信息
        
        返回:
        - 新的TimeWindowWorld对象
        '''
        # 扩展时间窗和服务时间
        new_time_windows = list(self.world.time_windows)
        new_service_times = list(self.world.service_times)
        
        # 添加备选节点信息
        alt_node = replacement_info['node_id']
        while len(new_time_windows) <= alt_node:
            new_time_windows.append((0, 0))
            new_service_times.append(0)
        
        new_time_windows[alt_node] = replacement_info['time_window']
        new_service_times[alt_node] = replacement_info['service_time']
        
        # 扩展通勤时间矩阵
        n = len(new_time_windows)
        new_travel_times = np.zeros((n, n))
        
        # 复制原有数据
        old_n = self.world.n_nodes
        new_travel_times[:old_n, :old_n] = self.world.travel_times
        
        # 为备选节点设置通勤时间（使用平均值或默认值）
        if alt_node >= old_n:
            avg_time = 25  # 默认通勤时间
            for i in range(n):
                if i != alt_node:
                    new_travel_times[i][alt_node] = avg_time
                    new_travel_times[alt_node][i] = avg_time
        
        return TimeWindowWorld(
            new_travel_times,
            new_time_windows,
            new_service_times,
            self.world.start_time,
            self.world.init_pheromone
        )
    
    def local_aco_optimize(self, start_node, remaining_nodes, current_time, extended_world):
        '''
        局部ACO优化
        
        参数:
        - start_node: 起始节点（违规前的最后一个节点）
        - remaining_nodes: 剩余待访问节点列表
        - current_time: 当前时间
        - extended_world: 扩展的问题空间
        
        返回:
        - 优化后的节点顺序 或 None
        '''
        if not remaining_nodes:
            return []
        
        # 创建局部蚁群系统（小规模：10只蚂蚁，20轮迭代）
        class LocalAnt(Ant):
            def __init__(self, world, start_node, remaining_nodes, start_time, alpha, beta):
                # 先设置局部属性，再调用父类初始化
                self.local_start = start_node
                self.local_remaining = set(remaining_nodes)
                self.local_start_time = start_time
                # 调用父类初始化（会调用reset）
                super().__init__(world, alpha, beta)
            
            def reset(self):
                self.visited = [self.local_start]
                self.unvisited = self.local_remaining.copy()
                self.path = []
                self.current_time = self.local_start_time
                self.current_node = self.local_start
                self.total_cost = 0
        
        # 创建局部蚂蚁
        local_ants = [LocalAnt(extended_world, start_node, remaining_nodes, current_time, 1, 3) 
                      for _ in range(10)]
        
        best_cost = float('inf')
        best_visited = None
        
        # 运行20轮迭代
        for iteration in range(20):
            for ant in local_ants:
                cost = ant.create_path()
                if cost < best_cost:
                    best_cost = cost
                    best_visited = ant.visited[1:]  # 去掉起始节点
                
                # 更新信息素
                ant.update_pheromone(1.0)
            
            # 信息素挥发
            for edge in extended_world.edges:
                edge.pheromone *= 0.8
        
        # 如果最佳成本包含惩罚，说明局部优化也无解
        if best_cost >= 9999:
            return None
        
        return best_visited
    
    def repair_solution(self, best_visited, verbose=True):
        '''
        修复违规解
        
        参数:
        - best_visited: ACO找到的最佳访问顺序
        - verbose: 是否打印日志
        
        返回:
        - 修复后的访问顺序
        '''
        if verbose:
            print("\n" + "="*80)
            print("开始修复策略")
            print("="*80)
        
        current_visited = best_visited.copy()
        used_alternatives = set()
        iteration = 0
        
        # 维护当前的扩展world（初始为原始world）
        current_world = self.world
        
        while iteration < self.max_repair_iterations:
            # 检测违规（使用当前的world）
            violations = self.detect_violations(current_visited, current_world)
            
            if not violations:
                if verbose:
                    print(f"\n✅ 修复成功！经过{iteration}次修复，所有节点满足时间窗约束")
                return current_visited
            
            # 获取第一个违规节点
            violated_node, violated_position, arrival_time, close_time = violations[0]
            
            if verbose:
                print(f"\n🔧 修复轮次 {iteration + 1}/{self.max_repair_iterations}")
                print(f"   检测到违规: 节点{violated_node}在位置{violated_position}")
                print(f"   到达时间: {arrival_time//60:02d}:{arrival_time%60:02d}, "
                      f"关闭时间: {close_time//60:02d}:{close_time%60:02d}")
            
            # 尝试找到替换节点
            replacement = self.find_replacement(violated_node, used_alternatives)
            
            if replacement is None:
                if verbose:
                    print(f"   ❌ 无可用备选节点，删除节点{violated_node}")
                current_visited = [n for n in current_visited if n != violated_node]
                iteration += 1
                continue
            
            alt_node = replacement['node_id']
            if verbose:
                print(f"   ✓ 找到备选节点{alt_node}, 时间窗: "
                      f"{replacement['time_window'][0]//60:02d}:{replacement['time_window'][0]%60:02d} - "
                      f"{replacement['time_window'][1]//60:02d}:{replacement['time_window'][1]%60:02d}")
            
            # 创建扩展的问题空间
            extended_world = self.create_extended_world(current_visited, replacement)
            
            # 计算违规前的状态（使用当前world）
            start_node = current_visited[violated_position - 1]
            current_time = current_world.start_time
            for i in range(1, violated_position):
                from_node = current_visited[i - 1]
                to_node = current_visited[i]
                travel_time = current_world.travel_times[from_node][to_node]
                arrival_time = current_time + travel_time
                open_time, close_time = current_world.time_windows[to_node]
                service_start = max(arrival_time, open_time)
                current_time = service_start + current_world.service_times[to_node]
            
            # 准备剩余节点（替换违规节点 + 后续节点）
            remaining_nodes = [alt_node] + current_visited[violated_position + 1:]
            
            if verbose:
                print(f"   运行局部ACO: 起点={start_node}, 剩余节点={remaining_nodes}")
            
            # 运行局部ACO
            optimized_remaining = self.local_aco_optimize(
                start_node, remaining_nodes, current_time, extended_world
            )
            
            if optimized_remaining is None:
                if verbose:
                    print(f"   ❌ 局部ACO无解，删除节点{violated_node}")
                current_visited = [n for n in current_visited if n != violated_node]
            else:
                # 更新路径和world
                current_visited = current_visited[:violated_position] + optimized_remaining
                current_world = extended_world  # 更新为扩展的world
                used_alternatives.add(alt_node)
                if verbose:
                    print(f"   ✅ 局部ACO成功，新路径: {current_visited}")
            
            iteration += 1
        
        # 达到最大修复次数
        if verbose:
            violations = self.detect_violations(current_visited, current_world)
            if violations:
                print(f"\n⚠️  达到最大修复次数({self.max_repair_iterations})，仍有{len(violations)}个违规节点")
                print(f"   返回原路径: {best_visited}")
                return best_visited
        
        return current_visited
