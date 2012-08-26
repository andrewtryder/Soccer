#!/usr/bin/env python
# -*- coding=utf-8 -*-
# 
# Copyright © 2012 Alex Kilgour (alexkilgour at hotmail dot com | @alexjkilgour)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from BeautifulSoup import BeautifulSoup
import urllib2
import re
import datetime
import sys

now = datetime.datetime.now()

if len(sys.argv) != 2:  # the program name and the one argument (team name)
	# stop the program and print an error message
	print "Please provide either the name of a team e.g. 'fixture chelsea', or the number of the team e.g. 'fixture 45'"
	sys.exit("Type 'fixture list' for a list of team names and numbers")

# grab the argument
arg = sys.argv[1]

# generate the list of possible teams
bbc = urllib2.urlopen('http://www.bbc.co.uk/sport/football/teams')
bbcsoup = BeautifulSoup(bbc)
bbcsoup.prettify()

# pull out all the relevent information.
teamslist = []
allteams = bbcsoup.find('div', 'teams-index')
for item in allteams.findAll('div', 'competition'):
	# get the name of the league. not used atm.
	#title = item.find('h2', 'table-header').contents[0].string
	for lists in item.findAll('ul'):
		for team in lists.findAll('li'):
			name = team.find('a')
			url = str(name['href'])
			url = re.sub('\/', '', url)
			url = re.sub('sport', '', url)
			url = re.sub('football', '', url)
			url = re.sub('teams', '', url)
			teamslist.append(url)
    
# output either the list or the fixture
if arg == 'list':
	for index, item in enumerate(teamslist):
		print str(index) + ')',
		print item
else:
	if arg in teamslist:
		# generate the next game for arg
		bbc = urllib2.urlopen('http://www.bbc.co.uk/sport/football/teams/' + arg)
		bbcsoup = BeautifulSoup(bbc)
		bbcsoup.prettify()
	elif arg.isdigit():
		if int(arg) in range(len(teamslist)):
			# generate the next game for arg
			arg = teamslist[int(arg)]
			bbc = urllib2.urlopen('http://www.bbc.co.uk/sport/football/teams/' + arg)
			bbcsoup = BeautifulSoup(bbc)
			bbcsoup.prettify()
		else:
			print "Please provide either the name of a team e.g. 'fixture chelsea', or the number of the team e.g. 'fixture 45'"
			sys.exit("Type 'fixture list' for a list of team names and numbers")
	else:
		print "Please provide either the name of a team e.g. 'fixture chelsea', or the number of the team e.g. 'fixture 45'"
		sys.exit("Type 'fixture list' for a list of team names and numbers")
		
	# pull out all the relevent information.
	table = bbcsoup.find('div', { 'id' : 'next-match' })
	matchtype = table.find('span', 'match-league')
	# can include league to show the match tournament e.g. Premier League, Champions League etc...
	league = matchtype.find('a').contents[0].string
	league = re.sub('^\s+', '', league)
	league = re.sub('\s+$', '', league)
	matchdate = table.find('div', 'component-content').contents[0].string
	matchdate = re.sub('^\s+', '', matchdate)
	matchdate = re.sub('\s+$', '', matchdate)
	# date comparison to see if it is today. May need to adjust to handle leading 0 issue 
	puredate = re.sub('^[A-z]*', '', matchdate)
	puredate = re.sub('^\s+', '', puredate)
	nowdate = now.strftime('%d %B %Y')
	nowdate = re.sub('^0', '', nowdate)
	if nowdate == puredate:
		matchdate = 'Today '
	else:
		matchdate = matchdate.rstrip('0123456789')
	kickoff = table.find('span', 'match-status').contents[0].string
	kickoff = re.sub('^\s+', '', kickoff)
	kickoff = re.sub('\s+$', '', kickoff)
	
	against = table.find('span', 'match-against')
	team = against.find(attrs={"itemprop" : "name"}).contents[0].string
	team = re.sub('^\s+', '', team)
	team = re.sub('\s+$', '', team)

	print kickoff + ' ' + matchdate + 'vs ' + team