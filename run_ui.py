#!/usr/bin/env python
"""Launch script for MyPaperAgent Streamlit UI."""
import subprocess
import sys
from pathlib import Path


def main():
    """Run the Streamlit app."""
    app_path = Path(__file__).parent / "src" / "ui" / "app.py"

    if not app_path.exists():
        print(f"Error: App file not found at {app_path}")
        sys.exit(1)

    print("🚀 Launching MyPaperAgent UI...")
    print(f"📂 App path: {app_path}")
    print("\n" + "="*50)
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")

    try:
        # Use uv run for consistency with the rest of the project
        subprocess.run([
            "uv", "run", "streamlit", "run",
            str(app_path),
            "--server.port=8501",
            "--browser.gatherUsageStats=false"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down MyPaperAgent UI...")
        sys.exit(0)
    except FileNotFoundError:
        print("\n❌ Error: 'uv' not found. Please install uv first:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
