import json
import subprocess
import sys
import splitstream
import logging


class FrotzbotBackend():
    def __init__(self,
                 arg_frotz_path,
                 arg_game_path,
                 savefile_prefix='',
                 terp_args=['-fm', '-width', '60', '-height', '100']):
        self.log = logging.getLogger('FrotzbotBackend')
        self.log.setLevel(logging.DEBUG)

        if not terp_args:
            self.log.warning('WARNING: NO TERP ARGS SPECIFIED! REMGLK WILL NOT PRODUCE ANY OUTPUT UNTIL FORMAT ARGUMENTS ARE SPECIFIED MANUALLY!')

        self.terp_path = arg_frotz_path
        self.game_path = arg_game_path
        self.savefile_prefix = savefile_prefix
        try:
            self.terp_proc = subprocess.Popen(
                [self.terp_path] + terp_args + [self.game_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                bufsize=0)
        except OSError as err:
            self.log.critical(
                'COULDN\'T RUN INTERPRETER. MAYBE WRONG ARCHITECTURE?',
                exc_info=1
            )
            self.terp_proc = None
            raise err
        else:
            # get iterator over json output stream
            self.json_iter = map(lambda x: json.loads(x.decode('utf-8')),
                                 splitstream.splitfile(self.terp_proc.stdout,
                                                       format="json",
                                                       bufsize=1))

            # interpreter state is defined as
            # an array of windows
            self.windows = []
            # current prompt
            self.prompt = None
            # and current state number
            self.gen = 0

    def process_update(self, json_update, filter_input_echo_str=None):
        # first, refresh windows and input info
        # TODO what TODO with multiple inputs? Is that even possible?
        self.windows = json_update.get('windows', self.windows)
        self.gen = json_update.get('gen', self.gen)

        if 'input' in json_update:
            self.prompt = json_update['input'][0]
        elif 'specialinput' in json_update:
            self.prompt = json_update['specialinput']

        # then, form update update_dict, where key is window id and value
        # is new text
        update_dict = dict()
        for content_update in json_update.get('content', []):
            text = ''
            if 'lines' in content_update:
                lines = [x for x in content_update['lines']
                         if x is not None and 'content' in x]
                for line in lines:
                    line_contents = line['content']
                    for line_content in line_contents:
                        text = text + line_content['text'].replace('\n', ' ')
                    text = text + '\n'
            elif 'text' in content_update:
                lines = [x for x in content_update['text']
                         if (len(x) == 0) or 'content' in x]
                for line in lines:
                    if 'content' in line:
                        line_contents = line['content']

                        # try to filter input echo
                        if filter_input_echo_str:
                            line_contents = [x for x in line_contents
                                             if x.get('style', '') != 'input' or x['text'] != filter_input_echo_str]

                        for line_content in line_contents:
                            text = text + line_content['text']
                    text = text + '\n'
            elif 'clear' in content_update:
                continue
            else:
                text = 'WARNING: UNKNOWN UPDATE TYPE ' + str(content_update)

            update_dict[content_update['id']] = text

            
        # now that we have filled update_dict, refresh window contents
        for window in self.windows:
            window['content_text'] = update_dict.get(
                window['id'],
                window.get('content_text', ''))

    def get_raw(self):
        return self.json_iter.__next__()

    def send_raw(self, text):
        self.terp_proc.stdin.write(text.encode('utf-8'))
        self.terp_proc.stdin.flush()

    def get(self, previous_input=None):
        out_json = self.get_raw()

        self.log.debug("INTERPRETER OUT: %s", str(out_json))

        # check for errors
        if out_json['type'] == 'error':
            return ['INTERPRETER ERROR: ' + out_json.get(
                'message', 'ERROR MESSAGE NOT SET. THIS INTERPRETER STINKS.')]

        self.process_update(out_json, previous_input)
        text_list = [window.get('content_text', '') for window in self.windows]

        if 'specialinput' in out_json:
            # if out_json contains specialinput - we need to
            # show 'file choosing dialog' - simply add text prompting user
            # to enter save name
            text_list.append('ENTER SAVE FILE NAME')

        return text_list

    def send(self, text):
        cmd_json = {'type': self.prompt['type'],
                    'gen': self.gen,
                    'value': text}

        if self.prompt['type'] == 'line':
            # responding to string request requires window id
            cmd_json['window'] = self.prompt['id']
        elif self.prompt['type'] == 'char':
            # responding to char request requires window id
            cmd_json['window'] = self.prompt['id']
        elif self.prompt['type'] == 'fileref_prompt':
            # responding to save/restore dialog
            cmd_json['type'] = 'specialresponse'
            cmd_json['response'] = 'fileref_prompt'
            cmd_json['value'] = self.savefile_prefix + text

        cmd_text = json.dumps(cmd_json)

        self.log.debug("INTERPRETER IN: %s", cmd_text)

        self.send_raw(cmd_text)

    def send_and_receive(self, text):
        self.send(text)
        return self.get(text)

    def __del__(self):
        if self.terp_proc is not None:
            logging.info('KILLING INTERPRETER')
            self.terp_proc.stdout.close()
            self.terp_proc.stdin.close()
            self.terp_proc.stderr.close()
            self.terp_proc.kill()
