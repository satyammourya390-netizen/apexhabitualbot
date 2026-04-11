#!/usr/bin/env python3
"""
Main entry point for Habitual Bot
"""
import subprocess
import sys
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "admin":
        print("Starting Admin Panel...")
        subprocess.run([sys.executable, "admin.py"])
    else:
        print("Starting Bot...")
        subprocess.run([sys.executable, "bot.py"])
if __name__ == "__main__":
    main()