#!/usr/bin/env python3
"""
Quick launcher for Napoleon Control Panel with demo mode.
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Napoleon's Command Panel - Enhanced GUI"
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run animation demo'
    )
    
    parser.add_argument(
        '--panel',
        action='store_true',
        help='Launch Napoleon Control Panel (default)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test all components'
    )
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo()
    elif args.test:
        run_tests()
    else:
        launch_panel()


def launch_panel():
    """Launch the main control panel."""
    print("👑 Launching Napoleon's Command Panel...")
    print("=" * 60)
    
    try:
        from src.gui.napoleon_panel import main
        main()
    except ImportError as e:
        print(f"Error: {e}")
        print("\nMake sure PyQt6 is installed:")
        print("pip install PyQt6")
        sys.exit(1)


def run_demo():
    """Run animation demo."""
    print("🎆 Running Animation Demo...")
    print("=" * 60)
    
    try:
        from src.gui.animated_components import demo_animations
        demo_animations()
    except ImportError as e:
        print(f"Error: {e}")
        sys.exit(1)


def run_tests():
    """Test all components."""
    print("🧪 Testing Components...")
    print("=" * 60)
    
    # Test imports
    try:
        from src.gui.napoleon_panel import NapoleonControlPanel
        print("✓ Control Panel imported")
    except ImportError as e:
        print(f"✗ Control Panel: {e}")
    
    try:
        from src.gui.animated_components import (
            ParticleSystem,
            VictoryAnimation,
            AnimatedProgressBar,
            ImperialNotification
        )
        print("✓ Animated Components imported")
    except ImportError as e:
        print(f"✗ Animated Components: {e}")
    
    # Test cheat commands
    try:
        from src.gui.napoleon_panel import CheatCommand, CheatCategory
        
        test_command = CheatCommand(
            id="test",
            name="Test Command",
            description="Testing",
            category=CheatCategory.TREASURY,
            icon="🧪"
        )
        print(f"✓ Cheat Command created: {test_command.name}")
    except Exception as e:
        print(f"✗ Cheat Command: {e}")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()
