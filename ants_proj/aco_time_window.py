'''
带时间窗约束的蚁群算法 (ACO with Time Windows)
基于ant_travel.py框架实现软时间窗约束的旅游路线优化

核心设计:
1. 软时间窗: 允许违反时间窗但加大惩罚(+9999)
2. 早到等待: 不增加成本，但占用时间
3. 启发函数: 综合考虑距离和时间窗紧迫度
4. 信息素: 考虑时间窗紧迫性
'''

import random
import numpy as np


class Edge:
    '''边: 连接起点和终点的路径'''
    
    def __init__(self, start, end, travel_time, pheromone=1.0):
        '''
        参数:
        - start: 起点节点索引
        - end: 终点节点索引
        - travel_time: 通勤时间(分钟)
        - pheromone: 信息素浓度
        '''
        self.start = start
        self.end = end
        self.travel_time = travel_time  # 通勤时间
        self.pheromone = pheromone


class TimeWindowWorld:
    '''
    带时间窗约束的问题空间
    
    属性:
    - n_nodes: 节点数量(包含起点)
    - travel_times: 通勤时间矩阵 [n_nodes x n_nodes]
    - time_windows: 时间窗列表 [(open, close), ...]
    - service_times: 游玩时间列表
    - start_time: 早上出发时间(分钟)
    - edges: 所有边的列表
    '''
    
    def __init__(self, travel_times, time_windows, service_times, start_time=480, init_pheromone=1.0):
        '''
        参数:
        - travel_times: 通勤时间矩阵 (分钟)
        - time_windows: 时间窗 [(open, close), ...]
        - service_times: 游玩时间列表 (分钟)
        - start_time: 出发时间 (分钟, 默认480=8:00)
        - init_pheromone: 初始信息素 (默认1.0)
        '''
        self.n_nodes = len(travel_times)
        self.travel_times = np.array(travel_times)
        self.time_windows = time_windows
        self.service_times = service_times
        self.start_time = start_time
        self.init_pheromone = init_pheromone
        
        # 创建所有边
        self.edges = []
        self._create_edges()
    
    def _create_edges(self):
        '''创建完全图的所有边'''
        for i in range(self.n_nodes):
            for j in range(self.n_nodes):
                if i != j:
                    travel_time = self.travel_times[i][j]
                    edge = Edge(i, j, travel_time, self.init_pheromone)
                    self.edges.append(edge)
    
    def get_edge(self, start, end):
        '''获取指定起点和终点的边'''
        for edge in self.edges:
            if edge.start == start and edge.end == end:
                return edge
        return None
    
    def reset_pheromone(self):
        '''重置所有边的信息素'''
        for edge in self.edges:
            edge.pheromone = self.init_pheromone


