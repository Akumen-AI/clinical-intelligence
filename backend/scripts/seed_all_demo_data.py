"""
This script reproduces the full demo environment from an empty database.
It sets up the synthetic demo accounts and then seeds the rich, believable clinical demo data.
"""
import os
import sys

# Ensure backend root directory is in python search path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.seed_users import seed_users
from scripts.seed_demo_data import seed_demo_data

def main():
    print("--- Seeding Users ---")
    seed_users()
    print("\n--- Seeding Demo Data ---")
    seed_demo_data()
    print("\n--- All Seeding Complete ---")

if __name__ == "__main__":
    main()
