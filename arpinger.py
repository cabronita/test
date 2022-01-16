#!/usr/bin/env python3

from argparse import ArgumentParser
from datetime import datetime
from platform import system
from random import randrange
from time import sleep
import logging
import os
import pickle
import subprocess

parser = ArgumentParser()
parser.add_argument('target', help='target IP address', metavar='IP', type=str)
parser.add_argument('-l', '--logfile', default='arpinger.log', help='log filename', metavar='FILE')
parser.add_argument('-o', '--output', default='report.html', help='report file', metavar='FILE')
parser.add_argument('-f', '--full-output', action='store_false', help='show full report, rather than last 20 events')
args = parser.parse_args()

target = args.target
logfile = args.logfile
report_file = args.output
full_output = args.full_output

logging.basicConfig(filename=logfile, filemode='w', encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


class State:
    def __init__(self):
        self.time = get_timestamp()
        self.online = is_online()

    def __repr__(self):
        return f"{self.time.strftime('%a %H:%M')} {'UP' if self.online else 'DOWN'}"


def get_timestamp():
    return datetime.now().replace(second=0, microsecond=0)


def is_online():
    if system() == 'Windows':
        return True if randrange(50) == 0 else False
    else:
        interface = subprocess.run(['/usr/sbin/ip', '-oneline', 'route', 'get', target],
                                   capture_output=True, text=True).stdout.split()[2]
        command = ['/usr/sbin/arping', '-qf', '-I', interface, '-w', '3', target]
        return True if subprocess.run(command).returncode == 0 else False


def report():
    background = 'palegreen' if not state_history or state_history[-1].online == True else 'pink'
    html = []
    html.append(f"<html><meta http-equiv='refresh' content='60' ><body style='background-color:{background};''><h1>")
    limit = -21 if full_output else 0
    for i in state_history[-1:limit:-1]:
        html.append(str(i) + '\n<br>')
    html.append('\n</h1></body></html>')
    try:
        logging.debug(f"Writing report")
        with open(report_file, 'w') as f:
            f.writelines(html)
    except Exception as err:
        logging.debug(f"Failed to write report - {err}")


def load_state_history():
    if os.path.isfile(state_history_file):
        with open(state_history_file, 'rb') as f:
            logging.debug(f"Loading state history from {state_history_file}")
            return pickle.load(f)
    else:
        logging.debug("No state history found")
        return []


def save_state_history():
    if os.path.isfile(state_history_file):
        os.remove(state_history_file)
    with open(state_history_file, 'wb') as f:
        pickle.dump(state_history, f)


def update_history(state):
    if not state_history:
        state_history.append(state)
        save_state_history()
        return True
    else:
        previous_state = state_history[-1]
        if state.online != previous_state.online:
            state_history.append(state)
            save_state_history()
            return True


if __name__ == '__main__':
    logging.debug("Starting")
    state = State()
    state_history_file = f"{target}.dat"
    state_history = load_state_history()
    report()

    while True:
        timestamp = get_timestamp()
        if state.time != timestamp:
            if update_history(state):
                report()
            state = State()
        else:
            if not state.online:
                state = State()
        sleep(1)
