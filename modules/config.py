import sys
import os
import configparser
from pytz import timezone
from colored import fore, back, style

from common import glob, logging

class config:
    def __init__(self, file):
        self.config = configparser.ConfigParser()
        self.default = True
        self.fileName = file
        if os.path.isfile(self.fileName):
            self.config.read(self.fileName, encoding="utf-8")
            self.default = False
        else:
            self.generateConfig()
            self.default = True

    def checkConfig(self, parsedConfig=None):
        if parsedConfig is None:
            parsedConfig = self.config
        
        try:
            parsedConfig.get("bot", "token")
            parsedConfig.get("bot", "prefix")
            parsedConfig.get("bot", "devloper_id")
            parsedConfig.get("db", "host")
            parsedConfig.get("db", "username")
            parsedConfig.get("db", "password")
            parsedConfig.get("db", "database")
            parsedConfig.get("general", "timezone")
            parsedConfig.get("lavalink", "host")
            parsedConfig.get("lavalink", "port")
            parsedConfig.get("lavalink", "password")
            return True
        except configparser.Error:
            return False
    
    def generateConfig(self):
        f = open(self.fileName, "w", encoding="utf-8")

        self.config.add_section("bot")
        self.config.set("bot", "token", "")
        self.config.set("bot", "prefix", "ㅇ")
        self.config.set("bot", "devloper_id", "")
        self.config.add_section("db")
        self.config.set("db", "host", "localhost")
        self.config.set("db", "username", "")
        self.config.set("db", "password", "")
        self.config.set("db", "database", "")
        self.config.add_section("general")
        self.config.set("general", "timezone", "Asia/Seoul")
        self.config.add_section("lavalink")
        self.config.set("lavalink", "host", "")
        self.config.set("lavalink", "port", "")
        self.config.set("lavalink", "password", "")

        self.config.write(f)
        
        f.close()