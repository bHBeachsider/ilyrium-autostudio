"""Make the `satirist` package importable when pytest runs from apps/satirist/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
