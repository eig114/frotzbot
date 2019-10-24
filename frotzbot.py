#!/usr/bin/python3

# Frotzbot - a telegram bot to play interactive fiction via
# external interpreter. Interpreters need to be compiled against remglk
# library (https://github.com/erkyrath/remglk)
# Idea (and some of the code) taken from https://github.com/sneaksnake/z5bot

import telegram.ext
import json
import frotzbotchat
import logging

from telegram.ext import Updater,CommandHandler,MessageHandler,Filters

chat_dict = dict()
config = dict()

# set up logging
logging.basicConfig(
    format='[%(asctime)s-%(name)s-%(levelname)s]\n%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    filename='frotzbot.log')
logging.getLogger('telegram').setLevel(logging.WARNING)


def log_dialog(in_message, out_messages):
    logging.info('@%s[%d] sent: %r' %
                 (in_message.from_user.username, in_message.from_user.id,
                  in_message.text))
    for out_message in out_messages:
        logging.info('Answering @%s[%d]: %r' % (
            in_message.from_user.username, in_message.from_user.id, out_message
            if out_message is not None else '[None]'))


def on_error(update, context):
    logger = logging.getLogger(__name__)
    logger.warn('Update %r caused error %r!' % (update, context.error))
    print(context.error)



def reload_conf(update, context, conf_path):
    bot = context.bot
    try:
        global config
        with open('config.json', 'r') as f:
            config = json.load(f)

        for chat in chat_dict.values():
            chat.games_dict = config['stories']
            chat.interpreter_path = config['interpreter']
            chat.interpreter_args = config['interpreter_args']

        text = '[Done! Changes will apply on next restart]'
        bot.sendMessage(chat_id=update.message.chat_id, text=text)
        log_dialog(update.message, [text])
    except Exception:
        # traceback.print_exc()
        text = '[Something went wrong. Your new config is probably invalid or something]'
        bot.sendMessage(chat_id=update.message.chat_id, text=text)
        log_dialog(update.message, [text])
        logging.exception('JSON configuration loading failed')


def get_chat(bot, chat_id):
    global chat_dict
    global config
    if (chat_id in chat_dict):
        chat = chat_dict[chat_id]
    else:
        logging.info('New chat instance: %s' % chat_id)
        chat = frotzbotchat.FrotzbotChat(bot, chat_id, config)
        chat_dict[chat_id] = chat

    return chat


def start(update, context):
    bot = context.bot
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_start)
    log_dialog(update.message, response_msgs)


def enter(update, context):
    bot = context.bot
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_enter)
    log_dialog(update.message, response_msgs)


def space(update, context):
    bot = context.bot
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_space)
    log_dialog(update.message, response_msgs)


def handle_text(update, context):
    bot = context.bot
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update)
    log_dialog(update.message, response_msgs)


def handle_file(update, context):
    bot = context.bot
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update)
    log_dialog(update.message, response_msgs)


def quit_interpreter(update, context):
    bot = context.bot
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_quit)
    log_dialog(update.message, response_msgs)

def list_savefiles(update, context):
    chat = get_chat(context.bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_list_savefiles)
    log_dialog(update.message, response_msgs)

def unknown_cmd(update, context):
    bot = context.bot
    text = '[I beg your pardon?]'
    bot.sendMessage(chat_id=update.message.chat_id, text=text)
    log_dialog(update.message, [text])


def unsupported(update, context):
    bot = context.bot
    text = '[I don\'t support this command yet. Sorry!]'
    bot.sendMessage(chat_id=update.message.chat_id, text=text)
    log_dialog(update.message.text, [text])


def main(config_path='config.json'):
    # load config
    global config
    with open(config_path, 'r') as f:
        config = json.load(f)

    # set up updater
    global updater
    updater = Updater(config['api_key'], use_context=True)
    dispatcher = updater.dispatcher

    # set up message handlers
    start_cmd_handler = CommandHandler('start', start)
    enter_cmd_handler = CommandHandler('enter', enter)
    space_cmd_handler = CommandHandler('space', space)
    quit_cmd_handler =CommandHandler('quit', quit_interpreter)
    listsaves_cmd_handler = CommandHandler('list_saves', list_savefiles)
    reload_handler = CommandHandler('reload_conf', lambda u,c: reload_conf(u, c, config_path))
    terp_cmd_handler = MessageHandler(telegram.ext.Filters.text, handle_text)
    file_handler = MessageHandler(telegram.ext.Filters.document, handle_file)

    unknown_cmd_handler = MessageHandler(telegram.ext.Filters.command, unknown_cmd)

    # error handlers
    dispatcher.add_error_handler(on_error)

    # command handlers
    dispatcher.add_handler(start_cmd_handler)
    dispatcher.add_handler(enter_cmd_handler)
    dispatcher.add_handler(space_cmd_handler)
    dispatcher.add_handler(quit_cmd_handler)
    dispatcher.add_handler(reload_handler)
    dispatcher.add_handler(listsaves_cmd_handler)

    # text handlers
    dispatcher.add_handler(terp_cmd_handler)

    # file handler
    dispatcher.add_handler(file_handler)

    # always add unknown cmd handler last
    dispatcher.add_handler(unknown_cmd_handler)

    updater.start_polling(clean=True)
    updater.idle()


if __name__ == '__main__':
    main()
