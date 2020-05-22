import os
import sys
import re
import configparser
import telegram.ext
import requests
import time
from PyPtt import PTT
#from telegram import ext




import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
# Initial bot by Telegram access token

config = configparser.ConfigParser()
config.read('config.ini')

def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')

def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def cheak(update, context):
    """Send a message when the command /cheak is issued."""
    PTTBot = PTT.API()
    
    ID = config.get('PTT','ID')
    Password = config.get('PTT','Password')

    trade_info = [
    ('Headphone', PTT.data_type.post_search_type.KEYWORD, '[交易]')
    ]

    try:
        PTTBot.login(ID, Password, kick_other_login=True)
    except PTT.exceptions.LoginError:
        PTTBot.log('登入失敗')
        sys.exit()
    except PTT.exceptions.WrongIDorPassword:
        PTTBot.log('帳號密碼錯誤')
        sys.exit()
    except PTT.exceptions.LoginTooOften:
        PTTBot.log('請稍等一下再登入')
        sys.exit()
    PTTBot.log('登入成功')
    update.message.reply_text('登入成功')

    for (trade_board, search_type, condition) in trade_info:
        index = PTTBot.get_newest_index(
            PTT.data_type.index_type.BBS,
            trade_board,
            search_type=search_type,
            search_condition=condition,
        )
        print(f'{trade_board} 最新關鍵字[交易]的文章編號為 {index}')



        post = PTTBot.get_post(
            trade_board,
            post_index=index,
            search_type=search_type,
            search_condition=condition,
        )

        print('標題:')
        print(post.title)
        print('作者:')
        print(post.author)
        print('內文:')
        print(post.content)
        print('=' * 50)

        #檢查可疑文章的作者在耳機板發了幾篇文章#
        post_autor = re.sub(u"\\(.*?\\)|\\{.*?}|\\[.*?]", "", post.author)
        print(f'{post_autor} 根據正規表示法解碼後的作者ID ')
        author_cheak = [
        ('Headphone', PTT.data_type.post_search_type.AUTHOR, post_autor)
        ]        
        for (author_board, search_type, condition) in author_cheak:
            index = PTTBot.get_newest_index(
                PTT.data_type.index_type.BBS,
                author_board,
                search_type=search_type,
                search_condition=condition,
            )
            print(f'他在 {author_board} 板發了 {index} 篇文章')
            
            #查詢這篇可疑的文章#
            post_D_info = PTTBot.get_post(
                author_board,
                post_index = index,
                search_type=search_type,
                search_condition=condition,
            )
            
            print('=' * 10 +'這是一篇可疑的文章'+ '=' * 10)
            print('標題:')
            print(post_D_info.title)
            print('作者:')
            print(post_D_info.author)
            print('內文:')
            print(post_D_info.content)
            print('=' * 50)
            

            if (index==1):
                print('這篇要被刪除的文章AID是:' + post_D_info.aid)
                post_D_info.author = re.sub(u"\\(.*?\\)|\\{.*?}|\\[.*?]", "", post_D_info.author)
                mark_type = PTT.data_type.mark_type.D
                PTTBot.mark_post(
                    mark_type,
                    'Headphone',
                    # AID 與 index 擇一使用
                    post_aid = post_D_info.aid,
                    # Postindex 可搭配 SearchType and SearchCondition 使用
                )

                mark_type = PTT.data_type.mark_type.DeleteD
                PTTBot.mark_post(
                    mark_type,
                    'Headphone',
                    post_aid = post_D_info.aid,
                )
                PTTBot.bucket(
                    # 看板
                    'Headphone',
                    # 幾天，請自行轉換成天數
                    360,
                    # 水桶原因
                    '板規一、a、1，未滿三篇非交易文不得發表交易文。',
                    # 水桶對象
                    post_D_info.author
                )
                update.message.reply_text('機器人剛剛幫你水桶了一個人')
                update.message.reply_text('被水桶的ID是 ：'+ post_D_info.author)
                update.message.reply_text('被水桶的AID是：'+ post_D_info.aid)
                update.message.reply_text('水桶的原因是：板規一、a、1，未滿三篇非交易文不得發表交易文。')
            else:
                update.message.reply_text('現在沒有人違規 開心')
                                


    time.sleep(3)
    PTTBot.logout()



def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    
    TOKEN = config.get('HeadphoneBot','ACCESS_TOKEN')
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("cheak", cheak))
    dp.add_handler(MessageHandler(Filters.text, echo))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
