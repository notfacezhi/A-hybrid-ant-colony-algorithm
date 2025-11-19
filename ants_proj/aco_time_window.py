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


# 这个世界是关键是 需要保存的点
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
    
    def __init__(self, travel_times, time_windows, service_times, start_time=480, init_pheromone=1.0, node_ids=None):
        '''
        参数:
        - travel_times: 通勤时间矩阵 (分钟)
        - time_windows: 时间窗 [(open, close), ...]
        - service_times: 游玩时间列表 (分钟)
        - start_time: 出发时间 (分钟, 默认480=8:00)
        - init_pheromone: 初始信息素 (默认1.0)
        - node_ids: 节点ID列表 (默认为索引 [0,1,2,...])
        '''
        self.n_nodes = len(travel_times)
        self.travel_times = np.array(travel_times)
        self.time_windows = time_windows
        self.service_times = service_times
        self.start_time = start_time
        self.init_pheromone = init_pheromone
        
        # 节点ID映射
        if node_ids is None:
            self.node_ids = list(range(self.n_nodes))
        else:
            self.node_ids = node_ids
        
        self.id2index = {node_id: idx for idx, node_id in enumerate(self.node_ids)}
        self.index2id = {idx: node_id for idx, node_id in enumerate(self.node_ids)}
        
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
                    # 为边添加ID信息
                    edge.from_id = self.index2id[i]
                    edge.to_id = self.index2id[j]
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
    
    def export_pheromones(self):
        '''
        导出所有边的信息素
        返回: [{'from_id': X, 'to_id': Y, 'pheromone': v}, ...]
        '''
        records = []
        for edge in self.edges:
            records.append({
                'from_id': edge.from_id,
                'to_id': edge.to_id,
                'pheromone': edge.pheromone
            })
        return records
    
    def import_pheromones(self, records, tau_min=None, tau_max=None, scale=1.0):
        '''
        导入信息素记录
        
        参数:
        - records: [{'from_id': X, 'to_id': Y, 'pheromone': v}, ...]
        - tau_min: 信息素下限 (可选)
        - tau_max: 信息素上限 (可选)
        - scale: 缩放因子 (默认1.0，可用于温和重置)
        '''
        # 构建快速查找字典
        pheromone_dict = {}
        for record in records:
            key = (record['from_id'], record['to_id'])
            pheromone_dict[key] = record['pheromone']
        
        # 更新边的信息素
        for edge in self.edges:
            key = (edge.from_id, edge.to_id)
            if key in pheromone_dict:
                pheromone = pheromone_dict[key] * scale
                
                # 应用边界
                if tau_min is not None:
                    pheromone = max(pheromone, tau_min)
                if tau_max is not None:
                    pheromone = min(pheromone, tau_max)
                
                edge.pheromone = pheromone
    
    def get_pheromone_stats(self):
        '''
        获取信息素统计信息
        返回: {'min': x, 'max': y, 'mean': z, 'median': w}
        '''
        pheromones = [edge.pheromone for edge in self.edges]
        return {
            'min': min(pheromones),
            'max': max(pheromones),
            'mean': np.mean(pheromones),
            'median': np.median(pheromones)
        }


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
            
            # 检查时间窗 并返回服务开始时间
            service_start_time, violated, penalty = self._check_time_window(edge.end, arrival_time)
            
            # 更新成本 成本函数是让到达时间最少的最好
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
        
        # 创建蚁群 所有蚁群共用一个world
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
    
    def export_best(self):
        '''
        导出最佳解摘要
        返回: {'best_cost': x, 'best_visited_ids': [...], 'best_path': [...], 'cost_history': [...]}
        '''
        if self.best_path is None:
            return None
        
        # 转换访问顺序为ID
        best_visited_ids = [self.world.index2id[idx] for idx in self.best_visited]
        
        # 转换路径为ID
        best_path_records = []
        for edge in self.best_path:
            best_path_records.append({
                'from_id': edge.from_id,
                'to_id': edge.to_id,
                'travel_time': edge.travel_time
            })
        
        return {
            'best_cost': self.best_cost,
            'best_visited_ids': best_visited_ids,
            'best_path': best_path_records,
            'cost_history': self.cost_history.copy()
        }
    
    def import_best(self, summary):
        '''
        导入最佳解摘要 (可选，用于展示或warm-start)
        
        参数:
        - summary: export_best()返回的字典
        '''
        if summary is None:
            return
        
        self.best_cost = summary['best_cost']
        self.cost_history = summary['cost_history'].copy()
        
        # 注意: best_visited 和 best_path 需要根据当前 world 的节点集重建
        # 这里仅保存成本和历史，不重建路径
    
    def continue_optimize(self, n_more_iterations, verbose=True):
        '''
        继续优化 (不重置信息素和最佳解)
        
        参数:
        - n_more_iterations: 额外迭代次数
        - verbose: 是否打印日志
        '''
        if verbose:
            print('| iter |         min        |         max        |        best        |')
            print('-' * 80)
        
        start_iteration = len(self.cost_history) + 1
        
        for iteration in range(start_iteration, start_iteration + n_more_iterations):
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
            print(f'继续优化完成! 最佳成本: {self.best_cost:.2f}')
            print(f'最佳路径: {self.best_visited}')
