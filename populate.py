#!/usr/bin/env python
import os
import subprocess
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "financeiro.settings")
    subprocess.run([sys.executable, "manage.py", "seed_initial_data"], check=True)


if __name__ == "__main__":
    main()
