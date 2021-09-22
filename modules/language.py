import pathlib
import os
import json

from common import mysql

def get_language(id, str):
    default_lang = "ko_kr"

    temp = mysql.execute("SELECT lang FROM users_lang where userid = {uid} limit 1;".format(uid = int(id)))
    if temp == None:
        language = default_lang.lower()
        mysql.execute_only("INSERT INTO users_lang (userid) VALUES ({uid});".format(uid = int(id)))
    else:
        language = temp[0][0]

    if not os.path.exists(f"{pathlib.Path(__file__).parent.parent}/languages/{language.lower()}.json"):
        language = default_lang.lower()
    
    with open(f"{pathlib.Path(__file__).parent.parent}/languages/{language.lower()}.json", encoding="utf-8") as f:
        lang_data = json.load(f)

    f.close()
    
    return lang_data[str]
        

    
