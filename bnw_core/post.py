import bnw_objects as objs
from base import get_db,genid,cropstring
from twisted.internet import interfaces, defer, reactor
import time
from twisted.python import log

@defer.inlineCallbacks
def subscribe(user,target_type,target,fast=False):
    sub_rec={ 'user': user['name'], 'target': target, 'type': target_type }
    if fast or ((yield objs.Subscription.find_one(sub_rec)) is None):
        sub=objs.Subscription(sub_rec)
        if (yield sub.save()):
            defer.returnValue(True) #'Subscribed.'
        else:
            defer.returnValue(False)
    else:            
        defer.returnValue(False)

@defer.inlineCallbacks
def unsubscribe(user,target_type,target,fast=False):
    sub_rec={ 'user': user['name'], 'target': target, 'type': target_type }
    db = yield get_db()
    rest = yield db['subscriptions'].remove(sub_rec) # even if there was no such subscription, we don't care
    defer.returnValue(rest) #'Subscribed.'

@defer.inlineCallbacks
def send_to_subscribers(queries,is_message,message):
    recipients=set()
    qn=0
    for query in queries:
        qn+=1
        for result in (yield objs.Subscription.find(query)):
            recipients.add(result['user'])
    for target_name in recipients:
        target=yield objs.User.find_one({'name': target_name})
        qn+=1
        if target:
            if not target.get('off',False):
                if is_message:
                    target.send_post(message)
                else:
                    target.send_comment(message)
                log.msg('Sent %s to %s' % (message['id'],target['jid']))
    defer.returnValue((qn,len(recipients)))

@defer.inlineCallbacks
def postMessage(user,tags,clubs,text,anon=False,anoncom=False):
    db=yield get_db()
    if len(text)==0:
        defer.returnValue('So where is your post?')
    if len(text)>2048:
        #defer.returnValue('E_LONG')
        #XmppResponse('Message is too long. %d/2048' % (len(text),))
        defer.returnValue('Message is too long. %d/2048' % (len(text),))
    message={ 'user': user['name'],
              'tags': tags,
              'clubs': clubs,
              'id': genid(6),
              'date': time.time(),
              'text': text,
              'anonymous': anon,
              'anoncomments': anoncom,
            }
    if anon:
        message['real_user']=message['user']
        message['user']='anonymous'
    stored_message = objs.Message(message)
    stored_message_id = yield stored_message.save()
    
    #raise Exception('ALL WRONG')
    
    #sub_rec={ 'target': message['id'], 'type': 'sub_message', 'user': user['name']}
    sub_result = yield subscribe(user,'sub_message',message['id'],True)
    
    queries=[{'target': tag, 'type': 'sub_tag'} for tag in tags]
    queries+=[{'target': club, 'type': 'sub_club'} for club in clubs]
    queries+=[{'target': 'anonymous' if anon else user['name'], 'type': 'sub_user'}]
    qn,recipients = yield send_to_subscribers(queries,True,message)
    defer.returnValue('Posted with id %s and delivered to %d users. Total cost: $%d' % (message['id'].upper(),recipients,qn))

@defer.inlineCallbacks
def postComment(message_id,comment_id,rest,user,anon=False):
    db = yield get_db()        

    if len(rest)==0:
        defer.returnValue('So where is your comment?')
    if len(rest)>2048:
        defer.returnValue('Comment is too long. %d/2048' % (len(rest),))
    message=yield objs.Message.find_one({'id': message_id})
    if comment_id!=None:
        old_comment=yield objs.Comment.find_one({'id': message_id+'/'+comment_id, 'message': message_id})
    else:
        old_comment=None
    if old_comment==None and comment_id!=None:
        defer.returnValue('No such comment.')
    if message==None:
        defer.returnValue('No such message.')
    
    comment={ 'user': user['name'],
              'id': message_id+'/'+genid(3),
              'message': message_id,
              'date': time.time(),
              'replyto': old_comment['id'] if old_comment else None,
              'replytotext': cropstring(old_comment['text'] if comment_id else message['text'],128),
              'text': ('@'+old_comment['user']+' 'if comment_id else '')+rest,
              'anonymous': anon,
            }
    if anon:
        comment['real_user']=comment['user']
        comment['user']='anonymous'
    comment = objs.Comment(comment)
    comment_id = yield comment.save()
    sub_rec={ 'target': message_id, 'type': 'sub_message', 'user': user['name']}
    sub_result = yield subscribe(user,'sub_message',message_id)
    #if get_db()['subscriptions'].find_one(sub_rec) is None: 
    #    get_db()['subscriptions'].insert(sub_rec)
    
    #for result in get_db().subscriptions.find({'target': message_id, 'type': 'sub_message'}):
    qn,recipients = yield send_to_subscribers([{'target': message_id, 'type': 'sub_message'}],False,comment)
    #defer.returnValue((qn,recipients))
    defer.returnValue('Posted with id %s and delivered to %d users. Total cost: $%d' % (message['id'].upper(),recipients,qn))