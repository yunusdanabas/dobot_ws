# Dobot Magician - Technical & Kinematic Specifications

## Technical Drawing & Dimensions

The Dobot Magician is a 4-DOF desktop robotic arm. It uses a **parallel four-bar linkage** mechanism for its rear and forearms, which ensures the end-effector platform remains parallel to the base (horizontal) at all times.

### Link Lengths (mm)
| Link | Description | Length (mm) |
| :--- | :--- | :--- |
| **$L_1$** | Base to Shoulder (Z-offset) | 138.0 |
| **$L_2$** | Rear Arm (Shoulder to Elbow) | 135.0 |
| **$L_3$** | Forearm (Elbow to Wrist) | 147.0 |
| **$L_{total}$** | Maximum Reach (Radius) | 320.0 |

### Joint Ranges & Limits
| Joint | Range (Degrees) | Physical Limit |
| :--- | :--- | :--- |
| **J1 (Base)** | $-135^\circ$ to $+135^\circ$ | ±135° |
| **J2 (Rear Arm)** | $0^\circ$ to $+85^\circ$ | 0° to 85° |
| **J3 (Forearm)** | $-10^\circ$ to $+95^\circ$ | -10° to 95° |
| **J4 (End Effector)** | $-140^\circ$ to $+140^\circ$ | ±150° (approx) |

*Note: In some software implementations (like pydobotplus), J2 and J3 may have different internal offsets. Always refer to the specific library documentation.*

---

## Denavit-Hartenberg (DH) Parameters

The following table represents the standard DH parameters for the Dobot Magician. Because of the parallel linkage, the angle of link 3 is typically measured relative to the horizontal plane.

| Link ($i$) | $\theta_i$ | $d_i$ | $a_i$ | $\alpha_i$ |
| :--- | :--- | :--- | :--- | :--- |
| **1 (Base)** | $q_1$ | 138 | 0 | $-90^\circ$ |
| **2 (Rear)** | $q_2 - 90^\circ$ | 0 | 135 | 0 |
| **3 (Fore)** | $q_3 + 90^\circ$ | 0 | 147 | 0 |
| **4 (Servo)** | $q_4$ | 0 | 0 | 0 |

---

## Kinematic Equations

### Forward Kinematics (Geometric Approach)
Given the joint angles ($q_1, q_2, q_3$), the Cartesian coordinates ($x, y, z$) of the tool center point (TCP) are:

1.  **Radial Distance ($R$):**  
    $R = L_2 \cdot \cos(q_2) + L_3 \cdot \cos(q_3)$
2.  **X Position:**  
    $x = R \cdot \cos(q_1)$
3.  **Y Position:**  
    $y = R \cdot \sin(q_1)$
4.  **Z Position:**  
    $z = L_1 + L_2 \cdot \sin(q_2) - L_3 \cdot \sin(q_3)$

### Inverse Kinematics
To find $(q_1, q_2, q_3)$ from $(x, y, z)$:
1.  **$q_1 = \operatorname{atan2}(y, x)$**
2.  **$q_2, q_3$** are solved by projecting the arm onto the vertical plane $(R, Z)$ and using the Law of Cosines on the triangle formed by the shoulder, elbow, and wrist.

---

## Power Information
- **Power Input:** DC 12V 7A

## Compliance Marks
- FCC, CE, REACH SVHC, KC, WEEE, Recycling, PSE, RoHS

## Manufacturing Information
- **Company:** Shenzhen Yuejiang Technology Co., Ltd.
- **Serial Number:** DT1317081333
- **Website:** www.dobot.cc

## Warning
**Chinese:** 警告：内含金属弹性结构件，不正当的拆解可能造成人身伤害或损害内部零件。如需维修，请联系当地代理或官方售后进行处理。  
**English:** Warning: There are mental elastic components. Improper disassembly may cause injury or damage to internal parts. If there is a need to repair, please contact local agents our technical support.