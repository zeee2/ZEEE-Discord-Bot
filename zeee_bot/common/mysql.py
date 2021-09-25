import mysql.connector
from mysql.connector import errorcode
import sys

from zeee_bot.common import glob, logging

def DB_CONNECT():
    try:
        cnx = mysql.connector.connect(
            user       = glob.SQL_USER,
            password   = glob.SQL_PASS,
            host       = glob.SQL_HOST,
            database   = glob.SQL_DB,
            autocommit = True,
            auth_plugin='mysql_native_password')
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logging.ConsoleLog("danger", 'DB', "Something is wrong with your username or password.")
            sys.exit()
        elif err.errno == errorcode.ER_BAD_DB_ERROR:   
            logging.ConsoleLog("danger", 'DB', "Database does not exist. Auto Create Process Start")
            return DB_CREATE()
        else:
            raise Exception(err)
    else:
        glob.DB = cnx
    if not glob.DB: raise Exception('Could not connect to SQL.')
    logging.ConsoleLog("ok", 'DB', "Connected DB.")
    CHECK_TABLE()


def DB_CREATE():
    logging.ConsoleLog("index", 'DB', "Database Creating.....")
    cnx = mysql.connector.connect(
        user       = glob.SQL_USER,
        password   = glob.SQL_PASS,
        host       = glob.SQL_HOST,
        autocommit = True,
        auth_plugin='mysql_native_password') 
    cur = cnx.cursor()
    cur.execute(f"CREATE DATABASE {glob.SQL_DB} default CHARACTER SET UTF8;")
    logging.ConsoleLog("index", 'DB', "A database Created.")
    cur.close()
    return DB_CONNECT()


def CHECK_TABLE():
    logging.ConsoleLog("ok", 'DB CHECKER', f"Checking DB Tables...")
    okTable = []
    CHECK_QUERYS_TABLE = ["users_lang", "musicBot_logs", "musicBot_queue"]
    cur = glob.DB.cursor()
    for query in CHECK_QUERYS_TABLE:
        cur.execute(f"""
            SELECT EXISTS (
            SELECT 1 FROM Information_schema.tables
            WHERE table_schema = '{glob.SQL_DB}'
            AND table_name = '{query}'
            ) AS flag
        """)
        checker = cur.fetchone()[0]
        okTable.append({query: int(checker)})
        
    for check in okTable:
        for key in check.keys():
            if key == "users_lang" and check[key] == 0:
                execute_only(f"""
                    CREATE TABLE `zeeebot`.`users_lang` (
                    `userid` BIGINT NOT NULL,
                    `lang` VARCHAR(6) NULL DEFAULT 'ko_kr',
                    PRIMARY KEY (`userid`))
                    ENGINE = InnoDB
                    DEFAULT CHARACTER SET = utf8mb4;
                """)
                logging.ConsoleLog("war", 'DB CHECKER', f"{key} table generated.")
            if key == "musicBot_queue" and check[key] == 0:
                execute_only(f"""
                CREATE TABLE `zeeebot`.`musicBot_queue` (
                    `queue_id` INT NOT NULL,
                    `track_id` BIGINT NULL,
                    `requester_id` BIGINT NULL,
                    `requester` VARCHAR(45) NULL,
                    `guild_id` BIGINT NULL,
                    `in_time` TIMESTAMP NULL,
                PRIMARY KEY (`queue_id`));
                """)
                logging.ConsoleLog("war", 'DB CHECKER', f"{key} table generated.")
    cur.close()


def execute(query):
    cur = glob.DB.cursor(buffered=True)
    cur.execute(query)
    result = cur.fetchall()
    cur.close()
    return result

def execute_one(query):
    cur = glob.DB.cursor(buffered=True)
    cur.execute(query)
    result = cur.fetchone()
    cur.close()
    return result


def execute_only(query):
    cur = glob.DB.cursor(buffered=True)
    try:
        cur.execute(query)
    except Exception as e:
        print(e)
        cur.close()
        return False
    cur.close()
    return True