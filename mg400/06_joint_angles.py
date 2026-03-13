"""
06_joint_angles.py — Joint-space motion, FK (PositiveSolution), and IK (InverseSolution).

Demonstrates:
  1. GetAngle()        — read current joint angles (degrees)
  2. JointMovJ()       — move in joint space (specify J1,J2,J3,J4 directly)
  3. PositiveSolution  — forward kinematics: angles → Cartesian pose
  4. InverseSolution   — inverse kinematics: Cartesian pose → joint angles
  5. Logging current pose and joints together

MG400 joints:
  J1 = base rotation  (-170° to +170°)
  J2 = shoulder       (-  5° to + 90°)  [MG400 specific; limits vary]
  J3 = elbow          (-140° to +  5°)
  J4 = wrist rotation (-170° to +170°)

Usage:
    python 06_joint_angles.py [--ip 192.168.2.9]
    python 06_joint_angles.py --robot 2
"""

import argparse
import time

from utils_mg400 import (
    connect,
    close_all,
    check_errors,
    go_home,
    parse_pose,
    parse_angles,
    SPEED_DEFAULT,
    MG400_IP,
    ROBOT_IPS,
)

# Joint-space waypoints (degrees): (J1, J2, J3, J4)
# These are example values — adjust for your robot's current calibration
JOINT_WAYPOINTS = [
    ( 0,   0,   0,  0),   # nominal zero (may not be same as Cartesian home)
    (30,   0,   0,  0),   # rotate base +30°
    (30,  20, -40,  0),   # raise arm
    ( 0,  20, -40, 30),   # rotate wrist +30°
    ( 0,   0,   0,  0),   # back to zero
]


def main():
    parser = argparse.ArgumentParser(description="MG400 joint angles demo")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    dashboard, move_api, feed = connect(ip)
    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print("Connected and enabled.\n")

        go_home(move_api)
        time.sleep(0.5)

        # --- 1. Read current state ---
        print("[1] Current state:")
        pose_resp  = dashboard.GetPose()
        angle_resp = dashboard.GetAngle()
        x, y, z, r    = parse_pose(pose_resp)
        j1, j2, j3, j4 = parse_angles(angle_resp)
        print(f"  Cartesian  : X={x:.2f}  Y={y:.2f}  Z={z:.2f}  R={r:.2f}  (mm/deg)")
        print(f"  Joint angles: J1={j1:.2f}  J2={j2:.2f}  J3={j3:.2f}  J4={j4:.2f}  (deg)")

        # --- 2. JointMovJ ---
        print(f"\n[2] JointMovJ through {len(JOINT_WAYPOINTS)} joint-space waypoints:")
        for i, (aj1, aj2, aj3, aj4) in enumerate(JOINT_WAYPOINTS, 1):
            print(f"  [{i}/{len(JOINT_WAYPOINTS)}] JointMovJ → J1={aj1}  J2={aj2}  J3={aj3}  J4={aj4}")
            move_api.JointMovJ(aj1, aj2, aj3, aj4)
            move_api.Sync()
            # Read back actual pose after each move
            a_resp = dashboard.GetAngle()
            rj1, rj2, rj3, rj4 = parse_angles(a_resp)
            print(f"           Actual J1={rj1:.1f}  J2={rj2:.1f}  J3={rj3:.1f}  J4={rj4:.1f}")
            time.sleep(0.3)

        # --- 3. Forward kinematics (PositiveSolution) ---
        print("\n[3] PositiveSolution (FK): angles → Cartesian pose")
        fk_angles = (20, 10, -30, 0)
        print(f"  Input angles: J1={fk_angles[0]}  J2={fk_angles[1]}  J3={fk_angles[2]}  J4={fk_angles[3]}")
        try:
            fk_resp = dashboard.PositiveSolution(*fk_angles, user=0, tool=0)
            print(f"  FK result   : {fk_resp.strip()}")
        except Exception as exc:
            print(f"  FK result   : (unavailable — {exc})")

        # --- 4. Inverse kinematics (InverseSolution) ---
        print("\n[4] InverseSolution (IK): Cartesian pose → joint angles")
        ik_pose = (300, 0, 50, 0)
        print(f"  Input pose  : X={ik_pose[0]}  Y={ik_pose[1]}  Z={ik_pose[2]}  R={ik_pose[3]}")
        try:
            ik_resp = dashboard.InverseSolution(*ik_pose, user=0, tool=0)
            print(f"  IK result   : {ik_resp.strip()}")
        except Exception as exc:
            print(f"  IK result   : (unavailable — {exc})")

        print("\nJoint angles demo complete.")
        go_home(move_api)

    finally:
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)


if __name__ == "__main__":
    main()
