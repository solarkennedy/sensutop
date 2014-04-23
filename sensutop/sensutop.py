#!/usr/bin/env python

import os, sys
import curses
import json
import logging
import threading
import time
import urllib2

API_FETCH_DELAY=30

from sensuapifetcher import *

def load_sensutop_configfile(filename):
    config = {}
    if os.path.isfile(filename):
        try:
            config = json.load(open(filename, 'r'))
            logging.debug('Loading config from ' + filename)
        # TODO: Be better about exceptions. Fail when invalid json
        except:
            logging.debug('Loading ' + filename + ' failed.')
    return config

def load_sensutop_defaults():
    localhost_api_endpoint = { 'localhost': {
                                 'username': None,
                                 'password': None,
                                 'ssl': False,
                                 'host': 'localhost',
                                 'port': 4567,
                                }
                             }
    default_config = {}
    default_config['api_endpoints'] = localhost_api_endpoint
    return default_config

def load_sensutop_config():
    # Load default values
    default_values = load_sensutop_defaults()
    config = default_values

    # Read the global config in /etc/sensutop.json
    system_defaults = load_sensutop_configfile('/etc/sensutop.json')
    config.update(system_defaults)

    # Load the config from the user's homedir, .sensutop.json
    user_config = load_sensutop_configfile( os.path.expanduser('~') + '/.sensutop.json')
    config.update(user_config)

    logging.debug("Our final config is: ")
    logging.debug(config)
    return config

class SensuTop(object):
    def __init__(self, screen, config):
        self.config = config
        self.screen = screen
        self.fetchers = {}
        curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        pass
    def get_relevant_sensu_events(self, quantity=10):
        return self.get_all_sensu_events()[:quantity]
    def get_all_sensu_events(self):
        all_events = []
        for fetcher in self.fetchers.itervalues():
            all_events.extend(fetcher.sensu_events)
        return all_events
    def draw_loop(self):
        (maxY, maxX) = self.screen.getmaxyx()
        while True: 
            self.screen.clear()
            self.screen.nodelay(1)
            self.draw_header()
            self.update_screen()
            event = self.screen.getch() 
            if event == ord("q"):
                break
            else: time.sleep(1)
    def draw_header(self):
        self.screen.addstr(0, 0, " SensuTop", curses.color_pair(10))
    def update_screen(self): 
        line = 1
        max_showable_events = self.screen.getmaxyx()[0] - 1
        logging.debug("This screen size only allows us to show " + str(max_showable_events) + " events")
        for sensu_event in self.get_relevant_sensu_events(max_showable_events):
            self.draw_event(line, sensu_event)
            line += 1
    def draw_event(self, line_number, sensu_event):
        status = sensu_event['status']
        event_string = self.format_event_for_output(sensu_event)
        color_pair = self.choose_color(sensu_event)
        logging.debug("Putting something on line " + str(line_number) + ". Color pair: " + str(color_pair) + ". String: " + event_string)
        self.screen.addstr(line_number, 1, event_string, curses.color_pair(color_pair))
    def format_event_for_output(self, sensu_event):
        # TODO Columns and stuff
        max_width = self.screen.getmaxyx()[1] - 1
        client = sensu_event['client']
        check = sensu_event['check']
        output = sensu_event['output']
        event_string = client + "\t" + check + "\t" + output
        event_string = event_string[:max_width]
        return event_string

    def choose_color(self, sensu_event):
        if sensu_event['status'] == 0:
            return 10
        elif sensu_event['status'] == 1:
            return 1
        elif sensu_event['status'] == 2:
            return 2
        else:
            return 3
    def start_fetchers(self):
        for endpoint_name, endpoint_config in self.config['api_endpoints'].iteritems():
            self.fetchers[endpoint_name] = SensuAPIFetcher(endpoint_name, endpoint_config)
            self.fetchers[endpoint_name].start()
    def stop_fetchers(self):
        for endpoint_name in self.config['api_endpoints']:
            logging.debug("Stopping background fetcher for " + endpoint_name)
            self.fetchers[endpoint_name].stop()
    

def main(stdscr):
    config = load_sensutop_config()
    st = SensuTop(stdscr, config)
    # Go ahead and start fetching sensu events
    st.start_fetchers()
    # Don't wait, go ahead and start the gui
    time.sleep(0)
    st.draw_loop()
    # When we are done, gracefully cleanup the background fetcher threads
    st.stop_fetchers()

if __name__ == '__main__':
    logging.getLogger().setLevel(0)
    logging.basicConfig(filename='sensutop.log',level=logging.DEBUG)
    curses.wrapper(main)
