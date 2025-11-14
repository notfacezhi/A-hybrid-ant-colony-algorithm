import numpy as np
import math
import random


class Ant:
    """
    蚂蚁类 - 用于求解带时间窗口的车辆路径问题(VRPTW)
    使用蚁群算法(ACO)构建可行路径
    """

    def __init__(self, data, capacity, q0):
        """
        初始化蚂蚁对象
        
        参数:
            data: 客户数据列表
            capacity: 车辆容量限制
            q0: 贪婪选择概率(0-1之间),越大越倾向于选择最优节点
        """
        # ========== 基础数据 ==========
        self.data = data  # 原始数据
        self.cordination = []  # 客户坐标列表
        self.distance_matrix = {}  # 距离矩阵 {(i,j): distance}
        self.intensity = {}  # 启发式信息 {(i,j): 1/distance}
        self.time_window = {}  # 时间窗口宽度 {node: width}

        # ========== 路径构建相关 ==========
        self.current_point = 1  # 当前所在节点(1为仓库)
        self.next_node = 1  # 下一个要访问的节点
        self.travel = ()  # 当前移动 (起点, 终点)
        self.visited_list = [1]  # 已访问节点列表
        self.candidate_list = []  # 候选节点列表(未访问的)

        # ========== 约束条件 ==========
        self.capacity = capacity  # 当前剩余容量
        self.minimum_capacity = 0  # 最小需求量
        self.capcities = {}  # 候选节点的需求量字典
        self.service_time = 0.00  # 当前累计服务时间
        self.serv_list = []  # 服务时间记录列表

        # ========== 信息素相关 ==========
        self.pheromon = {}  # 信息素矩阵 {(i,j): pheromone}
        self.pheromon_numbers = {}  # 信息素增量 {(i,j): delta}
        self.rho = 0.6  # 信息素挥发率(动态变化)
        self.Q = 1  # 信息素强度系数

        # ========== 算法参数 ==========
        self.q0 = q0  # 贪婪选择概率
        self.alpha = 1  # 信息素重要程度
        self.beta = 4  # 启发式信息重要程度(距离)
        self.gama = 3  # 时间窗口重要程度

        # ========== 概率计算 ==========
        self.probability_q0 = {}  # 节点吸引力(用于贪婪选择)
        self.probability_q = {}  # 归一化前的概率
        self.probability_q_norm = {}  # 归一化后的概率(用于轮盘赌)

        # ========== 结果统计 ==========
        self.travel_distance = 0  # 总行驶距离

    def customer_cord(self):
        """
        提取所有客户的坐标
        从数据的第2、3列提取x、y坐标
        """
        for i in range(len(self.data)):
            cords = [float(self.data[i][1]), float(self.data[i][2])]
            self.cordination.append(cords)
        return self.cordination

    def euclidean_distance(self):
        """
        计算所有节点间的欧氏距离和启发式信息
        
        distance_matrix: 节点i到节点j的欧氏距离
        intensity: 启发式信息 = 1/distance (距离越近，吸引力越大)
        """
        for i in range(len(self.cordination)):
            for j in range(len(self.cordination)):
                # 计算欧氏距离
                distance = math.sqrt(
                    ((self.cordination[i][0] - self.cordination[j][0]) ** 2) +
                    ((self.cordination[i][1] - self.cordination[j][1]) ** 2)
                )
                self.distance_matrix[i + 1, j + 1] = distance

                # 计算启发式信息(距离的倒数)
                if distance == 0:
                    # 同一节点，设置为极小值
                    self.intensity[i + 1, j + 1] = -99999999
                else:
                    self.intensity[i + 1, j + 1] = 1 / distance

        return self.distance_matrix, self.intensity

    def width_window(self):
        """
        计算每个节点的时间窗口宽度
        时间窗口宽度 = 最晚到达时间 - 最早到达时间
        窗口越窄，越需要优先访问
        """
        for i in self.data:
            self.time_window[i[0]] = float(i[5]) - float(i[4])
        return self.time_window

    def path_pheromon(self):
        """
        初始化所有路径的信息素为1
        信息素表示路径的历史优劣程度
        """
        for node_i in self.data:
            for node_j in self.data:
                self.pheromon[int(node_i[0]), int(node_j[0])] = 1
        return self.pheromon

    def number_pheromon(self):
        """
        初始化信息素增量为0
        每次完成一条路径后会更新增量
        """
        for node_i in self.data:
            for node_j in self.data:
                self.pheromon_numbers[int(node_i[0]), int(node_j[0])] = 0
        return self.pheromon_numbers

    def make_candidate_list(self):
        """
        生成候选节点列表
        包含所有未访问的客户节点
        """
        self.candidate_list = []
        for node in self.data:
            if int(node[0]) not in self.visited_list:
                self.candidate_list.append(int(node[0]))
        return self.candidate_list

    def choose_next_node(self):
        """
        选择下一个要访问的节点 - 算法核心方法
        
        策略:
        1. 无候选节点 -> 返回仓库
        2. 只有1个候选 -> 检查约束后选择
        3. 多个候选 -> 基于信息素、距离、时间窗口计算概率选择
        
        选择公式:
        吸引力 = (信息素^α) × (1/距离^β) × (1/时间窗口宽度^γ)
        
        选择方式:
        - q <= q0: 贪婪选择(选吸引力最大的)
        - q > q0: 轮盘赌选择(按概率随机选)
        """
        # 情况1: 没有候选节点，返回仓库
        if len(self.candidate_list) == 0:
            self.next_node = 1
            return self.next_node
        # 情况2: 只有1个候选节点
        elif len(self.candidate_list) == 1:
            self.next_node = self.candidate_list[0]
            # 检查容量约束
            if float(self.data[int(self.next_node)][3]) < self.capacity:
                return self.next_node
            else:
                # 容量不足，返回仓库
                self.next_node = 1
                return self.next_node

        # 情况3: 多个候选节点，需要计算概率选择
        else:
            next_node = 0
            self.probability_q0 = {}
            self.probability_q = {}
            self.probability_q_norm = {}

            # 计算每个候选节点的吸引力(用于贪婪选择)
            # 公式: τ^α × η^β × (1/时间窗口)^γ
            for node in self.candidate_list:
                self.probability_q0[self.current_point, node] = (
                        (self.pheromon[self.current_point, node] ** self.alpha) *
                        (self.intensity[self.current_point, node] ** self.beta) *
                        ((1 / (self.time_window[str(self.current_point)])) ** self.gama)
                )

            # 归一化吸引力(除以最大值)
            for node in self.candidate_list:
                self.probability_q[self.current_point, node] = (
                        self.probability_q0[self.current_point, node] /
                        max(self.probability_q0.values())
                )

            # Softmax归一化: 将概率转换为和为1的概率分布
            def softmax_normalize(dictionary):
                values = np.array(list(dictionary.values()), dtype=np.float64)
                exp_values = np.exp(values - np.max(values))  # 防止数值溢出
                normalized_values = exp_values / np.sum(exp_values)
                normalized_dict = dict(zip(dictionary.keys(), normalized_values))
                return normalized_dict

            self.probability_q_norm = softmax_normalize(self.probability_q)
            # 提取候选节点的需求量
            self.capcities = {}
            for node in self.candidate_list:
                self.capcities[node] = float(self.data[node - 1][3])

            # 生成随机数，决定选择策略
            q = random.random()
            i = 0

            # 策略1: 贪婪选择(q <= q0时，选择吸引力最大的节点)
            if q <= self.q0:
                # 按吸引力从大到小排序
                sorted_value_q0 = sorted(self.probability_q0.values(), reverse=True)
                for key, value in self.probability_q0.items():
                    if value == sorted_value_q0[i]:
                        # 检查容量和时间窗口约束
                        if (float(self.data[key[1] - 1][3]) <= self.capacity and
                                self.service_time + float(self.data[key[1] - 1][6]) <= float(self.data[0][5])):
                            next_node = key[1]
                            self.next_node = next_node
                            return self.next_node
                        else:
                            # 最优节点不满足约束，寻找其他可行节点
                            flag = 0
                            for key, value in self.capcities.items():
                                flag += 1
                                if (value <= self.capacity and
                                        self.service_time + float(self.data[key - 1][6]) <= float(self.data[0][5])):
                                    self.next_node = key
                                elif flag == len(self.capcities) - 1:
                                    self.next_node = None
                                else:
                                    pass
                            return self.next_node
            # 策略2: 轮盘赌选择(q > q0时，按概率随机选择)
            else:
                def roulette_wheel_selection(values, probabilities):
                    """轮盘赌选择: 按概率权重随机选择"""
                    selected_key = random.choices(list(values), weights=list(probabilities), k=1)[0]
                    return selected_key

                j = 0
                # 尝试选择满足约束的节点
                for item in self.probability_q_norm:
                    selected_key = roulette_wheel_selection(
                        self.probability_q_norm.keys(),
                        self.probability_q_norm.values()
                    )
                    # 检查容量和时间窗口约束
                    if (float(self.data[selected_key[1] - 1][3]) <= self.capacity and
                            self.service_time + float(self.data[selected_key[1] - 1][6]) <= float(self.data[0][5])):
                        next_node = selected_key[1]
                        self.next_node = next_node
                        return self.next_node
                    else:
                        continue
                # 没有可行节点，返回None(后续会返回仓库)
                self.next_node = None
                return self.next_node

    def cal_minimum_capacity(self):
        """
        计算所有客户中的最小需求量
        用于判断是否还能继续访问客户
        """
        demands = []
        for node in self.data[1:]:
            demands.append(float(node[3]))
            self.minimum_capacity = min(demands)
        return self.minimum_capacity

    def move(self):
        """
        执行移动操作，更新蚂蚁状态
        
        更新内容:
        - 访问列表
        - 剩余容量
        - 服务时间
        - 总距离
        - 当前位置
        """
        if self.next_node == None:
            # 没有可访问节点，返回仓库
            self.next_node = 1
            self.travel = (self.current_point, 1)
        else:
            # 标记节点为已访问
            self.visited_list.append(self.next_node)
            self.travel = (self.current_point, self.next_node)

            # 更新服务时间
            if self.travel[0] == 1:
                # 从仓库出发: 时间 = 时间窗口开始 + 服务时间
                self.service_time = (self.service_time +
                                     float(self.data[self.travel[1] - 1][4]) +
                                     float(self.data[self.travel[1] - 1][6]))
            else:
                # 从客户到客户: 时间 += 服务时间
                self.service_time = self.service_time + float(self.data[self.travel[1] - 1][6])

            self.serv_list.append(self.service_time)

            # 减少剩余容量
            self.capacity = self.capacity - float(self.data[self.next_node - 1][3])

            # 更新当前位置
            self.current_point = self.next_node

        # 累加总距离
        self.travel_distance += self.distance_matrix[self.travel]
        return self.travel

    def update_rho(self):
        """
        动态更新信息素挥发率
        每完成一条路径后，挥发率衰减为原来的90%
        这样后期信息素更稳定，算法更收敛
        """
        self.rho = 0.9 * self.rho
        return self.rho

    def update_pheromon_number(self, ants_travels):
        """
        更新信息素增量
        
        参数:
            ants_travels: 当前路径的所有移动序列
        
        增量公式: Δτ = Q / 路径长度
        路径越短，增量越大
        """
        for travel in ants_travels:
            self.pheromon_numbers[travel] = (
                    self.pheromon_numbers[travel] +
                    (self.Q / len(ants_travels))
            )
        return self.pheromon_numbers

    def update_pheromon(self, ants_travels):
        """
        更新路径信息素
        
        参数:
            ants_travels: 当前路径的所有移动序列
        
        更新公式: τ(t+1) = τ(t) + (1-ρ)×τ(t) + ρ×Δτ
        - (1-ρ)×τ(t): 信息素挥发
        - ρ×Δτ: 信息素增强
        """
        for travel in ants_travels:
            self.pheromon[travel] = (
                    self.pheromon[travel] +
                    ((1 - self.rho) * self.pheromon[travel]) +
                    (self.rho * self.pheromon_numbers[travel])
            )
        return self.pheromon
