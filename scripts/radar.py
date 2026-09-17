from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from radar_impl import main

if __name__ == "__main__":
    main()
