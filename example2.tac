# coding: utf-8
import sys
sys.setappdefaultencoding('utf-8')

from twisted.application import service

from twisted.words.protocols.jabber import component

import dbutils,couchdb
dbutils.db=couchdb.Server('http://10.254.230.1:5984/')['ololo_whores']
dbutils.typeddb=dbutils.TypedDb(dbutils.db)

import bnw_component

application = service.Application("example-echo")

# set up Jabber Component
sm = component.buildServiceManager('ololo.blasux.ru', 'abnn5hhhhhuidsgatjdsfg',
                    ("tcp:127.0.0.1:6592" ))


# Turn on verbose mode
bnw_component.LogService().setServiceParent(sm)

# set up our example Service
s = bnw_component.BnwService()
s.setServiceParent(sm)

sm.setServiceParent(application)