#!/bin/python3

# Frotzbot - a telegram bot to play zcode games via dfrotz.
# Idea (and some of the code) taken from https://github.com/sneaksnake/z5bot

import telegram.ext
import traceback
import json
import frotzbotchat

chat_dict = dict()
config = dict()


def debug(bot, update):
    try:
        entries = ['1', '2', '3']
        keyboard = telegram.ReplyKeyboardMarkup(
            entries, resize_keyboard=True, one_time_keyboard=True)

        bot.sendMessage(
            chat_id=update.message.chat_id,
            text='Choose your destiny:',
            reply_markup=keyboard)
    except Exception:
        traceback.print_exc()


def get_chat(chat_id):
    global chat_dict
    global config
    if (chat_id in chat_dict):
        chat = chat_dict[chat_id]
    else:
        chat = frotzbotchat.FrotzbotChat(chat_id, config)
        chat_dict[chat_id] = chat

    return chat


def start(bot, update):
    try:
        chat = get_chat(update.message.chat_id)
        chat.reply(bot, update, chat.cmd_start)
    except Exception:
        traceback.print_exc()


def enter(bot, update):
    try:
        chat = get_chat(update.message.chat_id)
        chat.reply(bot, update, chat.cmd_enter)
    except Exception:
        traceback.print_exc()


def handle_text(bot, update):
    try:
        chat = get_chat(update.message.chat_id)
        chat.reply(bot, update)
    except Exception:
        traceback.print_exc()


def quit_interpreter(bot, update):
    try:
        chat = get_chat(update.message.chat_id)
        chat.reply(bot, update, chat.cmd_quit)
    except Exception:
        traceback.print_exc()


def unknown_cmd(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text='I beg your pardon?')


def unsupported(bot, update):
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text='I don\'t support this command yet. Sorry!')


def main():
    global updater
    global config
    with open('config.json', 'r') as f:
        config = json.load(f)

    updater = telegram.ext.Updater(config['api_key'])
    dispatcher = updater.dispatcher

    start_cmd_handler = telegram.ext.CommandHandler('start', start)
    enter_cmd_handler = telegram.ext.CommandHandler('enter', enter)
    quit_cmd_handler = telegram.ext.CommandHandler('quit', quit_interpreter)
    save_cmd_handler = telegram.ext.CommandHandler('save', unsupported)
    restore_cmd_handler = telegram.ext.CommandHandler('restore', unsupported)
    debug_handler = telegram.ext.CommandHandler('debug', debug)
    terp_cmd_handler = telegram.ext.MessageHandler([telegram.ext.Filters.text],
                                                   handle_text)
    unknown_cmd_handler = telegram.ext.MessageHandler(
        [telegram.ext.Filters.command], unknown_cmd)

    # error handlers
    # dispatcher.add_error_handler(unknown_cmd_handler)

    # command handlers
    dispatcher.add_handler(start_cmd_handler)
    dispatcher.add_handler(enter_cmd_handler)
    dispatcher.add_handler(save_cmd_handler)
    dispatcher.add_handler(restore_cmd_handler)
    dispatcher.add_handler(quit_cmd_handler)
    dispatcher.add_handler(debug_handler)

    # text handlers
    dispatcher.add_handler(terp_cmd_handler)

    # always add unknown cmd handler last
    dispatcher.add_handler(unknown_cmd_handler)

    #updater.start_polling(poll_interval=2.0, clean=True)
    updater.start_polling(clean=True)
    updater.idle()


if __name__ == '__main__':
    main()
