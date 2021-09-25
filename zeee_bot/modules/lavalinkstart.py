import asyncio
from gc import freeze
from multiprocessing.spawn import freeze_support
from operator import mul
import os
import pathlib
import requests
import json
from urllib import request
from multiprocessing import Process

def child_process():
    print("lavalink start...")
    os.system(f"java -jar Lavalink.jar")
