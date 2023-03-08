import numpy as np
import cv2
import math

#  Euler Angles to Rotation Matrix
def eulerAnglesToRotationMatrix(roll, pitch, yaw):
    theta = np.zeros((3, 1), dtype=np.float64)
    theta[0] = roll
    theta[1] = pitch
    theta[2] = yaw
    R_x = np.array([[1, 0, 0],
                    [0, math.cos(theta[0]), -math.sin(theta[0])],
                    [0, math.sin(theta[0]), math.cos(theta[0])]
                    ])
    R_y = np.array([[math.cos(theta[1]), 0, math.sin(theta[1])],
                    [0, 1, 0],
                    [-math.sin(theta[1]), 0, math.cos(theta[1])]
                    ])
    R_z = np.array([[math.cos(theta[2]), -math.sin(theta[2]), 0],
                    [math.sin(theta[2]), math.cos(theta[2]), 0],
                    [0, 0, 1]
                    ])
    R = np.dot(R_z, np.dot(R_y, R_x))
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    singular = sy < 1e-6
    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0
    # print('dst:', R)
    x = x * 180.0 / 3.141592653589793
    y = y * 180.0 / 3.141592653589793
    z = z * 180.0 / 3.141592653589793
    return R


R2C = np.array([[0, 0, 1],
               [-1, 0, 0],
               [0, -1, 0]])

##Roll Pitch Yaw Degree
rpy=[0,7.2,0]
print(rpy)
R = eulerAnglesToRotationMatrix(rpy[0], rpy[1], rpy[2])
print("R= ", R)
C = np.dot(R2C,R)
print("C = ", C)
res = cv2.Rodrigues(C)[0]
print("res= ", res)
print(res[0][0], res[1][0], res[2][0])
