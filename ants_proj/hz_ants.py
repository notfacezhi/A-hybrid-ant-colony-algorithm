import matplotlib.pyplot as plt
import numpy as np
import math
import random
from ants import Ant

# ========== 数据加载部分 ==========
# 读取车辆路径问题数据集
# 数据格式: [节点编号, x坐标, y坐标, 需求量, 时间窗口开始, 时间窗口结束, 服务时间]
data = []
with open('../dataset/c101C6.txt', 'r') as datafile:
    for line in datafile:
        line = line.strip().split('\n')
        data.append(line)

# 转换为numpy数组并去掉第一行(表头)
numpy_data = np.array(data)
numpy_data = numpy_data[1:]

# 将每行数据按空格分割成列表
splited_data = [line[0].split() for line in numpy_data]

# ========== 蚁群算法主流程 ==========
# 存储每条路径的移动序列: {路径编号: [(起点,终点), ...]}
ants_travels = {}
# 存储每条路径访问的节点序列: {路径编号: [节点1, 节点2, ...]}
ants_route = {}
# 当前路径的移动序列
travels = []
# 当前路径访问的节点序列，从仓库(节点1)开始
path = [1]

# 创建蚂蚁对象
# 参数: 数据集, 车辆容量=200, q0=0.9(贪婪选择概率)
colony = Ant(splited_data, 200.00, 0.9)

# 初始化阶段
colony.customer_cord()        # 提取所有客户的坐标
colony.euclidean_distance()   # 计算节点间的欧氏距离矩阵和启发式信息(1/距离)
colony.width_window()         # 计算每个节点的时间窗口宽度
colony.path_pheromon()        # 初始化所有路径的信息素为1
colony.number_pheromon()      # 初始化信息素增量为0

# 路径编号计数器
i = 0
# 主循环: 构建完整的路径解决方案
while True:
    # 生成候选节点列表(未访问的客户)
    colony.make_candidate_list()
    
    # 根据信息素、距离、时间窗口选择下一个要访问的节点
    colony.choose_next_node()
    
    # 计算最小需求量(用于约束检查)
    colony.cal_minimum_capacity()
    
    # 移动到选中的节点，更新状态(容量、时间、距离)
    colony.move()
    
    # 记录访问的节点
    path.append(colony.next_node)
    
    # 记录移动(边)
    travel = colony.travel
    travels.append(travel)
    
    # 判断是否返回仓库
    if travel[1] == 1:
        # 如果是(1,1)，说明没有客户可访问了，算法结束
        if travel == (1, 1):
            break
        else:
            # 完成一条路径，保存结果
            ants_travels[i] = travels
            
            # 更新信息素
            colony.update_rho()                              # 动态衰减信息素挥发率
            colony.update_pheromon_number(ants_travels[i])  # 更新信息素增量
            colony.update_pheromon(ants_travels[i])         # 更新信息素值
            
            # 保存当前路径
            ants_route[i] = path
            
            # 重置状态，准备构建下一条路径
            path = [1]              # 重置路径，从仓库开始
            travels = []            # 清空移动序列
            i = i + 1               # 路径编号+1
            colony.current_point = 1      # 回到仓库
            colony.capacity = 200.00      # 重置车辆容量
            colony.service_time = 0       # 重置服务时间


# 输出结果: 显示所有路径的节点访问顺序
print("所有路径的访问顺序:")
print(ants_route)
print(f"\n总共生成了 {len(ants_route)} 条路径")
print(f"总行驶距离: {colony.travel_distance:.2f}")


