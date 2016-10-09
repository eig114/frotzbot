#!/bin/python2

import telegram.ext
import dfrotz
import traceback
import json

bot_terps = dict()
config = dict()


def debug(bot, update):
    try:
        game_list = config['stories']
        entries = list(map(lambda x: [x['name']], game_list))
        keyboard = telegram.ReplyKeyboardMarkup(
            entries, resize_keyboard=True, one_time_keyboard=True)

        bot.sendMessage(
            chat_id=update.message.chat_id,
            text='Choose your destiny:',
            timeout=5.0,
            reply_markup=keyboard)
    except Exception:
        traceback.print_exc()


def start(bot, update):
    try:
        global bot_terps
        global config

        if bot in bot_terps:
            del bot_terps[bot]

        text = 'What game would you like to play?\n'
        game_list = config['stories']
        entries = list(map(lambda x: [x['name']], game_list))
        keyboard = telegram.ReplyKeyboardMarkup(
            entries, resize_keyboard=True, one_time_keyboard=True)

        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=text,
            timeout=5.0,
            reply_markup=keyboard)
    except Exception:
        traceback.print_exc()


def start_terp(bot, update):
    global bot_terps
    global config
    try:
        print('starting Frotz for %d' % update.message.chat_id)
        frotz_path = config['interpreter']
        try:
            game = next(x for x in config['stories']
                        if x['name'] == update.message.text)
        except StopIteration:
            text = 'Dont\t know this one. Choose another.'
            game_list = config['stories']
            entries = list(map(lambda x: [x['name']], game_list))
            keyboard = telegram.ReplyKeyboardMarkup(
                entries, resize_keyboard=True, one_time_keyboard=True)
        else:
            new_terp = dfrotz.DFrotz(frotz_path, game['filename'])
            bot_terps[bot] = new_terp

            text = new_terp.get()
            if not text:
                text = '<no output>'

            keyboard = telegram.ReplyKeyboardMarkup(
                [['/enter']], resize_keyboard=True)

        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=text,
            timeout=5.0,
            reply_markup=keyboard)
    except Exception:
        traceback.print_exc()


def enter(bot, update):
    try:
        global bot_terps
        terp = bot_terps[bot]
        terp.send('\n')
        text = terp.get()
        if not text:
            text = '<no output>'
        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=text,
            timeout=5.0)
    except Exception:
        traceback.print_exc()


def send_to_terp(bot, update, terp):
    try:
        print(update.message.text)
        sent_successfully = True
        try:
            terp.send(update.message.text + '\n')
        except IOError:
            traceback.print_exc()
            sent_successfully = False

        if sent_successfully:
            text = terp.get()
            if not text:
                text = '<no output>'
        else:
            text = '<Error during communication with Frotz. Is it closed? >'
        bot.sendMessage(chat_id=update.message.chat_id, text=text, timeout=5.0)
    except Exception:
        traceback.print_exc()


def handle_text(bot, update):
    try:
        global bot_terps
        if bot in bot_terps:
            terp = bot_terps[bot]
            send_to_terp(bot, update, terp)
        else:
            start_terp(bot, update)
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
