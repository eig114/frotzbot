# abstraction layer for dfrotz
# parts for non-blocking communication are taken from
# https://gist.github.com/EyalAr/7915597

# this code is still somewhat shitty...

import queue
import subprocess
import sys
import threading


class DFrotz():
    def __init__(self, arg_frotz_path, arg_game_path):
        self.frotz_path = arg_frotz_path
        self.game_path = arg_game_path
        try:
            self.frotz = subprocess.Popen(
                [self.frotz_path, '-h', '100', '-w', '60', self.game_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                bufsize=0)
        except OSError as e:
            print('Couldn\'t run Frotz. Maybe wrong architecture?')
            sys.exit(0)
        self.queue = queue.Queue()
        self.thread = threading.Thread(
            target=self.enqueue, args=(self.frotz.stdout, self.queue))
        self.thread.daemon = True
        self.thread.start()

        self.err_queue = queue.Queue()
        self.thread = threading.Thread(
            target=self.enqueue, args=(self.frotz.stderr, self.err_queue))
        self.thread.daemon = True
        self.thread.start()

    def enqueue(self, out, queue):
        for char in iter(lambda: out.read(1), b''):
            queue.put(char)
        out.close()

    def send(self, command):
        self.frotz.stdin.write(command.encode('cp1252'))
        self.frotz.stdin.flush()

    def generate_output(self, chars):
        output = ''.join(chars)
        # clean up Frotz' output
        if output.endswith('> >'):
            output = output[:-3]
        elif output.endswith('>'):
            output = output[:-1]
        output = output.replace('\n.\n', '\n\n')
        #output = output.replace(']\n', '\n')
        #output = output.replace('\n) ', '\n')

        return output

    def get(self):
        chars = []
        while True:
            try:
                char = self.queue.get(timeout=1).decode('cp1252')
            except queue.Empty:
                #print('', end='')
                break
            else:
                chars.append(char)
        return self.generate_output(chars)
