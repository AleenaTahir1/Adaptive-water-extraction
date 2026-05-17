"""Launch the Mesa visualization server.

Usage:
    python run.py

Opens browser UI at http://127.0.0.1:8521
"""
from water_abm.server import create_server


if __name__ == "__main__":
    server = create_server()
    server.port = 8521
    server.launch()
