###
# Copyright (c) 2013-2014, spline
# All rights reserved.
#
#
###

from supybot.test import *

class SoccerTestCase(PluginTestCase):
    plugins = ('Soccer',)

    def testSoccer(self):
        conf.supybot.plugins.Soccer.disableANSI.setValue('True')
        # fifarankings, soccer, soccerformation, soccerlineup, soccerstats, and soccertable
        self.assertRegexp('fifarankings', 'FIFA Rankings')
        self.assertNotError('soccer epl')
        self.assertNotError('soccerlineup manchester united')
        self.assertNotError('soccerstats epl goals')
        self.assertNotError('soccertable epl')
        



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