class Ant:
    '''
    单只蚂蚁: 负责构建一条完整路径
    
    属性:
    - world: TimeWindowWorld对象
    - alpha: 信息素权重
    - beta: 启发函数权重
    - visited: 已访问节点列表
    - unvisited: 未访问节点集合
    - path: 路径(边的列表)
    - current_time: 当前时间
    - current_node: 当前节点
    '''
    
    def __init__(self, world, alpha=1, beta=3):
        '''
        参数:
        - world: TimeWindowWorld对象
        - alpha: 信息素权重 (默认1)
        - beta: 启发函数权重 (默认3)
        '''
        self.world = world
        self.alpha = alpha
        self.beta = beta
        self.reset()
    
    def reset(self):
        '''重置蚂蚁状态'''
        self.visited = [0]  # 从节点0开始
        self.unvisited = set(range(1, self.world.n_nodes))  # 其他节点未访问
        self.path = []  # 路径(边的列表)
        self.current_time = self.world.start_time  # 当前时间
        self.current_node = 0  # 当前节点
        self.total_cost = 0  # 总成本
    
    def _get_candidates(self):
        '''获取候选边列表'''
        candidates = []
        for next_node in self.unvisited:
            edge = self.world.get_edge(self.current_node, next_node)
            if edge:
                candidates.append(edge)
        return candidates
    
    def _calculate_urgency(self, node, arrival_time):
        '''
        计算时间窗紧迫度
        紧迫度 = 1 / (关闭时间 - 当前到达时间)
        距离关闭时间越近，紧迫度越高
        '''
        open_time, close_time = self.world.time_windows[node]
        
        # 如果已经超过关闭时间，紧迫度设为很小的值(表示不紧迫，因为已经违反)
        if arrival_time > close_time:
            return 0.001
        
        # 计算距离关闭时间的剩余时间
        time_to_close = close_time - arrival_time
        
        # 避免除零
        if time_to_close <= 0:
            return 0.001
        
        # 紧迫度与剩余时间成反比
        urgency = 1.0 / time_to_close
        return urgency
    
    def _heuristic(self, edge):
        '''
        启发函数: 综合考虑距离和时间窗紧迫度
        返回值越大，该边越有吸引力
        '''
        # 1. 距离启发: 距离越短越好
        distance_heuristic = 1.0 / (edge.travel_time + 1)  # 避免除零
        
        # 2. 时间窗紧迫度: 计算到达目标节点的时间
        arrival_time = self.current_time + edge.travel_time
        urgency = self._calculate_urgency(edge.end, arrival_time)
        
        # 综合启发值: 距离 + 紧迫度
        heuristic_value = distance_heuristic + urgency
        
        return heuristic_value
    
    def _choose_next_edge(self, candidates):
        '''
        选择下一条边: 基于信息素和启发函数的轮盘赌选择
        '''
        if not candidates:
            return None
        
        # 计算每条边的概率
        probabilities = []
        for edge in candidates:
            pheromone = edge.pheromone ** self.alpha
            heuristic = self._heuristic(edge) ** self.beta
            prob = pheromone * heuristic
            probabilities.append(prob)
        
        # 归一化概率
        probabilities = np.array(probabilities)
        total = probabilities.sum()
        
        if total == 0:
            # 如果所有概率都是0，随机选择
            return random.choice(candidates)
        
        probabilities = probabilities / total
        
        # 轮盘赌选择
        rand = random.random()
        cumulative = 0
        for i, prob in enumerate(probabilities):
            cumulative += prob
            if rand < cumulative:
                return candidates[i]
        
        return candidates[-1]
    
    def _calculate_arrival_time(self, edge):
        '''计算到达下一个节点的时间'''
        return self.current_time + edge.travel_time
    
    def _check_time_window(self, node, arrival_time):
        '''
        检查时间窗约束
        返回: (实际开始服务时间, 是否违反时间窗, 惩罚值)
        '''
        open_time, close_time = self.world.time_windows[node]
        
        # 早到: 等待到开门时间
        if arrival_time < open_time:
            return open_time, False, 0
        
        # 晚到: 违反时间窗，加大惩罚
        if arrival_time > close_time:
            return arrival_time, True, 9999
        
        # 正常到达
        return arrival_time, False, 0
    
    def create_path(self):
        '''
        构建完整路径
        返回: 总成本(包含惩罚)
        '''
        self.reset()
        
        while self.unvisited:
            # 获取候选边
            candidates = self._get_candidates()
            
            if not candidates:
                # 没有候选边，路径构建失败
                break
            
            # 选择下一条边
            edge = self._choose_next_edge(candidates)
            
            # 计算到达时间
            arrival_time = self._calculate_arrival_time(edge)
            
            # 检查时间窗
            service_start_time, violated, penalty = self._check_time_window(edge.end, arrival_time)
            
            # 更新成本
            self.total_cost += edge.travel_time + penalty
            
            # 更新状态
            self.path.append(edge)
            self.visited.append(edge.end)
            self.unvisited.remove(edge.end)
            self.current_node = edge.end
            
            # 更新当前时间: 服务开始时间 + 游玩时间
            self.current_time = service_start_time + self.world.service_times[edge.end]
        
        return self.total_cost
    
    def update_pheromone(self, deposit_amount):
        '''在路径上更新信息素'''
        for edge in self.path:
            edge.pheromone += deposit_amount


