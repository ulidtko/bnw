# -*- coding: utf-8 -*-

from base import CommandParserException
from bnw_core.base import BnwResponse
from twisted.internet import defer
import parser_basexmpp

class RedEyeParser(parser_basexmpp.BaseXmppParser):
    def __init__(self,commands,formatters):

        self.commands = {}
        self._commands = {}
        self.commandfuns = {}
        self.formatters = formatters

        for cmd in commands:
            assert len(cmd) in (3,4)
            if len(cmd)==4:
                name,args,handler,restname = cmd
            else:
                name,args,handler = cmd
                restname = None
            self.commands[name] = args
            self.commandfuns[name] = handler,restname
    
    def hashCommand(self,cmd):
        self._commands[cmd]={ "short": {}, "long": {} }
        args=self.commands[cmd]
        #args+=(('h','help',False,'Show list of possible arguments (autogenerated)'),)
        for arg in args:
           if arg[0]:
              self._commands[cmd]['short'][arg[0]]=arg
           if arg[1]:
              self._commands[cmd]['long'][arg[1]]=arg

    def getHashed(self,cmd):
        if not cmd in self._commands:
            self.hashCommand(cmd)
        return self._commands[cmd]
            
    def parseArgument(self,argi,prevopt,arg):
            #print "PA",prevopt,arg
            if prevopt:
                return None,((prevopt,arg),)
            elif arg.startswith('--'):
                namevalue=arg[2:].split('=')
                name=namevalue[0]
                if not name in argi['long']:
                    raise CommandParserException('Unknown option %s' % name)
                if argi['long'][name][2]: # option requires an argument
                    if len(namevalue)<2:
                        raise CommandParserException('Option %s requires an argument' % name)
                    value=namevalue[1]
                else:
                    value=True
                return False,((name,value),)
            elif arg.startswith('-'):
                shorts=[]
                for j,c in enumerate(arg[1:]):
                    if prevopt:
                        shorts.append( (prevopt,arg[j+1:]) )
                        prevopt=None
                        break
                    if not c in argi['short']:
                        raise CommandParserException('Unknown short option %s' % c)
                    if not argi['short'][c][2]:
                        shorts.append( (argi['short'][c][1],True) )
                    else:
                        prevopt=argi['short'][c][1]
                return prevopt,shorts

    def formatCommandHelp(self,command):
        return command+':\n'+'\n'.join( (("-"+arg[0]).rjust(4)+(' ARG' if arg[2] else '    ') + \
          ("--"+arg[1]).rjust(10)+('=ARG' if arg[2] else '    ') + \
          ' '+arg[3]) for arg in self.commands['redeye',command]['handler'].arguments)
        pass

    @defer.inlineCallbacks        
    def handle(self,msg):
        handler,restname,options,rest = self.resolve(msg)#unicode(msg.body).encode('utf-8','ignore'))
        if not handler:
            defer.returnValue('ERROR. Command not found: %s' % (restname,))
        try:
            #if 'help' in options:
            #    defer.returnValue((yield self.formatCommandHelp(command.lower())))
            if restname:
                options[restname] = rest
            options=dict((str(k),v) for k,v in options.iteritems()) # deunicodify options keys
            result=yield handler(msg,**options)
            defer.returnValue(self.formatResult(msg,result))
        except BnwResponse, response:
            defer.returnValue(response)

    def resolve(self,msg):
        text=msg.body
        inquotes=None
        firstsym=True
        wordbegin=-1
        prevopt=None
        rest=u''
        waitcommand=True
        options={}
        wordbuf=[] # i know it's ugly and slow. is there any better way to implement quotes?
        for i,c in enumerate(text):
            if (c==' ' and not inquotes) or c=='\n':
                inquotes=None
                if len(wordbuf)>0: #1: \todo check why there was 1
                    if waitcommand:
                        waitcommand=False
                        command=''.join(wordbuf).lower()#text[wordbegin:i]
                        handler_tuple = self.commandfuns.get(command,None)
                        if not handler_tuple:
                            #raise CommandParserException('No such command: "%s"' % command)
                            return None,command,None,None
                        argi=self.getHashed(command)
                    else:
                        prevopt,newopts = self.parseArgument(argi,prevopt,''.join(wordbuf))
                        for name,value in newopts:
                            options[name]=value
                wordbuf=[]
                firstsym=True
            elif c in ('"',"'"):
                if not inquotes:
                    inquotes=c
                elif inquotes==c:
                    inquotes=None
                else:
                    wordbuf.append(c)
            else:
                if firstsym:
                    wordbegin=i
                    firstsym=False
                    if c!='-' and not (prevopt or waitcommand):
                        if inquotes:
                            rest=inquotes+text[i:]
                        else:
                            rest=text[i:]
                        break
                wordbuf.append(c)
        else:
            if inquotes:
                raise CommandParserException("Ouch! You forgot to close quotes <%s> " % inquotes)
            if waitcommand:
                command = ''.join(wordbuf).lower()
                handler_tuple = self.commandfuns.get(command,None)
                if not handler_tuple:
                    raise CommandParserException('No such command: %s' % command)
            else:
                prevopt,newopts = self.parseArgument(argi,prevopt,''.join(wordbuf))
                if prevopt:
                    raise CommandParserException("Option %s requires an argument" % argi['long'][prevopt][0])
                for name,value in newopts:
                    options[name]=value
        handler,restname = handler_tuple
        return (handler,restname,options,rest)

