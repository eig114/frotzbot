"""This module contains a object representing a chat state for frotzbot"""

import frotzbotterp
import traceback
import telegram.ext
import re
import itertools
import os


def grouper(iterable, n):
    """group ITERABLE by N elements"""
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args)


def is_empty_string(text):
    whitespace_re = re.compile('^\s+$')
    return whitespace_re.match(text)


class FrotzbotChat():
    """Object representing a chat state for frotzbot"""

    def __init__(self, chat_id, config):
        self.chat_id = chat_id
        self.games_dict = config['stories']
        self.interpreter_path = config['interpreter']
        self.interpreter_args = config['interpreter_args']
        self.window_separator = config.get('window_separator', '\n\n')
        self.interpreter = None
        self.reply_markup = None

        self.handle_message = self.cmd_start

    def cmd_start(self, text='/start'):
        result_text = None
        if text != '/start':
            result_text = self.ignore(text)
        else:
            result_text = '<What game would you like to play?>\n\n'
            for game in self.games_dict:
                result_text = result_text + game['name'] + '\n'

            # entries = list(map(lambda x: [x['name']], self.games_dict))
            entries = [[x['name']] for x in self.games_dict]
            self.reply_markup = telegram.ReplyKeyboardMarkup(
                entries, resize_keyboard=True, one_time_keyboard=True)
            self.handle_message = self.select_game
        return result_text

    def ignore(self, *ignored_args):
        return None
        #return 'ignore_stub'

    def select_game(self, text):
        result_text = None
        try:
            game = next(x for x in self.games_dict if x['name'] == text)
        except StopIteration:
            result_text = 'Dont\'t know this one. Choose another.'
            entries = list(map(lambda x: [x['name']], self.games_dict))
            self.reply_markup = telegram.ReplyKeyboardMarkup(
                entries, resize_keyboard=True, one_time_keyboard=True)
            self.handle_message = self.select_game
        else:
            terp_path = game.get('interpreter', self.interpreter_path)
            terp_args = game.get('interpreter_args', self.interpreter_args)
            game_file = game['filename']

            self.interpreter = frotzbotterp.FrotzbotBackend(
                terp_path,
                game_file,
                'savedata' + os.path.sep + str(self.chat_id) + '_',
                terp_args)

            result_texts = [x for x in self.interpreter.get()
                            if not is_empty_string(x)]
            result_text = self.window_separator.join(result_texts)
            if not result_text:
                result_text = '<no output>'

            self.reply_markup = telegram.ReplyKeyboardMarkup(
                [['/enter', '/quit'], ['/start']], resize_keyboard=True)
            self.handle_message = self.send_to_terp
        return result_text

    def save(self, text):
        return 'save_stub'

    def restore(self, text):
        return 'restore_stub'

    def send_to_terp(self, text):
        if self.interpreter is None:
            text = self.cmd_quit()
        else:
            # check for special commands first
            # deprecated_cmds = ['save', 'restore', 'quit']
            deprecated_cmds = ['quit']
            cmd_regex = '|'.join(deprecated_cmds)
            regex = re.compile('^\s*(' + cmd_regex + ')\s*$',
                               re.IGNORECASE)
            match = regex.match(text)
            if match:
                text = 'Use the %s command instead' % ('/' + match.group(1))
            else:
                try:
                    result_texts = self.interpreter.send_and_receive(text)
                except (IOError, BrokenPipeError):
                    traceback.print_exc()
                    text = '<Error during communication with interpreter>'
                else:
                    # response might contain only whitespaces.
                    # since bots can't send 'empty' messages,
                    # assume it means 'press anykey to continue'
                    result_texts = [x for x in result_texts
                                    if not is_empty_string(x)]
                    text = self.window_separator.join(result_texts)
                    if not text:
                        text = '<press /enter to continue>'
                    #elif text.endswith('\n>\n') and len(text) > 3:
                    # try to remove input prompt
                    #    text = text[:-3]

        return text

    def cmd_enter(self, text='enter'):
        if self.interpreter is None:
            text = self.cmd_quit()
        elif self.interpreter.prompt is None:
            # Wait, what?
            text = 'WARNING: You did something really unexpected here. '
            text = text + 'I\'m gonna ignore your input and just past '
            text = text + 'current output from interpreter.\n'
            text = text + 'No promises though. '
            text = text + 'Demons might fly out of my nose for all I know.\n'

            result_texts = [x for x in self.interpreter.get()
                            if not is_empty_string(x)]
            result_text = self.window_separator.join(result_texts)
            if not result_text:
                result_text = '<no output>'

            text = text + result_text
        else:
            # reasonable guess. If 'terp expects char, it's a space character
            # if it expects line, it's an empty string
            text = self.send_to_terp(' ')
        return text

    def cmd_quit(self, text='quit'):
        self.interpreter = None  # TODO force kill interpreter process
        self.handle_message = self.cmd_start
        self.reply_markup = telegram.ReplyKeyboardHide()
        return '<No active games. /start a new session?>'

    def reply(self, bot, update, handler=None, text=None):
        if handler is None:
            handler = self.handle_message

        # print(update.message.text)
        reply_text = handler(update.message.text)

        if reply_text:
            # divide our message by chunks of 4096 chars
            # and send them, except empty string chunks
            max_len = 4096
            msgs = filter(lambda x: not is_empty_string(x),
                          map(lambda x: ''.join(
                              filter(lambda y: y is not None, x)),
                              grouper(reply_text, max_len)))
            for msg in msgs:
                bot.sendMessage(
                    chat_id=self.chat_id,
                    text=msg,
                    timeout=5.0,
                    reply_markup=self.reply_markup)
