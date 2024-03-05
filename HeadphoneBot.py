import os
import sys
import re
import configparser
import telegram.ext
import requests
import time
from datetime import datetime
import asyncio
import PyPtt
import signal
from tqdm import tqdm
import pdb
import logging
import json
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Initial bot by Telegram access token

greatAuthorListPath = 'greatAuthorList.txt'
config_path = 'config.ini'
buckerList_path = 'bucketList.txt'
config = configparser.ConfigParser()
config.read(config_path)
# TOKEN = config['TELEGRAM']['TOKEN']


def login(ptt_bot=None):

    max_retry = 5
    for retry_time in range(max_retry):
        try:
            ptt_bot = PyPtt.API()
            ID = config.get('PTT','ID')
            Password = config.get('PTT','Password')

            ptt_bot.login(ID, Password,kick_other_session=False if retry_time == 0 else True)
            break
        except PyPtt.exceptions.LoginError:
            ptt_bot = None
            print('登入失敗')
            time.sleep(3)
        except PyPtt.exceptions.LoginTooOften:
            ptt_bot = None
            print('請稍後再試')
            time.sleep(60)
        except PyPtt.exceptions.WrongIDorPassword:
            print('帳號密碼錯誤')
            raise
        except Exception as e:
            print('其他錯誤:', e)
            break

    return ptt_bot


def PostDetect(ptt_bot, board, Author):
    count = 0
    target_label = '交易'
    author_newset_postindex = ptt_bot.get_newest_index(index_type=PyPtt.NewIndex.BOARD, board=board, search_type=PyPtt.SearchType.AUTHOR, search_condition=Author)
    index = author_newset_postindex
    
    while(index > 0):
        post_info = ptt_bot.get_post(board=board, index=index, search_type=PyPtt.SearchType.AUTHOR, search_condition=Author, query = True)
        match = re.search(r'\[(.*?)\]', post_info['title'])
        if match:
            label = match.group(1)
            if(label != target_label):
                count += 1
        else:
            print("這篇文章沒有分類")
        if(count >= 3):
            break
        index -= 1
    print("發布交易的作者: {}".format(Author))
    print("計數器狀態: {}".format(count))
    return count
        
    
def initGreatList(ptt_bot, board):
    least_mark_index = int(config.get('Headphone','least_mark_index'))
    newest_mark_index = ptt_bot.get_newest_index(index_type=PyPtt.NewIndex.BOARD, board=board, search_type=PyPtt.SearchType.MARK, search_condition='m')
    progress = tqdm(total=newest_mark_index)

    try:
        with open(greatAuthorListPath, "r") as GALF:
            great_authors = list(json.load(GALF))
    except FileNotFoundError:
        print("好作者列表 JSON檔案 未找到")
        great_authors = []
    except json.decoder.JSONDecodeError:
        print("好作者列表 JSON數據 解碼錯誤")
        great_authors = []
    mark_index = newest_mark_index
    while(mark_index > least_mark_index):
        try:
            post_info = ptt_bot.get_post(board=board, index=mark_index, search_type=PyPtt.SearchType.MARK, search_condition='m', query = True)
            Author = post_info['author']
            # Author = re.match(r'(?<!\()\s*([a-zA-Z0-9]+)', post_info['author'])
            # Author = Author.group()
            great_authors.append(Author)
            mark_index -= 1
            progress.update(1)

        except PyPtt.exceptions.ConnectionClosed:
            ptt_bot = login(ptt_bot)
            continue

    great_authors = list(set(great_authors))
    great_authors.sort()
    with open(greatAuthorListPath, "w") as GALF:
        json.dump(great_authors, GALF)
    least_mark_index = newest_mark_index
    config['Headphone']['least_mark_index'] = str(least_mark_index)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    print("優秀作者名單建立完成！")
    return great_authors




def Bucket(ptt_bot):
    detect_time = time.time()
    least_time = int(config.get('Headphone','least_time'))
    board = 'Headphone'
    target_label = '交易'
    bucket_days_list = [360, 180, 90]
    newest_index = ptt_bot.get_newest_index(PyPtt.NewIndex.BOARD, board)
    post_time = int(detect_time+1)
    great_list = initGreatList(ptt_bot, board)

    while((post_time - least_time) > 0):
        post_info = ptt_bot.get_post(board, index=newest_index)
        print("現在檢測到 Index: {} 的文章".format(newest_index))
        newest_index -= 1

        # 初始化作者
        Author = post_info['author']
        matchAuthor = re.match(r'(?<!\()\s*([a-zA-Z0-9]+)', post_info['author'])
        if matchAuthor:
            Author = matchAuthor.group()

        if(post_info[PyPtt.PostField.post_status] != PyPtt.PostStatus.EXISTS):
            print("這篇文章被刪除了！")
            continue
        elif(Author in great_list):
            print("這作者是好人！")
            continue
        else:
            # 取得文章發布時間
            match_label = re.search(r'\[(.*?)\]', post_info['title'])
            if match_label:
                label = match_label.group(1)
                if(label != target_label or label ==''):
                    continue
            date_string = post_info['date']
            date_object = datetime.strptime(date_string, "%a %b %d %H:%M:%S %Y")
            post_time = datetime.timestamp(date_object)
            print("Detect time {}".format(int(detect_time)))
            print("Post time {}".format(int(post_time)))
            matchAuthor = re.match(r'(?<!\()\s*([a-zA-Z0-9]+)', post_info['author'])
            if matchAuthor:
                Author = matchAuthor.group()
                Detect_result = PostDetect(ptt_bot, board, Author)
                if(Detect_result >= 3):
                    print("這作者 {} 有發滿三篇非交易文！".format(Author))
                    continue
                else:
                    # 這邊寫水桶程式
                    print("這作者 {} 該桶！".format(Author))
                    # ptt_bot.bucket(board=board, bucket_days=bucket_days_list[Detect_result], reason='違反板規一', ptt_id=Author)
                    with open(buckerList_path, 'a') as file:
                        file.write("Date: {}, UID: {}\n".format(date_object, Author))
                    continue
            else:
                print("這個作者怪怪的，直接跳過。")
                continue
        
        
    least_time = detect_time
    config['Headphone']['least_time'] = str(int(least_time))
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    print("檢測完成，任務結束！")
        

def HeadphoneBot():
    ptt_bot = login()
    Bucket(ptt_bot)
    ptt_bot.logout()

# def TelegramBot_log(bucket_list):
#     config = configparser.ConfigParser()
#     config.read('config.ini')
#     TOKEN = config['TELEGRAM']['TOKEN']

def main():
    HeadphoneBot()

if __name__ == '__main__':
    main()