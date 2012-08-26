# -*- coding: utf-8 -*-
###
# Copyright (c) 2012, spline
# All rights reserved.
#
#
###

import urllib2
import re
from BeautifulSoup import BeautifulSoup
import collections
import string

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Soccer')

@internationalizeDocstring
class Soccer(callbacks.Plugin):
    """Add the help for "@plugin help Soccer" here
    This should describe *how* to use this plugin."""
    threaded = True

    def _b64decode(self, string):
        """Returns base64 decoded string."""
        import base64
        return base64.b64decode(string)

    ####################
    # Public Functions #
    ####################
    
    def soccer(self, irc, msg, args, optleague):
        """[league]
        Display live/completed scores for various leagues.
        """
        
        leagues = { 'MLS':'usa.1', 'EPL':'eng.1', 'LaLiga':'spa.1',
                    'SerieA':'ita.1', 'Bundesliga':'ger.1', 'Ligue1':'fra.1',
                    'Eredivise':'ned.1', 'LigaMX':'mex.1'
                 }
        
        if optleague not in leagues:
            irc.reply("Must specify league. Leagues is one of: %s" % leagues.keys())
            return

        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vc29jY2VyL3Njb3JlYm9hcmQ/') + 'leagueTag=%s&lang=EN&wjb=' % (leagues[optleague])
    
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open %s" % url)
            return
        
        soup = BeautifulSoup(html)
        divs = soup.findAll('div', attrs={'class':'ind'})

        append_list = []

        for div in divs:
            if div.find('div', attrs={'style':'white-space: nowrap;'}): # <div style="white-space: nowrap;">
                match = div.find('div', attrs={'style':'white-space: nowrap;'})
                if match:
                    match = match.getText().replace('Final -','FT -').replace('Postponed -','PP -')
                    match = match.replace('(ESPN, UK)','').replace('(ESPN3)','')
                    append_list.append(str(match).strip().encode('utf-8'))
            
        if len(append_list) > 0:
            descstring = string.join([item for item in append_list], " | ")
            irc.reply(descstring)
        else:
            irc.reply("I did not find any matches going on for: %s" % optleague)          
    soccer = wrap(soccer, [('somethingWithoutSpaces')])

Class = Soccer

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
