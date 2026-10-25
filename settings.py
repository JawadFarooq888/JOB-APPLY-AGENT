"""Loads settings from config.yaml, companies.yaml, the .env file and the resume."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent

# Read the .env file (only exists on your PC; on GitHub, secrets come as env vars)
load_dotenv(PROJECT_DIR / ".env")


def load_yaml(name):
    with open(PROJECT_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config():
    config = load_yaml("config.yaml")
    config["companies"] = load_yaml("companies.yaml")
    return config


def load_resume():
    """Resume text: from the RESUME_TEXT secret (GitHub) or resume.txt (your PC)."""
    text = os.getenv("RESUME_TEXT", "").strip()
    if text:
        return text
    path = PROJECT_DIR / "resume.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise SystemExit("No resume found. Put it in resume.txt or the RESUME_TEXT secret.")


def env(name, default=""):
    """Read one secret / setting from the environment (or .env)."""
    return os.getenv(name, default).strip()
