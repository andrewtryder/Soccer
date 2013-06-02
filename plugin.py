# -*- coding: utf-8 -*-
###
# Copyright (c) 2012-2013, spline
# All rights reserved.
#
#
###

# my libs.
import re
from BeautifulSoup import BeautifulSoup
import unicodedata
from collections import defaultdict  # container for soccerlineup
from operator import itemgetter  # similar names.
import random
import base64  # b64decode
import pytz  # convertTZ
import datetime  # convertTZ
# supybot libs.
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

        return base64.b64decode(string)

    def _remove_accents(self, data):
        """Clean up accented team names so we can print."""

        nkfd_form = unicodedata.normalize('NFKD', unicode(data))
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

    def _splicegen(self, maxchars, stringlist):
        """Return a group of splices from a list based on the maxchars string-length boundary."""

        runningcount = 0
        tmpslice = []
        for i, item in enumerate(stringlist):
            runningcount += len(item)
            if runningcount <= int(maxchars):
                tmpslice.append(i)
            else:
                yield tmpslice
                tmpslice = [i]
                runningcount = len(item)
        yield(tmpslice)

    def _convertTZ(self, origtz, thetime, ampm, tzstring):
        """Crude function to take local AM/PM time and convert into GMT or others (24hr)."""

        # base zones.
        if origtz == "ET":
            local = pytz.timezone("US/Eastern")
        elif origtz == "CT":
            local = pytz.timezone("US/Central")
        elif origtz == "MT":
            local = pytz.timezone("US/Mountain")
        elif origtz == "PT":
            local = pytz.timezone("US/Pacific")
        # going "from" here.
        naive = datetime.datetime.strptime(thetime + " " + ampm, "%I:%M %p")
        local_dt = local.localize(naive, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.timezone(tzstring)) # convert from utc->local(tzstring).
        # return 24hr.
        return utc_dt.strftime("%H:%M")

    def _similarTeams(self, teams, optteam):
        """Returns the top5 closest team names in 'teams' based on edit distance to optteam."""

        distances = []  # output container.
        for k in teams:  # need to input a list of teams.
            tmpdict = {}
            tmpdict['dist'] = int(utils.str.distance(optteam, k))
            tmpdict['name'] = k
            distances.append(tmpdict)
        # now find our top5 closest.
        distances = sorted(distances, key=itemgetter('dist'), reverse=False)[0:5]
        # return the team names as a list.
        output = [i['name'] for i in distances]
        return output

    def _sanitizeName(self, optname):
        """return a sanitized name so matching is easier."""

        optname = optname.lower()  # lower because case sucks.
        optname = optname.replace('.', '')  # remove periods.
        optname = optname.strip()  # remove spaces on the outside
        return optname

    def _httpget(self, url, h=None, d=None, l=True):
        """General HTTP resource fetcher. Pass headers via h, data via d, and to log via l."""

        if self.registryValue('logURLs') and l:
            self.log.info(url)

        try:
            if h and d:
                page = utils.web.getUrl(url, headers=h, data=d)
            else:
                page = utils.web.getUrl(url)
            return page
        except utils.web.Error as e:
            self.log.error("ERROR opening {0} message: {1}".format(url, e))
            return None

    ################################
    # LEAGUE AND TOURNAMENT TABLES #
    ################################

    def _validtournaments(self, tournament=None):
        """Return string containing tournament string if valid, None if error. If no tournament is given, return dict keys."""

        tournaments = { 'wcq-uefa':['fifa.worldq.uefa', 'CET'],
                        'intlfriendly':['fifa.friendly', 'US/Eastern'],
                        'wcq-concacaf':['fifa.worldq.concacaf', 'US/Eastern'],
                        'wcq-conmebol':['fifa.worldq.conmebol', 'US/Eastern'],
                        'ucl':['UEFA.CHAMPIONS', 'CET'],
                        'carling':['ENG.WORTHINGTON', 'GMT'],
                        'europa':['UEFA.EUROPA', 'CET'],
                        'facup':['ENG.FA', 'GMT'],
                        'knvbcup':['NED.CUP', 'CET'],
                        'copadelrey':['ESP.COPA_DEL_REY', 'CET'],
                        'concacaf-cl':['CONCACAF.CHAMPIONS', 'US/Eastern'],
                        'goldcup':['concacaf.gold', 'US/Eastern'],
                        'coppaitalia':['ita.coppa_italia', 'CET'],
                        'dfbcup':['ger.dfb_pokal', 'CET'] }

        # check input. if None, return keys. Else, check for key/value match.
        if not tournament:  # if no tournament, return the keys.
            return " | ".join(sorted(tournaments.keys()))
        else:  # check for tournament.
            if tournament not in tournaments:  # not found.
                return None  # no tournament found.
            else:  # return the value from key.
                return tournaments[tournament]

    def _validleagues(self, league=None):
        """Return string containing league string if valid, None if error. If no league given, return leagues as keys of dict."""

        leagues = { 'mls':['usa.1', 'US/Eastern'],
                    'epl':['eng.1', 'GMT'],
                    'laliga':['esp.1', 'CET'],
                    'npower-cship':['eng.2', 'GMT'],
                    'seriea':['ita.1', 'CET'],
                    'bundesliga':['ger.1', 'CET'],
                    'ligue1':['fra.1', 'CET'],
                    'turkish':['tur.1', 'EET'],
                    'eredivisie':['ned.1', 'CET'],
                    'ligamx':['mex.1', 'US/Eastern'],
                    'austrian':['aut.1', 'CET'],
                    'belgian':['bel.1', 'CET'],
                    'danish':['den.1', 'CET'],
                    'portuguese':['por.1', 'WET'],
                    '2spain':['esp.2', 'CET'],
                    '2bundesliga':['ger.2', 'CET'],
                    'allsvenskanliga':['swe.1', 'CET'],
                    'danish':['den.1', 'CET'],
                    'russian':['rus.1','Europe/Moscow'],
                    'scottish':['sco.1', 'GMT'],
                    'argentina':['arg.1', 'America/Argentina/Buenos_Aires'] }

        # check input. if None, return keys. Else, check for key/value match.
        if not league:  # if no league, return the keys.
            return " | ".join(sorted(leagues.keys()))
        else:  # check for league.
            if league not in leagues:  # not found.
                return None  # no league found.
            else:  # return the value from key.
                return leagues[league]

    ####################
    # PUBLIC FUNCTIONS #
    ####################

    def soccer(self, irc, msg, args, optscore):
        """<league/tournament>
        Display live/completed scores for various leagues and tournaments.
        Usage: leagues to display a list of leagues/tournaments.
        Ex: EPL or leagues
        """

        # first, check if we're looking for a league or tournament and setup variables.
        optscore, teamstring = optscore.lower(), None  # lower optscore, setup empty teamstring.
        validkeys = "{0} | {1}".format(self._validleagues(league=None), self._validtournaments(tournament=None))  # use for later.
        if optscore == "leagues" or optscore == "help":  # someone wants the leagues/tournament keys.
            irc.reply("Valid leagues and tournaments are: {0}".format(validkeys))
            return
        else:  # search leagues->tournaments-> looking for a team.
            leaguestring = self._validleagues(league=optscore)  # check for a league.
            if not leaguestring:  # no league found.
                tournamentstring = self._validtournaments(tournament=optscore)  # check for a tournament.
                if not tournamentstring:  # no tournament found.
                    teamstring = optscore  # must be looking for a team.
        # now, based on above, we setup our url and tzstring.
        if leaguestring:  # if we're looking for a league.
            url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vc29jY2VyL3Njb3JlYm9hcmQ/') + 'leagueTag=%s&lang=EN&wjb=' % leaguestring[0]
            tzstring = leaguestring[1]
        elif not leaguestring and tournamentstring:  # no league string.
            url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vc29jY2VyL3Njb3JlYm9hcmQ/') + 'leagueTag=%s&lang=EN&wjb=' % tournamentstring[0]
            tzstring = tournamentstring[1]
        else:  # generic url (search with teamstring)
            url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vc29jY2VyL3Njb3JlYm9hcmQ/Jmxhbmc9RU4md2piPQ==')
            tzstring = 'US/Eastern'
        # fetch url.
        html = self._httpget(url)
        if not html:
            irc.reply("ERROR: Failed to fetch {0}.".format(url))
            self.log.error("ERROR opening {0}".format(url))
            return
        # process html.
        soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES, fromEncoding='utf-8')
        divs = soup.findAll('div', attrs={'class':'ind'})
        # container for output.
        append_list = []
        # each div is a container for games.
        for div in divs:
            if div.find('div', attrs={'style':'white-space: nowrap;'}):  # each of these are games.
                match = div.find('div', attrs={'style':'white-space: nowrap;'})
                match = match.getText().encode('utf-8')  # do string formatting/color. encode.
                match = match.split('(', 1)[0]  # easier to strip out the tv stuff.
                # now, we're left with the text. two conditionals for game started or not.
                if not " vs " in match:  # Match has started.
                    parts = re.split("^(.*?)\s-\s(.*?)\s(\d+)-(\d+)\s(.*?)$", match)  # regex for score.
                    if len(parts) is 7:  # split to bold the winner.
                        parts[2] = parts[2].strip()  # clean up extra spaces in teams.
                        parts[5] = parts[5].strip()  # ibid.
                        if parts[3] > parts[4]:  # bold winner: homeTeam winning.
                            match = "{0} - {1} {2}-{3} {4}".format(parts[1], ircutils.bold(parts[2]), ircutils.bold(parts[3]), parts[4], parts[5])
                        elif parts[4] > parts[3]:  # bold winner: awayTeam winning.
                            match = "{0} - {1} {2}-{3} {4}".format(parts[1], parts[2], parts[3], ircutils.bold(parts[4]), ircutils.bold(parts[5]))
                        else:  # tied. no bold
                            match = "{0} - {1} {2}-{3} {4}".format(parts[1], parts[2], parts[3], parts[4], parts[5])
                    # finish up by abbr/color. this is also parts[1]
                    match = match.replace('Final -', ircutils.mircColor('FT', 'red') + ' -')
                    match = match.replace('Half -', ircutils.mircColor('HT', 'yellow') + ' -')
                    match = match.replace('Postponed -', ircutils.mircColor('PP', 'yellow') + ' -')
                elif " vs " in match:  # match not started. String looks like: ['11:45', 'AM', 'PT', '- Stoke City vs Liverpool']
                    parts = match.split(' ', 3)  # try to split into 4. worst case we get an error and fix it manually.
                    if parts[2] in ["ET", "CT", "MT", "PT"] and self.registryValue('adjustTZ', msg.args[0]):  # must be ET+PT and adjustTZ on in config.
                        adjustedtime = self._convertTZ(parts[2], parts[0], parts[1], tzstring)  # '11:45', 'AM', 'PT', 'league/tournament'
                        match = "{0} {1}".format(adjustedtime, parts[3])  # HH:mm - Match
                    else:  # timestring is not ET/PT or we don't want to adjustTZ config.
                        match = "{0} {1}".format(parts[0], parts[3])  # HH:mm - Match
                # now we add the game in. strip the extras.
                append_list.append(match.strip())
        # output time. if we have teamstring, only display what we match.
        if teamstring:  # looking for a specific game/score
            outlist = []  # container for output.
            for item in append_list:  # iterate through our matches.
                if teamstring in item.lower():  # if we match item inside.
                    if not self.registryValue('disableANSI', msg.args[0]):  # color.
                        outlist.append(item)  # add into our list.
                    else:  # no color.
                        outlist.append(ircutils.stripFormatting(item))
            # now that we have matching items, check length and output differently.
            if len(outlist) == 0:  # no matches found.
                irc.reply("ERROR: I did not find anything for: '{0}'. To see valid leagues and tournaments, issue 'leagues' as argument.".format(teamstring))
            elif 1 <= len(outlist) <= 5:  # we have between 1-5 matching items.
                irc.reply("{0}".format(" | ".join([item for item in outlist])))
            else:   # more than 5, so take first five, print, and relay error.
                irc.reply("{0}".format(" | ".join([item for item in outlist[0:5]])))
                irc.reply("I found too many matches for '{0}'. Try something more specific.".format(teamstring))
        else:  # regular output for tournament/leagues.
            if len(append_list) < 1:  # no games.
                irc.reply("Sorry, I did not find any matches going on in: {0}".format(optscore))
            else:  # we have games.
                for splice in self._splicegen('380', append_list):
                    if not self.registryValue('disableANSI', msg.args[0]):
                        irc.reply(" | ".join([append_list[item] for item in splice]))
                    else:
                        irc.reply(" | ".join([ircutils.stripFormatting(append_list[item]) for item in splice]))

    soccer = wrap(soccer, [('text')])

    def soccerformation(self, irc, msg, args):
        """
        Display a random lineup for channel users.
        """

        if not ircutils.isChannel(msg.args[0]):  # make sure its run in a channel.
            irc.reply("ERROR: Must be run from a channel.")
            return
        # now make sure we have more than 9 users.
        users = [i for i in irc.state.channels[msg.args[0]].users]
        if len(users) < 11:  # need >9 users.
            irc.reply("Sorry, I can only run this in a channel with more than 9 users.")
            return
        # now that we're good..
        formations = {'4-4-2':['(GK)', '(RB)', '(CB)', '(CB)', '(LB)', '(RM)', '(LM)', '(CM)', '(CM)', '(FW)', '(FW)'],
                      '4-4-1-1':['(GK)', '(RB)', '(CB)', '(CB)', '(LB)', '(RM)', '(LM)', '(CM)', '(CM)', '(ST)', '(FW)'],
                      '4-5-1':['(GK)', '(RB)', '(CB)', '(CB)', '(LB)', '(RM)', '(LM)', '(CM)', '(CM)', '(CM)', '(ST)'],
                      '3-5-1-1':['(GK)', '(CB)', '(CB)', '(SW)', '(RM)', '(CM)', '(LM)', '(CM)', '(CM)', '(FW)', '(ST)'],
                      '10-1 (CHELSEA)':['(GK)', '(LB)', '(CB)', '(RB)', '(CB)', '(CB)', '(CB)', '(CB)', '(CB)', '(CB)', '(DROGBA)'],
                      '8-1-1 (PARK THE BUS)':['(GK)', '(LB)', '(CB)', '(RB)', '(CB)', '(CB)', '(CB)', '(CB)', '(CB)', '(CM)', '(ST)']
                     }
        formation = random.choice(formations.keys())
        random.shuffle(formations[formation])  # shuffle.
        lineup = []  # list for output.
        for position in formations[formation]:  # iterate through and highlight.
            a = random.choice(users)  # pick a random user.
            users.remove(a)  # remove so its unique. append below.
            lineup.append("{0}{1}".format(ircutils.bold(a), position))
        # now output.
        output = "{0} ALL-STAR LINEUP ({1}) :: {2}".format(ircutils.mircColor(msg.args[0], 'red'), formation, ", ".join(lineup))
        if not self.registryValue('disableANSI', msg.args[0]):  # display color or not?
            irc.reply(output)
        else:
            irc.reply(ircutils.stripFormatting(output))

    soccerformation = wrap(soccerformation)

    def soccerlineup(self, irc, msg, args, optteam):
        """<team>
        Display lineup for team.
        Ex: Real Madrid
        """

        optteam = self._sanitizeName(optteam)  # sanitize input.
        # build and fetch url. (scoreboard)
        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vc29jY2VyL3Njb3JlYm9hcmQ/bGFuZz1FTiZ3amI9')
        html = self._httpget(url)
        if not html:
            irc.reply("ERROR: Failed to fetch {0}.".format(url))
            self.log.error("ERROR opening {0}".format(url))
            return
        # process html.
        soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES, fromEncoding='utf-8')
        games = soup.findAll('div', attrs={'style':'white-space: nowrap;'})
        # k,v where the key is the name of the team. value is match id.
        matches = {} #collections.defaultdict(list)
        # for each match, filter.
        for game in games:
            if game.find('a', attrs={'href':re.compile('^gamecast.*')}):  # only matches.
                match = game.getText()  # text so we can regex below.
                match = match.replace('(ESPN, UK)','').replace('(ESPN3)','').replace('(ESPN2)','').replace('(ESPN, US)','')  # remove manually
                parts = re.split("^.*?\s-\s(.*?)\s(?:vs|\d+-\d+|P-P)\s(.*?)$", match, re.UNICODE)
                gameid = game.find('a')['href']  # find the gameid.
                gameid = gameid.replace('gamecast?gameId=', '').replace('&lang=EN&wjb=', '')  # strip.
                if len(parts) == 4:  # sanity check.
                    matches[self._sanitizeName(parts[1])] = gameid
                    matches[self._sanitizeName(parts[2])] = gameid
        # now, fetch the matchid.
        optmatch = matches.get(optteam)
        if not optmatch:  # we did not find a matching team.
            irc.reply("ERROR: I did not find any matches with a team '{0}' in them playing. Spelled wrong? Missing accent?".format(optteam))
            irc.reply("The closest five I found: {0}".format(" | ".join([i for i in self._similarTeams(matches, optteam)])))
            return
        else:  # we did find a match. lets continue.
            # construct url with matchid.
            url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vc29jY2VyL2dhbWVjYXN0P2dhbWVJZD0=') + '%s&action=summary&lang=EN&wjb=' % optmatch
            html = self._httpget(url)
            if not html:
                irc.reply("ERROR: Failed to fetch {0}.".format(url))
                self.log.error("ERROR opening {0}".format(url))
                return
            # process html.
            soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES, fromEncoding='utf-8')
            link = soup.find('a', attrs={'class':'white'}, text='LINEUPS')
            if not link:  # test for link.
                irc.reply("ERROR: I did not find a lineup for {0}. Either the match was suspended, check closer to gametime or no lineups given.".format(optteam))
                return
            # found link so find the table with lineups.
            table = link.findNext('table', attrs={'class':'stats', 'cellpadding':'3', 'cellspacing':'0'})
            rows = table.findAll('tr')
            # our datacontainer here.
            lineupteams = []
            lineup = defaultdict(list)
            lineupsubs = defaultdict(list)
            # each "row" is a player in the table.
            for i, row in enumerate(rows):
                if i == 0:  # handle the first row, which is the teams.
                    tds = row.findAll('td')
                    for td in tds:  # should always be two here.
                        lineupteams.append(td.getText().encode('utf-8'))  # populate the list with the two teams (0, 1)
                else:  # each other rows, which are players.
                    divs = row.findAll('div', attrs={'style':'white-space: nowrap;'})  # two divs
                    for y, div in enumerate(divs):  # enumerate so we can ref lineup teams.
                        pn = self._remove_accents(div.getText())
                        if row.findPrevious('td', attrs={'align':'center'}, text='Substitutes'):  # is it a sub?
                            lineupsubs[lineupteams[y]].append(pn.encode('utf-8'))
                        else:  # non-subs.
                            lineup[lineupteams[y]].append(pn.encode('utf-8'))
            # output time.
            for team in lineupteams:  # one per team.
                irc.reply("{0} lineup :: {1} :: SUBS :: {2}".format(team, " | ".join(lineup[team]), " | ".join(lineupsubs[team])))

    soccerlineup = wrap(soccerlineup, [('text')])

    def soccerstats(self, irc, msg, args, optleague, optstat):
        """<league> <goals|assists|cards|fairplay>
        Display stats in league for a statistic.
        Ex: EPL goals or laliga assists or bundesliga cards
        """

        # check for valid stats and leagues below.
        optleague, optstat = optleague.lower(), optstat.lower()
        # check for a valid league.
        leagueString = self._validleagues(league=optleague)
        if not leagueString:
            irc.reply("ERROR: Must specify league. Leagues is one of: {0}".format(self._validleagues(league=None)))
            return
        # check for a valid stat.
        validstat = {'goals':'scorers', 'assists':'assists', 'cards':'discipline', 'fairplay':'fairplay'}
        if optstat not in validstat:
            irc.reply("ERROR: Stat category must be one of: {0}".format(" | ".join(sorted(validstat.keys()))))
            return
        # build and fetch url.
        url = self._b64decode('aHR0cDovL3NvY2Nlcm5ldC5lc3BuLmdvLmNvbS9zdGF0cw==') + '/%s/_/league/%s/' % (validstat[optstat], leagueString[0])
        html = self._httpget(url)
        if not html:
            irc.reply("ERROR: Failed to fetch {0}.".format(url))
            self.log.error("ERROR opening {0}".format(url))
            return
        # sanity check before.
        if "There are no statistics available for this season." in html:
            irc.reply("ERROR: I did not find any statistics for: {0} in {1}".format(optstat, optleague))
            return
        # process html.
        soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES, fromEncoding='utf-8')
        table = soup.find('table', attrs={'class':'tablehead'})
        title = soup.find('h2').getText().encode('utf-8')
        rows = table.findAll('tr', attrs={'class':re.compile('(^odd|^even)row')})[0:10]  # top10.
        # container for output.
        append_list = []
        # each row is a player.
        for row in rows:
            tds = row.findAll('td')
            # depending on the stat, conditional adds to the list. utf-8 player/team names.
            if optstat == "goals" or optstat == "assists":
                appendString = "{0} ({1})".format(tds[1].getText().encode('utf-8'), tds[3].getText())
            elif optstat == "cards":
                appendString = "{0} (Y: {1} R: {2} PTS: {3})".format(tds[1].getText().encode('utf-8'), tds[3].getText(), tds[4].getText(), tds[5].getText())
            elif optstat == "fairplay":
                appendString = "{0} (Y: {1} R: {2} PTS: {3})".format(tds[1].getText().encode('utf-8'), tds[2].getText(), tds[3].getText(), tds[4].getText())
            # finally add.
            append_list.append(appendString)
        # output time.
        descstring = " | ".join([item for item in append_list])  # join all the players/stats.
        #output = "{0} leaders in {1} :: {2}".format(ircutils.underline(optleague), ircutils.mircColor(optstat, 'red'), descstring)
        output = "{0} :: {1}".format(ircutils.mircColor(title, 'red'), descstring)
        if not self.registryValue('disableANSI', msg.args[0]):  # display color or not?
            irc.reply(output)
        else:
            irc.reply(ircutils.stripFormatting(output))

    soccerstats = wrap(soccerstats, [('somethingWithoutSpaces'), ('somethingWithoutSpaces')])

    def soccertable(self, irc, msg, args, optleague):
        """<league>
        Display a league's table (standings).
        Ex: bundesliga
        """

        # make sure we have a league.
        optleague = optleague.lower()
        leagueString = self._validleagues(league=optleague)
        if not leagueString:
            irc.reply("ERROR: Must specify league. Leagues is one of: %s" % (self._validleagues(league=None)))
            return
        # build and fetch url.
        url = self._b64decode('aHR0cDovL3NvY2Nlcm5ldC5lc3BuLmdvLmNvbS90YWJsZXMvXy9sZWFndWU=') + '/%s/' % leagueString[0]
        html = self._httpget(url)
        if not html:
            irc.reply("ERROR: Failed to fetch {0}.".format(url))
            self.log.error("ERROR opening {0}".format(url))
            return
        # now process html.
        soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES, fromEncoding='utf-8')
        tables = soup.findAll('table', attrs={'class':'tablehead'})
        for table in tables:  # must do this because of MLS with east/west standings.
            # header = table.find('tr', attrs={'class':'colhead'}).findAll('td')
            title = table.find('thead').find('tr', attrs={'class':'stathead sl'})
            titleSpan = title.find('span')  # remove span which has the current date.
            if titleSpan:
                titleSpan.extract()
            rows = table.findAll('tr', attrs={'align':'right'})[1:]  # skip header.
            # list for output.
            append_list = []
            # each row is a team.
            for row in rows:
                tds = row.findAll('td')
                rank = tds[0]
                movement = tds[1].find('img')['src']
                team = self._remove_accents(tds[2].getText()) #.encode('utf-8')
                pts = tds[-1]
                if "up_arrow" in movement:  # moving up.
                    appendString = (rank.getText() + ". " + team + " " + pts.getText())
                elif "down_arrow" in movement:  # lost points.
                    appendString = (rank.getText() + ". " + team + " " + pts.getText())
                else:  # draw/inactive.
                    appendString = (rank.getText() + ". " + team + " " + pts.getText())
                append_list.append(appendString)
            # prepare to output.
            title = title.getText().strip().encode('utf-8').replace('\r\n', '')
            if not self.registryValue('disableANSI', msg.args[0]):  # display color or not?
                descstring = " | ".join([item for item in append_list])
                output = "{0} :: {1}".format(ircutils.bold(title), descstring)
            else:  # no color.
                descstring = " | ".join([ircutils.stripFormatting(item) for item in append_list])
                output = "{0} :: {1}".format(title, descstring)
            # output.
            irc.reply(output)

    soccertable = wrap(soccertable, [('somethingWithoutSpaces')])

    def fifarankings(self, irc, msg, args, optinput):
        """[team]
        Display FIFA rankings.
        Defaults to the top10 teams.
        Call with [team] to find a team (country).
        """

        # build and fetch url.
        url = self._b64decode('aHR0cDovL3VzLnNvY2NlcndheS5jb20vdGVhbXMvcmFua2luZ3MvZmlmYS8=')
        html = self._httpget(url)
        if not html:
            irc.reply("ERROR: Failed to fetch {0}.".format(url))
            self.log.error("ERROR opening {0}".format(url))
            return
        # now process html.
        soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES, fromEncoding='utf-8')
        year = soup.find('div', attrs={'id':'year-select'}).find('select').find('option', attrs={'selected':'selected'}).getText()
        month = soup.find('div', attrs={'id':'month-select'}).find('select').find('option', attrs={'selected':'selected'}).getText()
        table = soup.find('table', attrs={'class':'leaguetable table fifa_rankings'})
        rows = table.findAll('tr', attrs={'class':re.compile('even|odd')})
        # container for output. key = int(rank), value = team+entry.
        fifarankings = defaultdict(list)
        # each row is a team.
        for row in rows:
            tds = [item.getText() for item in row.findAll('td')]
            rank = int(tds[0])
            team = tds[1].encode('utf-8')
            points = tds[2]
            change = tds[4]
            fifarankings[rank] = "{0} - {1}({2})".format(team, points, change)
        # prepare for output.
        if not optinput:  # just display top10.
            output = " | ".join([str(k) + ". " + v for (k, v) in fifarankings.items()[0:10]])
            if not self.registryValue('disableANSI', msg.args[0]):  # color
                irc.reply("{0} ({1}-{2}) :: {3}".format(ircutils.mircColor("FIFA Rankings", 'red'), year, month, output))
            else:  # no color
                irc.reply("FIFA Rankings ({0}-{1}) :: {2}".format(year, month, output))
        else:  # search for a specific team.
            count = 0  # max 5 to display.
            for (k, v) in fifarankings.items():  # iterate through all.
                if optinput.lower() in v.lower():  # match here.
                    count += 1  # ++ or +1.
                    if count < 6:  # 5 or fewer, output.
                        irc.reply("{0}. {1}".format(k, v))
                    else:  # spit out a more specific.
                        irc.reply("Sorry, I found too many matches for '{0}'. Please try to be more specific.".format(optinput))
                        break

    fifarankings = wrap(fifarankings, [optional('text')])


Class = Soccer

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
