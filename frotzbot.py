#!/usr/bin/python3

# Frotzbot - a telegram bot to play interactive fiction via
# external interpreter. Interpreters need to be compiled against remglk
# library (https://github.com/erkyrath/remglk)
# Idea (and some of the code) taken from https://github.com/sneaksnake/z5bot

import telegram.ext
import json
import frotzbotchat
import logging

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


def on_error(bot, update, error):
    logger = logging.getLogger(__name__)
    logger.warn('Update %r caused error %r!' % (update, error))
    print(error)


def reload_conf(bot, update, conf_path):
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


def start(bot, update):
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_start)
    log_dialog(update.message, response_msgs)


def enter(bot, update):
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_enter)
    log_dialog(update.message, response_msgs)


def space(bot, update):
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_enter)
    log_dialog(update.message, response_msgs)


def handle_text(bot, update):
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update)
    log_dialog(update.message, response_msgs)


def handle_file(bot, update):
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update)
    log_dialog(update.message, response_msgs)


def quit_interpreter(bot, update):
    chat = get_chat(bot, update.message.chat_id)
    response_msgs = chat.reply(update, chat.cmd_quit)
    log_dialog(update.message, response_msgs)


def unknown_cmd(bot, update):
    text = '[I beg your pardon?]'
    bot.sendMessage(chat_id=update.message.chat_id, text=text)
    log_dialog(update.message, [text])


def unsupported(bot, update):
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
    updater = telegram.ext.Updater(config['api_key'])
    dispatcher = updater.dispatcher

    # set up message handlers
    start_cmd_handler = telegram.ext.CommandHandler('start', start)
    enter_cmd_handler = telegram.ext.CommandHandler('enter', enter)
    space_cmd_handler = telegram.ext.CommandHandler('space', space)
    quit_cmd_handler = telegram.ext.CommandHandler('quit', quit_interpreter)
    reload_handler = telegram.ext.CommandHandler(
        'reload_conf', lambda b, u: reload_conf(b, u, config_path))
    terp_cmd_handler = telegram.ext.MessageHandler([telegram.ext.Filters.text],
                                                   handle_text)
    file_handler = telegram.ext.MessageHandler(
        [telegram.ext.Filters.document], handle_file)

    unknown_cmd_handler = telegram.ext.MessageHandler(
        [telegram.ext.Filters.command], unknown_cmd)

    # error handlers
    dispatcher.add_error_handler(on_error)

    # command handlers
    dispatcher.add_handler(start_cmd_handler)
    dispatcher.add_handler(enter_cmd_handler)
    dispatcher.add_handler(space_cmd_handler)
    dispatcher.add_handler(quit_cmd_handler)
    dispatcher.add_handler(reload_handler)

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
