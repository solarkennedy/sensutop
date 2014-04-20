#!/usr/bin/env python

import os, sys
import curses
import json
import logging
import threading
import time
import urllib2

DELAY=5


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

class SensuAPIFetcher(threading.Thread):
    def __init__(self, endpoint_name, endpoint_config):
        threading.Thread.__init__(self)
        self.name = endpoint_name
        self.host = endpoint_config['host']
        self.ssl = endpoint_config['ssl']
        self.port = endpoint_config['port']
        self.username = endpoint_config['username']
        self.password = endpoint_config['password']
        self.sensu_events = []
        if self.ssl:
            proto = 'https://'
        else:
            proto = 'http://'
        self.url = proto + self.host + ":" + str(self.port) + '/events?_=' 
        self.event = threading.Event()
        logging.debug("initializing background sensu api fetching for " + self.name)
    def run(self):
        while not self.event.is_set():
            logging.debug("  Fetching " + self.name)
            self.sensu_events = self.get_events()
            logging.debug("     Got " + str(len(self.sensu_events)) + " events!")
            self.event.wait(DELAY)
    def stop(self):
        self.event.set()
    def get_events(self):
        logging.debug("    Fetching " + self.url)
        headers = {'X_REQUESTED_WITH' :'XMLHttpRequest',
           'Accept': 'application/json, text/javascript, */*; q=0.01',}
        request = urllib2.Request(self.url, None, headers)
        if self.username:
            # Need to handle authentication
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, self.url, self.username, self.password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
        else:
            logging.debug("Aparently we dont need basic auth")
        try:
            pagehandle = urllib2.urlopen(request)
            the_page = pagehandle.read()
        except IOError as e:
            raise
            logging.debug("Fetching " + self.url + "Failed: ")
            logging.debug(e)
            return []
        try:
            events = json.loads(the_page)
        except Exception as e:
            logging.debug("Parsing json failed ")
            logging.debug(e)
            raise
            events = []
        return events

class SensuTop(object):
    def __init__(self, screen, config):
        self.config = config
        self.screen = screen
        self.fetchers = {}
        pass
    def get_all_sensu_events(self):
        all_events = []
        for fetcher in self.fetchers.itervalues():
            all_events.extend(fetcher.sensu_events)
        return all_events
    def draw_loop(self):
        (maxY, maxX) = self.screen.getmaxyx()
        while True: 
            self.screen.nodelay(1)
            self.update_screen()
            event = self.screen.getch() 
            if event == ord("q"):
                break
            else: time.sleep(1)
    def update_screen(self): 
        line = 1
        for sensu_event in self.get_all_sensu_events():
            self.draw_event(line, sensu_event)
            line += 1
    def draw_event(self, line_number, sensu_event)
        client = sensu_event['client']
        check = sensu_event['check']
        output = sensu_event['output']
        status = sensu_event['status']
        self.screen.addstr(line_number, 1, client + "\t" + check + "\t" + output)
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
    st.draw_loop()
    # When we are done, gracefully cleanup the background fetcher threads
    st.stop_fetchers()

if __name__ == '__main__':
    # For now, just spit out all messages
    logging.getLogger().setLevel(0)
    curses.wrapper(main)
