#!/usr/bin/env python3

from argparse import ArgumentParser
from datetime import datetime, timedelta
from platform import system
from random import randrange
import logging
import os
import pickle
import subprocess
import time

parser = ArgumentParser()
parser.add_argument('target', help='target IP', metavar='IP address', type=str)
parser.add_argument('-o', '--output', default='report.txt', help='report file', metavar='FILE')
parser.add_argument('-t', '--timeout', default='3', help='arping timeout', metavar='SECONDS', type=int)
args = parser.parse_args()

target = args.target
timeout = args.timeout
output_file = args.output
state = {}
state_history_file = "state_history.dat"

logging.basicConfig(filename='main.log', encoding='utf-8', datefmt='%x %X', level=logging.DEBUG)


def get_state():
    if system() == 'Windows':
        return 'UP' if randrange(40) == 0 else 'DOWN'
    else:
        interface = subprocess.run(["/usr/sbin/ip", "-oneline", "route", "get", target],
                                   capture_output=True, text=True).stdout.split()[2]
        command = ["/usr/sbin/arping", "-qf", "-I", interface, "-w", str(timeout), target]
        return_code = subprocess.run(command).returncode
        return 'UP' if return_code == 0 else 'DOWN'


def load_state_history():
    if os.path.isfile(state_history_file):
        with open(state_history_file, "rb") as f:
            state_history = pickle.load(f)
            return state_history
    else:
        return {}


def save_state_history():
    if os.path.isfile(state_history_file):
        os.remove(state_history_file)
    with open(state_history_file, "wb") as f:
        pickle.dump(state_history, f)


def update_state_history():
    if len(state_history) == 0:
        state_history.update(state)
    else:
        previous_timestamp = sorted(state_history)[-1]
        previous_state = state_history[previous_timestamp]
        if next(iter(state.values())) != previous_state:
            state_history.update(state)
    save_state_history()


def report():
    report_text = []
    for timestamp in sorted(state_history, reverse=True):
        report_text.append(f"{timestamp.strftime('%a %H:%M')} {state_history[timestamp]}\n")
    try:
        with open(output_file, "w") as f:
            f.writelines(report_text)
    except Exception as e:
        logging.info(e)
        print("Failed to save history. Will retry later.")


if __name__ == "__main__":
    state_history = load_state_history()
    report()
    while True:
        timestamp = datetime.now().replace(second=0, microsecond=0)
        if timestamp not in state:  # either first run of first run for the minute
            if state:  # first run
                update_state_history()
                report()
            state = {timestamp: get_state()}
            logging.debug(f"{datetime.now().strftime('%a %X')} {state[timestamp]}")
        else:  # subsequent runs
            if state[timestamp] == 'DOWN':
                state = {timestamp: get_state()}
                logging.debug(f"{datetime.now().strftime('%a %X')} {state[timestamp]}")
                if state[timestamp] == 'UP':
                    logging.warning(f"{datetime.now().strftime('%a %X')} changed from DOWN to UP")
        time.sleep(1)
