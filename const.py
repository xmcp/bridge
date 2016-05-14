#coding=utf-8

import os
if 'APPSETTING_BRIDGE_SECRET' in os.environ:
    import json
    db_config,oj_config=json.loads(os.environ['APPSETTING_BRIDGE_SECRET'])
else:
    from secret import db_config,oj_config

def hashed(u,p):
    import hashlib
    return hashlib.new(
        'sha384',
        ('hello world! this is a simple hash that indicates a user called %r having the password %r. bazinga!'%(u,p)).encode()
    ).hexdigest()