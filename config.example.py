import json

TOKEN = ""
PREFIX = ""
OWNERS = []

DISCODO_HOST = "discodo"

with open("config.json") as f:
    discodo = json.load(f)
