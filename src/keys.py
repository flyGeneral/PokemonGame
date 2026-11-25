"""按键映射(集中管理)。

右手四键 UIJK 按 Nintendo Switch / DS 手柄的菱形排列(右手上排 U I,下排 J K):

        U = X 键(菜单)        I = A 键(确定 / 对话 / 调查 / 推进文本)
        J = Y 键(快捷背包)    K = B 键(取消 / 返回;按住跑步)

与原作《钻石/珍珠》一致:A 确定、B 取消并按住跑步、X 打开菜单、Y 使用登记道具
(本作把 Y 简化为直接打开背包)。方向键与 WASD 仍用于移动/光标;
Z / 空格 / 回车 仍可当作 A,X / Esc 仍可当作 B(兼容旧测试与 RL 环境)。
"""
import pygame

UP = (pygame.K_UP, pygame.K_w)
DOWN = (pygame.K_DOWN, pygame.K_s)
LEFT = (pygame.K_LEFT, pygame.K_a)
RIGHT = (pygame.K_RIGHT, pygame.K_d)

A = (pygame.K_i, pygame.K_z, pygame.K_RETURN, pygame.K_SPACE)   # 确定
B = (pygame.K_k, pygame.K_x, pygame.K_ESCAPE)                   # 取消 / 返回
X = (pygame.K_u, pygame.K_RETURN)                               # 菜单(回车兼容旧习惯)
Y = (pygame.K_j,)                                               # 快捷背包
RUN = (pygame.K_k, pygame.K_b, pygame.K_LSHIFT, pygame.K_RSHIFT)   # 按住跑步

MOVE_KEYS = UP + DOWN + LEFT + RIGHT
HELD_KEYS = MOVE_KEYS + RUN                                     # 需要记录按下状态的键

# 界面提示文案
HINT_CONFIRM = "I"
HINT_CANCEL = "K"
HINT_MENU = "U"
HINT_BAG = "J"
HINT_UI = f"{HINT_CONFIRM} 确认   {HINT_CANCEL} 返回"
HINT_CLOSE = f"{HINT_CONFIRM} 关闭"
HINT_FIELD = (f"方向键/WASD 移动   {HINT_CONFIRM} 调查/对话   {HINT_MENU} 菜单   "
              f"{HINT_BAG} 背包   按住 {HINT_CANCEL}/Shift 跑步")


def is_a(key):
    return key in A


def is_b(key):
    return key in B
