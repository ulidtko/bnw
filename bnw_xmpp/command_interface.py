# -*- coding: utf-8 -*-
#from twisted.words.xish import domish

from base import *

import bnw_core.bnw_objects as objs

@require_auth
@defer.inlineCallbacks
def cmd_interface(request,iface=None): # TODO: asynchronize
        parsers=('simplified','redeye')
        if not iface:
            defer.returnValue(
                dict(ok=True,desc='Possible interfaces: '+', '.join(parsers))
            )
        if iface in parsers:
            request.user['interface']=iface
            _ = yield objs.User.save(request.user)
            defer.returnValue(
                dict(ok=True,desc='Interface changed.')
            )
        else:
            defer.returnValue(
                dict(ok=True,desc='No such interface.')
            )
