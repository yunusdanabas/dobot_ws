"""
lab01_fk.py — Lab 01: Forward Kinematics (DOBOT MG400)
ME403 Introduction to Robotics | Sabanci University | Spring 2025-26

Instructions
------------
This script is your workspace. Do NOT modify the SETUP or TEARDOWN sections.
Work only inside the three TASK blocks.

Body-frame joint angles (what you specify in q):
  q[0]  J1 — base rotation (same as firmware)
  q[1]  J2 — shoulder elevation from horizontal
  q[2]  J3 — elbow angle FROM the upper-arm direction  ← body-frame offset
  q[3]  J4 — wrist angle FROM the forearm direction    ← body-frame offset

The FK formula (planar 2-link model, base rotation q[0] out of plane):

  theta2 = radians(q[1])               # shoulder absolute angle
  theta3 = radians(q[1] + q[2])        # forearm absolute angle
  reach  = L1*cos(theta2) + L2*cos(theta3)   # horizontal projection
  Z_pred = Z_base + L1*sin(theta2) + L2*sin(theta3)
  X_pred = reach * cos(radians(q[0]))
  Y_pred = reach * sin(radians(q[0]))

Link lengths: L1 = 175 mm, L2 = 175 mm.
Z_base ≈ 116 mm (shoulder height above mounting surface; verify at Task 0).

Robot selection:
  Change setup(robot=1) to setup(robot=2), setup(robot=3), or setup(robot=4)
  to use a different robot. See the Robot Network Map below.

  Robot 1  192.168.2.7   (match robot sticker)
  Robot 2  192.168.2.10  (match robot sticker)
  Robot 3  192.168.2.9   (match robot sticker)
  Robot 4  192.168.2.6   (match robot sticker)
"""

import math

import utils_mg400 as U

