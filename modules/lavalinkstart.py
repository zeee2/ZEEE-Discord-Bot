import os
import multiprocessing
import requests
import json

def child_process():
    print(f"Child process PID : {multiprocessing.current_process().pid}")
    a = requests.get("https://api.github.com/repos/Cog-Creators/Lavalink-Jars/releases")
    b = json.loads(a.text)
    os.system(f"java -jar Lavalink-{b[0]['tag_name']}.jar")
