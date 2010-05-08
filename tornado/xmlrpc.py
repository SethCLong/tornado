#!/usr/bin/env python
#
# Copyright 2010 Seth Long
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""An asynchronous XML-RPC client for Python.

The client is built around the xmlrpclib module and uses Tornado's
AsyncHTTPClient as the transport.
"""

import xmlrpclib
import tornado.httpclient
import urllib

class AsyncXMLRPClient(xmlrpclib.ServerProxy):
    """An asynchronous XML-RPC client.
    
    Since it is built around xmlrpclib the usage is nearly identical
    to the xmlrpclib client except a callback method is added to the
    RPC call. Example usage:
    
        import ioloop
        
        def handle_response(result):
            print result
            
        client = AsyncXMLRPClient("http://example.com/")
        client.add_numbers(handle_response, 1, 2)
        ioloop.IOLoop.instance().start()
    
    If you want more information read the python doc on xmlrpclib at
    http://docs.python.org/library/xmlrpclib.html
    """
    def __init__(self, uri):

        type, uri = urllib.splittype(uri)
        if type not in ("http", "https"):
            raise IOError, "unsupported XML-RPC protocol"
        self.__host, self.__handler = urllib.splithost(uri)
        if not self.__handler:
            self.__handler = "/RPC2"

        self.__uri = "%s://%s%s" % (type, self.__host, self.__handler)
        
    def __parse(self, response):
        p, u = xmlrpclib.getparser()
        p.feed(response.body)
        p.close()
        tmp = u.close()
        
        if len(tmp) == 1:
            tmp = tmp[0]
            
        return tmp

    def __request(self, methodname, callback, params):
        # call a method on the remote server
        postdata = xmlrpclib.dumps(params, methodname, encoding=None,
                        allow_none=0)

        header = {"Content-Length": str(len(postdata))}
        request = tornado.httpclient.HTTPRequest(self.__uri, method="POST", headers=header,
                                           body=postdata, request_timeout=60)

        http = tornado.httpclient.AsyncHTTPClient()
        http.fetch(request, lambda r: callback(self.__parse(r)))

    def __getattr__(self, name):
        # magic method dispatcher
        return _Dispatcher(self.__request, name)
    
class _Dispatcher(object):
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _Dispatcher(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, callback, *args):
        return self.__send(self.__name, callback, args)