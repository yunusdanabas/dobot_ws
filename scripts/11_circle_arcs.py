#!/usr/bin/env python3
"""
Circle Drawing via go_arc() Segments (Track A: pydobotplus)

Demonstrates the mathematical decomposition of a circle into N arc segments
using the go_arc(x, y, z, r, cir_x, cir_y, cir_z, cir_r) function.

Key insight:
  - go_arc() traces: Current Position → Via-Point → Target Endpoint
  - Via-point is NOT the circle center; it's an intermediate waypoint
  - For a full circle: minimum 4 arcs (90° each); 8 arcs (45° each) is smoother

Run with:
    python scripts/11_circle_arcs.py
"""

import math
import sys
import time
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home, get_home

def draw_circle_arcs(bot, center_x, center_y, z, radius, num_arcs=4, rot=0):
    """
    Draw a circle using go_arc() segments.
    
    Mathematical breakdown:
      For segment i (0 to num_arcs-1):
        via_angle = 2π·(i + 0.5) / num_arcs   (45°, 90°, 135°, ... for 8 arcs)
        end_angle = 2π·(i + 1) / num_arcs     (endpoint of this segment)
        
        via_x = cx + r·cos(via_angle)
        via_y = cy + r·sin(via_angle)
        end_x = cx + r·cos(end_angle)
        end_y = cy + r·sin(end_angle)
    
    Args:
        bot: Dobot instance
        center_x, center_y: Circle center (mm)
        z: Fixed height (mm)
        radius: Circle radius (mm)
        num_arcs: Number of arc segments (default 4 = quarter-circles)
        rot: End-effector rotation (degrees)
    """
    print(f"\n  📍 Drawing circle with {num_arcs} arc segment(s)")
    print(f"     Center: ({center_x}, {center_y}), Z={z}, Radius={radius} mm")
    print(f"     Arc angle: {360/num_arcs:.0f}° per segment")
    
    # Move to start of first arc (angle = 0°, east point)
    start_angle = 0
    start_x = center_x + radius * math.cos(start_angle)
    start_y = center_y + radius * math.sin(start_angle)
    
    print(f"     Start position: ({start_x:.1f}, {start_y:.1f})")
    safe_move(bot, start_x, start_y, z, rot)
    time.sleep(0.3)
    
    # Execute each arc segment
    for i in range(num_arcs):
        # Via-point is at the midpoint angle of this arc segment
        via_angle = 2 * math.pi * (i + 0.5) / num_arcs
        # Endpoint is at the end of this arc segment
        end_angle = 2 * math.pi * (i + 1) / num_arcs
        
        # Calculate via-point on the circle
        via_x = center_x + radius * math.cos(via_angle)
        via_y = center_y + radius * math.sin(via_angle)
        
        # Calculate endpoint on the circle
        end_x = center_x + radius * math.cos(end_angle)
        end_y = center_y + radius * math.sin(end_angle)
        
        via_deg = via_angle * 180 / math.pi
        end_deg = end_angle * 180 / math.pi
        
        print(f"       Arc {i+1:2d}/{num_arcs}: "
              f"{via_deg:6.1f}° via=({via_x:6.1f}, {via_y:6.1f}) "
              f"→ {end_deg:6.1f}° end=({end_x:6.1f}, {end_y:6.1f})")
        
        # Execute the arc
        bot.go_arc(
            x=end_x, y=end_y, z=z, r=rot,
            cir_x=via_x, cir_y=via_y, cir_z=z, cir_r=rot
        )
        time.sleep(0.1)
    
    print(f"     ✓ Circle complete")


def demo():
    """Demonstrate circle drawing with multiple arc decompositions."""
    port = find_port()
    if port is None:
        sys.exit("❌ No serial port found. Run: python scripts/01_find_port.py")
    
    bot = Dobot(port=port)
    try:
        print("\n" + "="*70)
        print("CIRCLE DRAWING VIA go_arc() DECOMPOSITION")
        print("="*70)
        print("✓ Connected to Dobot\n")
        
        # Set slow speed for visual validation
        bot.speed(50, 40)
        print("✓ Speed: 50 mm/s velocity, 40 mm/s² acceleration\n")
        
        # Start from home
        go_home(bot)
        time.sleep(0.5)
        hx, hy, hz, hr = get_home()
        
        # === Test 1: 4-arc circle (90° arcs) ===
        print("\n" + "─"*70)
        print("TEST 1: Minimum circle decomposition (4 arcs = quarter-circles)")
        print("─"*70)
        print("  Each arc covers 90°. Via-point at 45°, 135°, 225°, 315°")
        draw_circle_arcs(bot, hx + 20, hy, hz, 40, num_arcs=4)
        time.sleep(0.5)
        go_home(bot)
        time.sleep(0.5)
        
        # === Test 2: 8-arc circle (45° arcs, smoother) ===
        print("\n" + "─"*70)
        print("TEST 2: Smoother circle (8 arcs = 45° each)")
        print("─"*70)
        print("  Each arc covers 45°. Via-points at 22.5°, 67.5°, 112.5°, etc.")
        draw_circle_arcs(bot, hx + 20, hy, hz, 40, num_arcs=8)
        time.sleep(0.5)
        go_home(bot)
        time.sleep(0.5)
        
        # === Test 3: 12-arc circle (30° arcs, very smooth) ===
        print("\n" + "─"*70)
        print("TEST 3: High-quality circle (12 arcs = 30° each)")
        print("─"*70)
        print("  Each arc covers 30°. Better approximation of true circle.")
        draw_circle_arcs(bot, hx + 20, hy, hz, 40, num_arcs=12)
        time.sleep(0.5)
        go_home(bot)
        time.sleep(0.5)
        
        # === Test 4: Smaller circle with 8 arcs ===
        print("\n" + "─"*70)
        print("TEST 4: Smaller circle (radius=25mm, 8 arcs)")
        print("─"*70)
        print("  Demonstrates that the algorithm scales with radius.")
        draw_circle_arcs(bot, hx, hy - 60, hz, 25, num_arcs=8)
        time.sleep(0.5)
        go_home(bot)
        time.sleep(0.5)
        
        print("\n" + "="*70)
        print("✓ All tests completed successfully!")
        print("="*70)
        print("\nKey findings:")
        print("  • 4 arcs: Minimum; noticeable angular steps at 90° intervals")
        print("  • 8 arcs: Good balance of smoothness and execution speed")
        print("  • 12+ arcs: Visually indistinguishable from a true circle")
        print("\nFor teaching (ME403 labs):")
        print("  Prefer sampled move_to() circles (scripts/09_arc_motion.py)")
        print("  as they are more robust and easier to debug.\n")
        
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            go_home(bot)
        except Exception:
            pass
        bot.close()
        print("✓ Connection closed\n")


if __name__ == "__main__":
    demo()
