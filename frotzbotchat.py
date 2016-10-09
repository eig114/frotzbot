"""This module contains a object representing a chat state for frotzbot"""

import dfrotz
import traceback
import telegram.ext
import re


class FrotzbotChat():
    """Object representing a chat state for frotzbot"""

    def __init__(self, chat_id, config):
        self.chat_id = chat_id
        self.games_dict = config['stories']
        self.interpreter_path = config['interpreter']
        self.interpreter_args = config['interpreter_args']
        self.interpreter = None
        self.reply_markup = None

        self.handle_message = self.cmd_start

    def cmd_start(self, text='/start'):
        result_text = None
        if text != '/start':
            result_text = self.ignore(text)
        else:
            result_text = 'What game would you like to play?'
            entries = list(map(lambda x: [x['name']], self.games_dict))
            self.reply_markup = telegram.ReplyKeyboardMarkup(
                entries,
                resize_keyboard=True,
                one_time_keyboard=True)
            self.handle_message = self.select_game
        return result_text

    def ignore(self, *ignored_args):
        return None
        #return 'ignore_stub'

    def select_game(self, text):
        result_text = None
        try:
            game = next(x for x in self.games_dict
                        if x['name'] == text)
        except StopIteration:
            result_text = 'Dont\'t know this one. Choose another.'
            entries = list(map(lambda x: [x['name']],
                               self.games_dict))
            self.reply_markup = telegram.ReplyKeyboardMarkup(
                entries,
                resize_keyboard=True,
                one_time_keyboard=True)
            self.handle_message = self.select_game
        else:
            self.interpreter = dfrotz.DFrotz(
                self.interpreter_path,
                game['filename'],
                self.interpreter_args)

            result_text = self.interpreter.get()
            if not result_text:
                result_text = '<no output>'

            self.reply_markup = telegram.ReplyKeyboardMarkup(
                [['/enter', '/quit'],
                 ['/start']],
                resize_keyboard=True)
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
            cmds = ['quit']
            cmd_regex = '|'.join(cmds)
            regex = re.compile('^\s*(' + cmd_regex + ')\s*$',
                               re.IGNORECASE)
            match = regex.match(text)
            if match:
                text = 'Use the %s command instead' % ('/' + match.group(1))
            else:
                try:
                    self.interpreter.send(text + '\n')
                except (IOError, BrokenPipeError):
                    traceback.print_exc()
                    text = '<Error during communication with Frotz>'
                else:
                    text = self.interpreter.get()
        return text

    def cmd_enter(self, text='enter'):
        return self.send_to_terp('')

    def cmd_quit(self, text='quit'):
        self.interpreter = None  # TODO force kill interpreter process
        self.handle_message = self.cmd_start
        self.reply_markup = telegram.ReplyKeyboardHide()
        return 'Frotzbot is stopped. Use /start to start a new session'

    def reply(self, bot, update, handler=None, text=None):
        if handler is None:
            handler = self.handle_message

        print(update.message.text)
        reply_text = handler(update.message.text)
        if reply_text:
            bot.sendMessage(
                chat_id=self.chat_id,
                text=reply_text,
                timeout=5.0,
                reply_markup=self.reply_markup)
