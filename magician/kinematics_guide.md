# Dobot Magician Kinematics Guide

This guide provides the mathematical foundations and technical parameters required for calculating the Forward and Inverse Kinematics of the Dobot Magician robotic arm.

## 1. Mechanical Dimensions (Link Lengths)

The Dobot Magician's geometry is defined by three main link lengths. Note that the parallel linkage mechanism significantly simplifies the kinematic model.

| Symbol | Description | Official Value | Code Variable (18_joint_control.py) |
| :--- | :--- | :--- | :--- |
| **$h_{base}$** | Base Height (Ground to Shoulder Joint) | 138.0 mm | *Not used in script FK* |
| **$L_{rear}$** | Rear Arm Length (Shoulder to Elbow) | 135.0 mm | `L1 = 135.0` |
| **$L_{fore}$** | Forearm Length (Elbow to Wrist) | 147.0 mm | `L2 = 147.0` |

### The Parallel Linkage Constraint
The Dobot Magician features a parallel four-bar linkage. Physically, this means that as Joint 2 (Shoulder) moves, the motor for Joint 3 (Elbow) remains at the base, and the linkage ensures that the orientation of the end-effector platform is always parallel to the base (horizontal).

In terms of angles:
- **$J_1$ (Base):** Rotation around the Z-axis.
- **$J_2$ (Shoulder):** Angle of the Rear Arm relative to the horizontal plane.
- **$J_3$ (Elbow):** Angle of the Forearm **relative to the Rear Arm**.
- **$\theta_{forearm}$ (Absolute):** The absolute angle of the forearm relative to the horizontal plane is **$J_2 + J_3$**.

---

## 2. Forward Kinematics (FK)

To find the Cartesian position $(x, y, z)$ from joint angles $(J_1, J_2, J_3)$:

1.  **Calculate the Plane Projection ($R$ and $Z_{arm}$):**
    The arm operates in a vertical plane that rotates with $J_1$.
    -   $R = L_{rear} \cdot \cos(J_2) + L_{fore} \cdot \cos(J_2 + J_3)$
    -   $Z_{arm} = L_{rear} \cdot \sin(J_2) + L_{fore} \cdot \sin(J_2 + J_3)$

2.  **Calculate Cartesian Coordinates:**
    -   $x = R \cdot \cos(J_1)$
    -   $y = R \cdot \sin(J_1)$
    -   $z = h_{base} + Z_{arm}$

---

## 3. Inverse Kinematics (IK)

To find joint angles $(J_1, J_2, J_3)$ from a target $(x, y, z)$:

1.  **Solve for $J_1$:**
    $J_1 = \operatorname{atan2}(y, x)$

2.  **Solve for $R$ and $Z_{arm}$:**
    -   $R = \sqrt{x^2 + y^2}$
    -   $Z_{arm} = z - h_{base}$

3.  **Solve the 2-Link Planar Arm (R, Z):**
    Using the Law of Cosines on the triangle formed by $(0,0)$, the elbow, and the wrist $(R, Z_{arm})$:
    -   $D = \frac{R^2 + Z_{arm}^2 - L_{rear}^2 - L_{fore}^2}{2 \cdot L_{rear} \cdot L_{fore}}$
    -   $\beta = \operatorname{atan2}(\sqrt{1-D^2}, D)$  *(This is the angle at the elbow)*
    -   $J_3 = \beta$ (or related by offset depending on convention)
    -   $J_2 = \operatorname{atan2}(Z_{arm}, R) - \operatorname{atan2}(L_{fore} \cdot \sin(\beta), L_{rear} + L_{fore} \cdot \cos(\beta))$

---

## 4. Denavit-Hartenberg (DH) Parameters

Standard DH parameters for students performing matrix-based analysis:

| Link ($i$) | $\theta_i$ | $d_i$ | $a_i$ | $\alpha_i$ |
| :--- | :--- | :--- | :--- | :--- |
| **1** | $J_1$ | 138 | 0 | $-90^\circ$ |
| **2** | $J_2 - 90^\circ$ | 0 | 135 | 0 |
| **3** | $J_3 + 90^\circ$ | 0 | 147 | 0 |
| **4** | $J_4$ | 0 | 0 | 0 |

---

## 5. Summary Table for Students

| Parameter | Value | Range |
| :--- | :--- | :--- |
| Max Reach | 320 mm | Radius from center |
| Payload | 500 g | Recommended max |
| Precision | 0.1 mm | Repetitive accuracy |
| Power | 12V / 7A | DC Input |
