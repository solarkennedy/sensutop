#!/usr/bin/env python

import os, sys
import curses
import json
import logging
import threading
import time
import urllib2

API_FETCH_DELAY=30

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
            self.event.wait(API_FETCH_DELAY)
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

