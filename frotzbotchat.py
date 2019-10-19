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

    def __init__(self, bot, chat_id, config):
        self.bot = bot
        self.chat_id = chat_id
        self.games_dict = config['stories']
        self.interpreter_path = config['interpreter']
        self.interpreter_args = config.get('interpreter_args', [])
        self.window_separator = config.get('window_separator', '\n\n')
        self.terp_list = config.get('interpreter_list')
        self.interpreter = None
        self.reply_markup = None

        self.handle_message = self.cmd_start

    def cmd_start(self, message):
        text = message.text
        result_text = None
        if not(re.compile('^/start(@.*)?$').match(text)):
            result_text = None
        elif self.interpreter is not None:
            result_text = '[Are you sure you want to restart? (y/n)]'
            self.handle_message = self.restart_dialog
        else:
            result_text = self.newgame_dialog()
        return result_text

    def newgame_dialog(self):
        result_text = '[What game would you like to play?]\n\n'
        for game in self.games_dict:
            result_text = result_text + game['name'] + '\n'

        # entries = list(map(lambda x: [x['name']], self.games_dict))
        entries = [[x['name']] for x in self.games_dict]
        self.reply_markup = telegram.ReplyKeyboardMarkup(
            entries, resize_keyboard=True, one_time_keyboard=True)
        self.handle_message = self.select_game
        return result_text

    def restart_dialog(self, message):
        text = message.text
        result_text = None
        if text == 'y' or text == 'yes':
            result_text = '[Alright then.]\n' + self.newgame_dialog()
        elif text == 'n' or text == 'no':
            result_text = '[Never mind]'
            self.handle_message = self.send_to_terp  # Return to game
        else:
            result_text = '[yes or no, please]'
        return result_text

    def select_game_text(self, text):
        result_text = None
        try:
            game = next(x for x in self.games_dict if x['name'] == text)
        except StopIteration:
            result_text = '[Don\'t know this one. Choose another]'
            entries = [[x['name']] for x in self.games_dict]
            self.reply_markup = telegram.ReplyKeyboardMarkup(
                entries, resize_keyboard=True, one_time_keyboard=True)
            self.handle_message = self.select_game
        else:
            terp_path = game.get('interpreter', self.interpreter_path)
            terp_args = game.get('interpreter_args', self.interpreter_args)
            game_file = game['filename']

            try:
                self.interpreter = frotzbotterp.FrotzbotBackend(
                    terp_path,
                    game_file,
                    'savedata' + os.path.sep + str(self.chat_id) + '_',
                    terp_args)
            except OSError:
                result_text = '[Could not start interpreter]'
                self.handle_message = self.cmd_start
                self.reply_markup = telegram.ReplyKeyboardMarkup(
                    [['/start']],
                    resize_keyboard=True)
            else:
                result_text = self.window_separator.join(self.interpreter.get())
                if is_empty_string(result_text):
                    result_text = '[no output]'

                self.reply_markup = telegram.ReplyKeyboardMarkup(
                    [['/enter', '/space', '/quit'], ['/start']],
                    resize_keyboard=True)
                self.handle_message = self.send_to_terp
        return result_text

    def select_game_file(self, document):
        file = self.bot.getFile(document.file_id)
        filename = 'downloaded_stories' + os.path.sep + str(self.chat_id) + '_' + document.file_name
        file.download(filename)

        self.handle_message = lambda msg: self.select_terp(filename, msg)
        entries = [[x['name']] for x in self.terp_list]
        self.reply_markup = telegram.ReplyKeyboardMarkup(
            entries, resize_keyboard=True)
        result_text = "[Select interpreter]"
        for terp in self.terp_list:
            result_text = result_text + '\n' + terp['name']

        return result_text

    def select_game(self, message):
        text = message.text
        document = message.document

        if (document is None):
            return self.select_game_text(text)
        else:
            return self.select_game_file(document)

    def select_terp(self, filename, message):
        text = message.text

        try:
            terp = next(x for x in self.terp_list if x['name'] == text)
        except StopIteration:
            result_text = '[Don\'t know this one. Choose another]'
            entries = [[x['name']] for x in self.terp_list]
            self.reply_markup = telegram.ReplyKeyboardMarkup(
                entries, resize_keyboard=True, one_time_keyboard=True)
            self.handle_message = lambda msg: self.select_terp(filename, msg)
        else:
            try:
                self.interpreter = frotzbotterp.FrotzbotBackend(
                    terp['path'],
                    filename,
                    'savedata' + os.path.sep + str(self.chat_id) + '_',
                    self.interpreter_args)
            except OSError:
                result_text = '[Could not start interpreter]'
                self.handle_message = self.cmd_start
                self.reply_markup = telegram.ReplyKeyboardMarkup(
                    [['/start']],
                    resize_keyboard=True)
            else:
                result_text = self.window_separator.join(self.interpreter.get())
                if is_empty_string(result_text):
                    result_text = '[no output]'

                self.reply_markup = telegram.ReplyKeyboardMarkup(
                    [['/enter', '/space', '/quit'], ['/start']],
                    resize_keyboard=True)
                self.handle_message = self.send_to_terp
        return result_text

    def send_to_terp(self, message):
        # Yeah, I'm lazy like that
        if (isinstance(message, str)):
            text = message
        else:
            text = message.text

        if self.interpreter is None:
            text = self.cmd_quit()
        elif self.interpreter.prompt is None:
            text = '[WARNING: interpreter returned valid response, but no input prompt. Posssibly wrong interpreter was chosen]'

            try:
                result_text = self.window_separator.join(self.interpreter.get())
                if is_empty_string(result_text):
                    result_text = self.cmd_quit()
            except (StopIteration):
                result_text = self.cmd_quit()

            text = text + '\n' + result_text
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
                    text = '[Error during communication with interpreter]'
                else:
                    # response might contain only whitespaces.
                    # since bots can't send 'empty' messages,
                    # assume it means 'press anykey to continue'
                    text = self.window_separator.join(result_texts)
                    if is_empty_string(text):
                        text = '[press /enter to continue]'

        return text

    def cmd_enter(self, message=None):
        if self.interpreter is None:
            text = self.cmd_quit()
        elif self.interpreter.prompt is None:
            text = '[WARNING: interpreter returned valid response, but no input prompt. Posssibly wrong interpreter was chosen]\n' + self.cmd_quit()
        elif self.interpreter.prompt['type'] == 'char':
            text = self.send_to_terp('return')
        else:
            text = self.send_to_terp('\n')
        return text

    def cmd_space(self, message=None):
        if self.interpreter is None:
            text = self.cmd_quit()
        elif self.interpreter.prompt is None:
            text = '[WARNING: interpreter returned valid response, but no input prompt. Posssibly wrong interpreter was chosen]\n' + self.cmd_quit()
        else:
            text = self.send_to_terp(' ')
        return text

    def cmd_quit(self, message=None):
        self.interpreter = None
        self.handle_message = self.cmd_start
        self.reply_markup = telegram.ReplyKeyboardRemove()
        return '[No active games. /start a new session?]'

    def reply(self, update, handler=None, text=None):
        if handler is None:
            handler = self.handle_message

        # print(update.message.text)
        reply_text = handler(update.message)

        if reply_text:
            # divide our message by chunks of 4096 chars
            # and send them, except empty string chunks
            max_len = 4096
            msgs = map(lambda x: ''.join(filter(lambda y: y is not None, x)),
                       grouper(reply_text, max_len))
            msg_strings = [x for x in msgs
                           if not is_empty_string(x)]
            for msg in msg_strings:
                self.bot.sendMessage(
                    chat_id=self.chat_id,
                    text=msg,
                    timeout=5.0,
                    parse_mode='HTML',
                    reply_markup=self.reply_markup)
            return msg_strings
        else:
            return []