# # 画图
# coordinates={}
# for i,j in enumerate(colony.cordination):
#     coordinates[i+1]=j
# data=ants_route
# def draw_graph(coordinates, data):
#     plt.figure(figsize=(10, 6))
#     plt.grid(True)
#
#     # رسم یال‌های گراف
#     colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']  # رنگ‌های متفاوت برای هر مسیر
#     color_index = 0
#     for path in data.values():
#         for i in range(len(path) - 1):
#             x_values = [coordinates[path[i]][0], coordinates[path[i+1]][0]]  # مختصات x
#             y_values = [coordinates[path[i]][1], coordinates[path[i+1]][1]]  # مختصات y
#             plt.plot(x_values, y_values, marker='o', color=colors[color_index])
#         color_index = (color_index + 1) % len(colors)  # تغییر رنگ برای مسیر بعدی
#
#     # رسم نقاط گراف
#     for node, coords in coordinates.items():
#         plt.scatter(coords[0], coords[1], color='k', s=100)
#         plt.text(coords[0], coords[1], str(node), fontsize=12, ha='center', va='bottom')
#
#     plt.xlabel('X Coordinate')
#     plt.ylabel('Y Coordinate')
#     plt.title('Ant Colony Optimization Graph')
#     plt.show()
#
# # فراخوانی تابع برای رسم گراف
# draw_graph(coordinates, data)
#


# # 采用变体
# class Mutation:
#
#     def __init__(self, ants_route):
#         self.ants_route = ants_route
#         self.distance = 0
#
#     def swap_mutation(self):
#         half = int(len(self.ants_route) / 2)
#         while True:
#             route_i = random.randint(0, half - 1)
#             route_j = random.randint(half, len(self.ants_route) - 1)
#             node_i = random.randint(0, len(self.ants_route[route_i]) - 1)
#             node_j = random.randint(0, len(self.ants_route[route_j]) - 1)
#             if splited_data[node_i - 1][3] == splited_data[node_j - 1][3]:
#                 fake = self.ants_route[route_i][node_i]
#                 self.ants_route[route_i][node_i] = self.ants_route[route_j][node_j]
#                 self.ants_route[route_j][node_j] = fake
#                 break
#             else:
#                 continue
#         return self.ants_route
#
#     def mutated_distance(self, distance_matrix, travel):
#         self.distance += distance_matrix[travel]
#         return self.distance
#
# results = {}
# result_ant_numb = {}
# swap_mutated_result = {}
#
# for j in range(50):
#     ants_number = 0
#     ants_travels = {}
#     ants_route = {}
#     travels = []
#     path = [1]
#     colony = Ant(splited_data, 200.00, 0.9)
#     colony.customer_cord()
#     colony.euclidean_distance()
#     colony.width_window()
#     colony.path_pheromon()
#     colony.number_pheromon()
#     i = 0
#     while True:
#         colony.make_candidate_list()
#         colony.choose_next_node()
#         colony.cal_minimum_capacity()
#         colony.move()
#         path.append(colony.next_node)
#         travel = colony.travel
#         travels.append(travel)
#         if travel[1] == 1:
#             if travel == (1, 1):
#                 break
#             else:
#                 ants_travels[i] = travels
#                 colony.update_rho()
#                 colony.update_pheromon_number(ants_travels[i])
#                 colony.update_pheromon(ants_travels[i])
#                 ants_route[i] = path
#                 path = [1]
#                 travels = []
#                 i = i + 1
#                 colony.current_point = 1
#                 colony.capacity = 200.00
#                 colony.service_time = 0
#                 ants_number += 1
#
#     # #######Mutated################################
#
#     mutated_ants_route = {}
#     ant_travel = ()
#     ####swap mute###
#     mutated_route = Mutation(ants_route)
#
#     mutated_ants_route = mutated_route.swap_mutation()
#     for key, value in mutated_ants_route.items():
#         for i in range(len(value) - 1):
#             ant_travel = (value[i], value[i + 1])
#             mutated_route.mutated_distance(colony.distance_matrix, ant_travel)
#     swap_mutated_result[j] = mutated_route.distance
#     results[j] = colony.travel_distance
#     result_ant_numb[j] = (ants_number, mutated_route.distance)
# print('non mutation result:')
# print(results)
# print('swap mutation result:')
# print(swap_mutated_result)