class AntColonySystem:
    '''
    蚁群优化系统
    
    属性:
    - world: TimeWindowWorld对象
    - n_ants: 蚂蚁数量
    - n_iterations: 迭代次数
    - alpha: 信息素权重
    - beta: 启发函数权重
    - evaporation_rate: 信息素挥发率
    - pheromone_deposit: 信息素沉积量
    - elite_ratio: 精英蚂蚁比例
    - elite_deposit: 精英蚂蚁额外信息素
    '''
    
    def __init__(self, world, n_ants=20, n_iterations=50, alpha=1, beta=3,
                 evaporation_rate=0.2, pheromone_deposit=1.0, 
                 elite_ratio=0.3, elite_deposit=1.0):
        '''
        参数:
        - world: TimeWindowWorld对象
        - n_ants: 蚂蚁数量 (默认20)
        - n_iterations: 迭代次数 (默认50)
        - alpha: 信息素权重 (默认1)
        - beta: 启发函数权重 (默认3)
        - evaporation_rate: 信息素挥发率 (默认0.2)
        - pheromone_deposit: 信息素沉积量 (默认1.0)
        - elite_ratio: 精英蚂蚁比例 (默认0.3)
        - elite_deposit: 精英蚂蚁额外信息素 (默认1.0)
        '''
        self.world = world
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha
        self.beta = beta
        self.evaporation_rate = evaporation_rate
        self.pheromone_deposit = pheromone_deposit
        self.elite_ratio = elite_ratio
        self.elite_deposit = elite_deposit
        
        # 创建蚁群
        self.ants = [Ant(world, alpha, beta) for _ in range(n_ants)]
        
        # 最佳解
        self.best_cost = float('inf')
        self.best_path = None
        self.best_visited = None
        
        # 历史记录
        self.cost_history = []
    
    def optimize(self, verbose=True):
        '''
        执行优化过程
        
        参数:
        - verbose: 是否打印日志
        '''
        if verbose:
            print('| iter |         min        |         max        |        best        |')
            print('-' * 80)
        
        for iteration in range(1, self.n_iterations + 1):
            # 所有蚂蚁构建路径
            ant_results = []
            for ant in self.ants:
                cost = ant.create_path()
                ant_results.append((cost, ant))
            
            # 按成本排序
            ant_results.sort(key=lambda x: x[0])
            
            # 更新全局最佳解
            min_cost = ant_results[0][0]
            max_cost = ant_results[-1][0]
            
            if min_cost < self.best_cost:
                self.best_cost = min_cost
                self.best_path = ant_results[0][1].path.copy()
                self.best_visited = ant_results[0][1].visited.copy()
            
            # 所有蚂蚁更新信息素
            for cost, ant in ant_results:
                ant.update_pheromone(self.pheromone_deposit)
            
            # 精英蚂蚁额外更新信息素
            n_elite = int(self.elite_ratio * self.n_ants)
            for i in range(n_elite):
                ant_results[i][1].update_pheromone(self.elite_deposit)
            
            # 信息素挥发
            for edge in self.world.edges:
                edge.pheromone *= (1 - self.evaporation_rate)
            
            # 记录历史
            self.cost_history.append(self.best_cost)
            
            # 打印日志
            if verbose:
                print('|%6d|%20.2f|%20.2f|%20.2f|' % (iteration, min_cost, max_cost, self.best_cost))
        
        if verbose:
            print('-' * 80)
            print(f'优化完成! 最佳成本: {self.best_cost:.2f}')
            print(f'最佳路径: {self.best_visited}')
    
    def get_best_solution(self):
        '''
        获取最佳解
        返回: (成本, 访问顺序, 路径详情)
        '''
        if self.best_path is None:
            return None
        
        # 构建路径详情
        path_details = []
        current_time = self.world.start_time
        
        for i, edge in enumerate(self.best_path):
            arrival_time = current_time + edge.travel_time
            open_time, close_time = self.world.time_windows[edge.end]
            
            # 检查时间窗
            if arrival_time < open_time:
                service_start = open_time
                status = '等待'
            elif arrival_time > close_time:
                service_start = arrival_time
                status = '违反时间窗'
            else:
                service_start = arrival_time
                status = '正常'
            
            service_end = service_start + self.world.service_times[edge.end]
            
            path_details.append({
                'step': i + 1,
                'from': edge.start,
                'to': edge.end,
                'travel_time': edge.travel_time,
                'arrival_time': arrival_time,
                'service_start': service_start,
                'service_end': service_end,
                'status': status
            })
            
            current_time = service_end
        
        return {
            'cost': self.best_cost,
            'visited': self.best_visited,
            'path_details': path_details
        }


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
