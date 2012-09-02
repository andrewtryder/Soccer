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
import unicodedata

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
    
    def _remove_accents(self, data):
        nkfd_form = unicodedata.normalize('NFKD', unicode(data))
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

    def _validleagues(self, league=None):
        """Return string containing league string if valid, 0 if error. If no league given, return leagues as keys of tuple."""
        leagues = { 'MLS':'usa.1', 'EPL':'eng.1', 'LaLiga':'esp.1',
                    'SerieA':'ita.1', 'Bundesliga':'ger.1', 'Ligue1':'fra.1',
                    'Eredivise':'ned.1', 'LigaMX':'mex.1'
                  }
        
        if league is None:
            return leagues.keys() # return the keys here for an list to display.
        else:
            if league not in leagues:
                return "0" # to parse an error.
            else:
                return leagues[league]
            

    ####################
    # Public Functions #
    ####################
            
    
    def soccer(self, irc, msg, args, optleague):
        """[league]
        Display live/completed scores for various leagues.
        """
        
        leagueString = self._validleagues(league=optleague)
        
        if leagueString == "0":
            irc.reply("Must specify league. Leagues is one of: %s" % (self._validleagues(league=None)))
            return

        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vc29jY2VyL3Njb3JlYm9hcmQ/') + 'leagueTag=%s&lang=EN&wjb=' % (leagueString)
    
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
            if div.find('div', attrs={'style':'white-space: nowrap;'}):
                match = div.find('div', attrs={'style':'white-space: nowrap;'})
                if match:
                    match = match.getText().encode('utf-8') # do string formatting/color below. Ugly but it works.
                    match = match.replace('Final -',ircutils.mircColor('FT', 'red') + ' -')
                    match = match.replace('Half -',ircutils.mircColor('HT', 'yellow') + ' -')
                    match = match.replace('Postponed -',ircutils.mircColor('PP', 'yellow') + ' -')
                    match = match.replace('(ESPN, UK)','').replace('(ESPN3)','').replace(' ET','').replace(' CT','').replace(' PT','').replace('(ESPN2)','')
                    # 17' - Osasuna 1-0 Barcelona | 2:00 PM - Getafe vs Real Madrid
                    append_list.append(str(match).strip())
            
        if len(append_list) > 0:
            descstring = string.join([item for item in append_list], " | ")
            irc.reply(descstring)
        else:
            irc.reply("I did not find any matches going on for: %s" % leagueString)
                 
    soccer = wrap(soccer, [('somethingWithoutSpaces')])
    
    
    def soccerstats(self, irc, msg, args, optleague, optstat):
        """[league] [goals|assists|cards|fairplay]
        Display stats in league for stat. Ex: EPL goals 
        """
        
        validstat = {'goals':'scorers', 'assists':'assists', 'cards':'discipline', 'fairplay':'fairplay'}
        
        leagueString = self._validleagues(league=optleague)
        
        if leagueString == "0":
            irc.reply("Must specify league. Leagues is one of: %s" % (self._validleagues(league=None)))
            return

        url = self._b64decode('aHR0cDovL3NvY2Nlcm5ldC5lc3BuLmdvLmNvbS9zdGF0cw==') + '/%s/_/league/%s/' % (validstat[optstat], leagueString)
    
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open %s" % url)
            return

        html = html.replace('&nbsp;','')

        if "There are no statistics available for this season." in html:
            irc.reply("I did not find any statistics for: %s in %s" % (optstat, optleague))
            return
            
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'class':'tablehead'})
        header = table.find('tr', attrs={'class':'colhead'}).findAll('td')
        rows = table.findAll('tr', attrs={'class':re.compile('(^odd|^even)row')})[0:5] # int option

        del header[0] # no need for rank.

        append_list = []

        for row in rows:
            tds = row.findAll('td')
            del tds[0] # delete the first as it is the rank.
            mini_list = []
            for i,td in enumerate(tds):
                colname = header[i].getText().replace('Team','T').replace('Player','Plr').replace('Yellow','Y').replace('Red','R').replace('Points','Pts').replace('Assists','A').replace('Goals','G')
                colstat = td
                mini_list.append(ircutils.bold(colname) + ": " + colstat.getText()) # bold colname.
            append_list.append(" ".join(mini_list))
    						
        descstring = string.join([item for item in append_list], " | ")
        output = "Leaders in {0} for {1} :: {2}".format(ircutils.mircColor(optstat, 'red'), ircutils.underline(optleague), descstring.encode('utf-8'))
        irc.reply(output)
        
    soccerstats = wrap(soccerstats, [('somethingWithoutSpaces'), ('somethingWithoutSpaces')])
    
    
    def soccertable(self, irc, msg, args, optleague):
        """[league]
        Display a league's table (standings).
        """

        leagueString = self._validleagues(league=optleague)
        
        if leagueString == "0":
            irc.reply("Must specify league. Leagues is one of: %s" % (self._validleagues(league=None)))
            return
    
        url = self._b64decode('aHR0cDovL3NvY2Nlcm5ldC5lc3BuLmdvLmNvbS90YWJsZXMvXy9sZWFndWU=') + '/%s/' % leagueString
    
        try: 
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        self.log.info(url)

        soup = BeautifulSoup(html)
        tables = soup.findAll('table', attrs={'class':'tablehead'})
        
        for table in tables: # must do this because of MLS
            header = table.find('tr', attrs={'class':'colhead'}).findAll('td')
            title = table.find('thead').find('tr', attrs={'class':'stathead sl'})
            titleSpan = title.find('span') # remove span which has the current date.
            if titleSpan:
                titleSpan.extract()
            rows = table.findAll('tr', attrs={'align':'right'})[1:] # int option

            append_list = []

            for row in rows:
                tds = row.findAll('td')
                rank = tds[0]
                movement = tds[1].find('img')['src']
                team = tds[2]
                gd = tds[-2]
                pts = tds[-1]
                if "up_arrow" in movement:
                    appendString = (rank.getText() + ". " + self._remove_accents(team.getText()) + " " + pts.getText())
                elif "down_arrow" in movement:
                    appendString = (rank.getText() + ". " + self._remove_accents(team.getText()) + " " + pts.getText())
                else:
                    appendString = (rank.getText() + ". " + self._remove_accents(team.getText()) + " " + pts.getText())
                append_list.append(appendString)
    
            title = self._remove_accents(title.getText().strip().replace('\r\n','')) # clean up title. some have \r\n.
            descstring = string.join([item for item in append_list], " | ")
            output = "{0} :: {1}".format(ircutils.bold(title), descstring)
            irc.reply(output)
        
    
    soccertable = wrap(soccertable, [('somethingWithoutSpaces')])
        
Class = Soccer

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
