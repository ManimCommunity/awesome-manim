#!/usr/bin/python3

# Copyright (C) 2020  Stefan Vargyas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys, os
from dotenv import load_dotenv
load_dotenv()

program = os.path.basename(sys.argv[0])
verdate = '0.1 2020-07-25 11:23' # $ date +'%F %R'

def joinln(args):
    return "\n".join(map(str, args))

def write(where, msg, args):
    s = isinstance(msg, str)
    l = isinstance(msg, list) or \
        isinstance(msg, tuple)
    n = len(args)
    if l:
        msg = joinln(msg)
    elif not s:
        msg = str(msg)
    if s and n:
        msg = msg % args
    elif not s and n:
        msg += "\n" + joinln(args)
    where.write(msg)

def cout(msg = "", *args):
    write(sys.stdout, msg, args)

def cerr(msg = "", *args):
    write(sys.stderr, msg, args)

def error(msg, *args):
    if len(args):
        msg = msg % args
    cerr("%s: error: %s\n", program, msg)
    sys.exit(1)

def warn(msg, *args):
    if len(args):
        msg = msg % args
    cerr("%s: warning: %s\n", program, msg)

def print_list(lst, name = None, ln = False):
    if len(lst):
        if ln: cout('\n')
        if name: cout('%s:\n', name)
        cout('%s\n', '\n'.join(lst))

class Text:

    from unicodedata import normalize

    # https://stackoverflow.com/a/29247821/8327971

    @staticmethod
    def normalize_casefold(text):
        return Text.normalize("NFKD", text.casefold())

    @staticmethod
    def casefold_equal(text1, text2):
        return \
            Text.normalize_casefold(text1) == \
            Text.normalize_casefold(text2)

class Service:

    from googleapiclient.discovery import build

    def __init__(self, max_results, app_key):
        self.youtube = Service.build(
            'youtube', 'v3', developerKey = app_key)
        self.max_results = max_results

    def search_term(self, term, type = None):
        resp = self.youtube.search().list(
            q = term,
            type = type,
            part = 'id,snippet',
            fields = 'items(id,snippet(title))',
            maxResults = self.max_results
        ).execute()

        items = resp['items']
        assert len(items) <= self.max_results

        res = [], [], []

        for item in items:
            k = item['id']['kind']
            if k == 'youtube#video':
                i, k = 0, 'videoId'
            elif k == 'youtube#channel':
                i, k = 1, 'channelId'
            elif k == 'youtube#playlist':
                i, k = 2, 'playlistId'
            else:
                assert False

            res[i].append('%s: %s' % (
                item['id'][k], item['snippet']['title']))

        return res

    def find_channel_by_custom_url(self, url):
        resp = self.youtube.search().list(
            q = url,
            part = 'id',
            type = 'channel',
            fields = 'items(id(kind,channelId))',
            maxResults = self.max_results
        ).execute()

        items = resp['items']
        assert len(items) <= self.max_results

        ch = []
        for item in items:
            assert item['id']['kind'] == 'youtube#channel'
            ch.append(item['id']['channelId'])

        if not len(ch):
            return None

        resp = self.youtube.channels().list(
            id = ','.join(ch),
            part = 'id,snippet',
            fields = 'items(id,snippet(customUrl))',
            maxResults = len(ch)
        ).execute()

        items = resp['items']
        assert len(items) <= len(ch)

        for item in items:
            cust = item['snippet'].get('customUrl')
            if cust is not None and \
                Text.casefold_equal(cust, url):
                assert item['id'] is not None
                return item['id']

        return None

    def find_channel_by_user_name(self, user):
        resp = self.youtube.channels().list(
            forUsername = user,
            part = 'id',
            fields = 'items(id)',
            maxResults = 1
        ).execute()

        # stev: 'items' may be absent
        items = resp.get('items', [])
        assert len(items) <= 1

        for item in items:
            assert item['id'] is not None
            return item['id']

        return None

    def query_custom_url(self, channel):
        resp = self.youtube.channels().list(
            id = channel,
            part = 'snippet',
            fields = 'items(snippet(customUrl))',
            maxResults = 1
        ).execute()

        # stev: 'items' may be absent
        items = resp.get('items', [])
        assert len(items) <= 1

        for item in items:
            return item['snippet'].get('customUrl')
        return None

