"""
Blender（Z-up 右手系）→ Unity（Y-up 左手系）坐标换算，纯 Python，bpy 脚本与布局脚本共用。

链路：Blender 导出 glTF（+Y up）：(x, y, z)_b → (x, z, -y)_g ；
      Unity glTFast 导入时反转 X 轴（glTF +Z 正前 → Unity +Z 正前）：(x, y, z)_g → (-x, y, z)_u
      合成：(x, y, z)_b → (-x, z, -y)_u
Unity 的 Euler 顺序为 Quaternion.Euler(x, y, z) = Ry(y)·Rx(x)·Rz(z)。
"""
import math

def _rx(a):
    c, s = math.cos(a), math.sin(a); return [[1, 0, 0], [0, c, -s], [0, s, c]]
def _ry(a):
    c, s = math.cos(a), math.sin(a); return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
def _rz(a):
    c, s = math.cos(a), math.sin(a); return [[c, -s, 0], [s, c, 0], [0, 0, 1]]
def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

C = [[-1, 0, 0], [0, 0, 1], [0, -1, 0]]
C_INV = [[-1, 0, 0], [0, 0, -1], [0, 1, 0]]

def blender_pos_to_unity(p):
    return [round(-p[0], 3), round(p[2], 3), round(-p[1], 3)]

def unity_pos_to_blender(p):
    return [-p[0], -p[2], p[1]]

def blender_euler_to_unity(rx, ry, rz):
    """Blender XYZ Euler（弧度）→ Unity Euler（角度）。"""
    rb = _mm(_rz(rz), _mm(_ry(ry), _rx(rx)))
    r = _mm(C, _mm(rb, C_INV))
    x = math.asin(max(-1.0, min(1.0, -r[1][2])))
    y = math.atan2(r[0][2], r[2][2])
    z = math.atan2(r[1][0], r[1][1])
    return [round(math.degrees(x), 2), round(math.degrees(y), 2), round(math.degrees(z), 2)]

def unity_euler_to_blender(x, y, z):
    """Unity Euler（角度）→ Blender XYZ Euler（弧度）。"""
    x, y, z = map(math.radians, (x, y, z))
    ru = _mm(_ry(y), _mm(_rx(x), _rz(z)))
    r = _mm(C_INV, _mm(ru, C))
    # Blender XYZ: R = Rz·Ry·Rx → ry = asin(-r[2][0]); rx = atan2(r[2][1], r[2][2]); rz = atan2(r[1][0], r[0][0])
    ry = math.asin(max(-1.0, min(1.0, -r[2][0])))
    rx = math.atan2(r[2][1], r[2][2])
    rz = math.atan2(r[1][0], r[0][0])
    return (rx, ry, rz)

def blender_scale_to_unity(s):
    return [round(s[0], 3), round(s[2], 3), round(s[1], 3)]

def yaw_to_unity(rz_deg):
    """仅绕 Blender Z 轴的朝向角 → Unity 绕 Y 轴角度。"""
    return blender_euler_to_unity(0, 0, math.radians(rz_deg))[1]

def sun_to_unity(rx_deg, rz_deg):
    """Blender 太阳灯 rotation_euler=(rx, 0, rz)（度）→ Unity 方向光 Euler(pitch, yaw, 0)。"""
    return [90 - rx_deg, 180 - rz_deg, 0]

if __name__ == "__main__":
    # 自检：单轴旋转
    for e in ((90, 0, 0), (0, 90, 0), (0, 0, 90), (30, -45, 120)):
        u = blender_euler_to_unity(*map(math.radians, e))
        back = tuple(round(math.degrees(a), 2) for a in unity_euler_to_blender(*u))
        print(e, "->", u, "->", back)