# ── SETUP (do not modify) ─────────────────────────────────────────────────────
# try/finally ensures teardown() runs even if your code crashes (prevents
# the robot from staying enabled with an open TCP connection).
dashboard, move_api = U.setup(robot=1)   # change robot=N as needed
try:
    L1     = U.L1      # 175.0 mm
    L2     = U.L2      # 175.0 mm
    Z_base = U.Z_base  # 116.0 mm (nominal; verify below)

    # ── TASK 0: Measure Z_base (5 min) ───────────────────────────────────────
    # setup() homes the arm to READY_POSE (300, 0, 50, 0).
    # To find Z_base, move the arm to J2=0 (horizontal upper arm) and read Z.
    # Move to body-frame q=[0, 0, 0, 0]:
    U.moveMG400(move_api, [0, 0, 0, 0])
    x0, y0, z0, r0 = U.get_pose(dashboard)
    print(f"\nTask 0 — Arm horizontal (q=[0,0,0,0]):")
    print(f"  Pose: X={x0:.1f}  Y={y0:.1f}  Z={z0:.1f}")
    print(f"  Z_base (nominal): {Z_base:.1f} mm   |   Z_base (measured): {z0:.1f} mm")
    # Optionally use the measured value in Tasks 1–3:
    # Z_base = z0

    # ── TASK 1: Single Configuration ─────────────────────────────────────────
    # Choose one body-frame configuration. Move the robot to it, then compare
    # the robot's actual pose to your hand-calculated FK prediction.
    #
    # Guidelines: keep J2 between 10° and 60° and J3 between 0° and 40°
    # to stay safely within the robot's workspace. Keep J1=0 for the
    # planar FK formula to apply directly.
    #
    # EXAMPLE:  q = [0, 30, 20, 0]
    #   theta2 = radians(30)  = 0.5236 rad
    #   theta3 = radians(50)  = 0.8727 rad  (30 + 20)
    #   reach  = 175*cos(0.5236) + 175*cos(0.8727) = 151.6 + 112.6 = 264.2 mm
    #   Z_pred = 116 + 175*sin(0.5236) + 175*sin(0.8727) = 116 + 87.5 + 134.0 = 337.5 mm
    #   X_pred = 264.2 * cos(0) = 264.2 mm
    # ─────────────────────────────────────────────────────────────────────────

    # TODO: replace None with your chosen body-frame angles [q1, q2, q3, q4]
    q1 = None   # e.g. [0, 30, 20, 0]

    U.moveMG400(move_api, q1)
    pose1 = U.get_pose(dashboard)
    print(f"\nTask 1 — Actual pose:")
    print(f"  X={pose1[0]:.2f}  Y={pose1[1]:.2f}  Z={pose1[2]:.2f}  R={pose1[3]:.2f}")

    # TODO: compute your hand-calculated prediction on paper, then print it here.
    # X_pred_1 = ???
    # Z_pred_1 = ???
    # print(f"  X_pred={X_pred_1:.2f}   Z_pred={Z_pred_1:.2f}")
    # print(f"  Error XY = {abs(pose1[0] - X_pred_1):.2f} mm   "
    #       f"Error Z  = {abs(pose1[2] - Z_pred_1):.2f} mm")

    # ── TASK 2: Multi-Step Trajectory ────────────────────────────────────────
    # Define at least 3 body-frame configurations. The robot moves through them
    # in order. Each row is [q1, q2, q3, q4].
    # Observe the path the end-effector traces. Describe it qualitatively.
    # ─────────────────────────────────────────────────────────────────────────

    # TODO: fill in at least 3 configurations (replace each None)
    configurations = [
        None,   # e.g. [0,  20, 10, 0]
        None,   # e.g. [20, 30, 15, 0]
        None,   # e.g. [0,  45, 25, 0]
    ]

    print("\nTask 2 — Trajectory:")
    print(f"  {'Step':<6} {'q':^26} {'X':>8} {'Y':>8} {'Z':>8}")
    for i, q in enumerate(configurations):
        U.moveMG400(move_api, q)
        pose = U.get_pose(dashboard)
        print(f"  {i+1:<6} {str(q):<26} {pose[0]:>8.1f} {pose[1]:>8.1f} {pose[2]:>8.1f}")

    # ── TASK 3: FK Verification ───────────────────────────────────────────────
    # Implement the planar FK formula. Predict (X, Y, Z) for each configuration
    # in Task 2, then compare to the robot's actual reported pose.
    #
    # Advanced: the MG400 firmware can also compute FK for you.
    # After filling in fk_predict(), add a cross-check:
    #   j1_fw, j2_fw, j3_fw, j4_fw = U._rel_to_fw_mg400(q)
    #   fk_str = dashboard.PositiveSolution(j1_fw, j2_fw, j3_fw, j4_fw)
    # Compare the PositiveSolution output to your fk_predict() output.
    # ─────────────────────────────────────────────────────────────────────────

    def fk_predict(q, L1, L2, Z_base):
        """Predict (x, y, z) from body-frame joint angles using planar 2R FK.

        TODO: fill in the three ??? expressions below.

        Args:
            q:      [q1, q2, q3, q4] body-frame angles (degrees)
            L1:     upper-arm length (mm)
            L2:     forearm length (mm)
            Z_base: shoulder height above mounting surface (mm)

        Returns:
            (x, y, z) predicted Cartesian position in mm
        """
        theta2 = math.radians(q[1])
        theta3 = math.radians(q[1] + q[2])   # forearm absolute angle from horizontal

        reach  = None  # TODO: L1*cos(theta2) + L2*cos(theta3)
        Z_pred = None  # TODO: Z_base + L1*sin(theta2) + L2*sin(theta3)
        X_pred = None  # TODO: reach * math.cos(math.radians(q[0]))
        Y_pred = None  # TODO: reach * math.sin(math.radians(q[0]))

        return X_pred, Y_pred, Z_pred

    print("\nTask 3 — FK prediction vs actual:")
    print(f"  {'q':^26} {'Xp':>8} {'Zp':>8}  {'Xa':>8} {'Za':>8}  {'eXY':>8} {'eZ':>8}")
    for q in configurations:
        U.moveMG400(move_api, q)
        act = U.get_pose(dashboard)
        # TODO: call fk_predict and compute errors, then uncomment the print below
        # xp, yp, zp = fk_predict(q, L1, L2, Z_base)
        # e_xy = math.sqrt((act[0]-xp)**2 + (act[1]-yp)**2)
        # e_z  = abs(act[2] - zp)
        # print(f"  {str(q):<26} {xp:>8.1f} {zp:>8.1f}  "
        #       f"{act[0]:>8.1f} {act[2]:>8.1f}  {e_xy:>8.2f} {e_z:>8.2f}")

# ── TEARDOWN (do not modify) ──────────────────────────────────────────────────
finally:
    U.teardown(dashboard, move_api)
    print("Done.")