def service_func(func):
    from googleapiclient.errors import HttpError
    from google.auth.exceptions import GoogleAuthError
    from functools import wraps

    @wraps(func)
    def wrapper(*arg, **kwd):
        try:
            return func(*arg, **kwd)
        except HttpError as e:
            error('HTTP error: %s', e)
        except GoogleAuthError as e:
            error('Google auth error: %s', e)

    return wrapper

class Act:

    @staticmethod
    @service_func
    def search_term(opts):
        service = Service(
            opts.max_results,
            opts.app_key)

        v, c, p = service.search_term(
            opts.search_term,
            opts.type)

        h = not opts.type or None

        print_list(v, h and 'Videos')
        print_list(c, h and 'Channels', bool(v))
        print_list(p, h and 'Playlists', bool(v) or bool(c))

    @staticmethod
    @service_func
    def find_channel(opts, name):
        service = Service(
            opts.max_results,
            opts.app_key)

        n = name.lower() \
                .replace(' ', '_')
        a = getattr(opts, n)
        c = getattr(service, 'find_channel_by_' + n)(a)

        if c is None:
            error('%s "%s": no associated channel found',
                name, a)
        else:
            cout('%s\n', c)

    find_channel_by_custom_url = \
        lambda opts: Act.find_channel(opts, 'custom URL')

    find_channel_by_user_name = \
        lambda opts: Act.find_channel(opts, 'user name')

    @staticmethod
    @service_func
    def query_channel_custom_url(opts):
        service = Service(
            opts.max_results,
            opts.app_key)

        u = service.query_custom_url(
            opts.channel_url)

        if u is not None:
            cout("%s\n", u)

def options():
    from argparse import ArgumentParser, HelpFormatter

    class Formatter(HelpFormatter):

        def _format_action_invocation(self, act):
            # https://stackoverflow.com/a/31124505/8327971
            meta = self._get_default_metavar_for_optional(act)
            return '|'.join(act.option_strings) + ' ' + \
                self._format_args(act, meta)

    p = ArgumentParser(
            formatter_class = Formatter,
            add_help = False)
    p.error = error

    STR = 'STR'
    NUM = 'NUM'

    def uint(arg):
        r = int(arg)
        if r <= 0:
            raise ValueError()
        return r

    # stev: action options:
    g = p.add_mutually_exclusive_group(required = True)
    g.add_argument('-s', '--search-term',
        help = 'do search for the given term',
        metavar = STR, default = None)
    g.add_argument('-c', '--custom-url',
        help = 'do find the channel ID associated to the given custom URL',
        metavar = STR, default = None)
    g.add_argument('-u', '--user-name',
        help = 'do find the channel ID associated to the given user name',
        metavar = STR, default = None)
    g.add_argument('-l', '--channel-url',
        help = 'do query the custom URL associated to the given channel',
        metavar = STR, default = None)
    # stev: dependent options:
    p.add_argument('-t', '--type', choices = ('channel', 'playlist', 'video'),
        help = 'restrict the search query to only retrieve the specified type of resource',
        default = None)
    p.add_argument('-m', '--max-results', type = uint,
        help = 'set the API endpoint parameter `maxResults\' to the given number (default: 10)',
        metavar = NUM, default = 10)
    p.add_argument('-k', '--app-key',
        help = 'YouTube Data API application key (default: $YOUTUBE_DATA_APP_KEY)',
        metavar = STR, default = None)
    # stev: info options:
    p.add_argument('-v', '--version',
        action = 'version', version = '%(prog)s: version ' + verdate,
        help = 'print version numbers and exit')
    p.add_argument('-h', '--help',
        help = 'display this help info and exit',
        action = 'help')

    a = p.parse_args()

    if a.app_key is None:
        a.app_key = os.getenv('YOUTUBE_DATA_APP_KEY')
        if a.app_key is None:
            error('application key not given')

    s = bool(a.search_term)
    c = bool(a.custom_url)
    u = bool(a.user_name)
    l = bool(a.channel_url)
    assert s + c + u + l == 1

    if a.search_term:
        a.action = Act.search_term
    elif a.custom_url:
        a.action = Act.find_channel_by_custom_url
    elif a.user_name:
        a.action = Act.find_channel_by_user_name
    elif a.channel_url:
        a.action = Act.query_channel_custom_url
    else:
        assert False

    return a

def main():
    opt = options()
    opt.action(opt)

if __name__ == '__main__':
    main()