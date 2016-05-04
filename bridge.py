import os
import cherrypy
from mako.lookup import TemplateLookup
import sqlite3
import const
import interface
import time

# def connect():
#     return contextlib.closing(mysql.connector.connect(**const.db_config))
def connect():
    return sqlite3.connect('db.sqlite3')
def auth():
    if 'uid' not in cherrypy.session  or 'username' not in cherrypy.session:
        raise cherrypy.HTTPRedirect('/login')

lookup=TemplateLookup(directories=['templates'],input_encoding='utf-8',output_encoding='utf-8')

class Bridge:
    @cherrypy.expose()
    def index(self):
        auth()
        with connect() as db:
            cur=db.cursor()
            cur.execute('select time,uid,hustid,probid,status,id,source from submits order by time desc')
            result=cur.fetchall()
            new=[]
            for res in result:
                cur.execute('select username from users where id=?',[res[1]])
                new.append({
                    'time': res[0],
                    'username': (cur.fetchone() or ['???'])[0],
                    'hustid': res[2],
                    'probid': res[3],
                    'status': res[4],
                    'subid': res[5],
                    'source': res[6],
                })
            return lookup.get_template('index.html').render(submits=new,username=cherrypy.session['username'])

    @cherrypy.expose()
    def login(self,username=None,password=None):
        if not username or not password:
            return lookup.get_template('login.html').render(error=None)

        with connect() as db:
            cur=db.cursor()
            cur.execute('select id,passhash from users where username=? and disabled=0',[username])
            result=cur.fetchone()
            if result:
                if result[1]==const.hashed(username,password):
                    cherrypy.session['username']=username
                    cherrypy.session['uid']=result[0]
                    raise cherrypy.HTTPRedirect('/')
                else:
                    time.sleep(1.5)
                    return lookup.get_template('login.html').render(error='密码错误')
            else:
                time.sleep(1.5)
                return lookup.get_template('login.html').render(error='用户不存在')

    @cherrypy.expose()
    def logout(self):
        if 'username' in cherrypy.session:
            del cherrypy.session['username']
        if 'uid' in cherrypy.session:
            del cherrypy.session['uid']
        raise cherrypy.HTTPRedirect('/login')

    @cherrypy.expose()
    def problem(self,probid):
        auth()
        probid=int(probid)
        hust=interface.Hust(const.oj_config)
        return lookup.get_template('problem.html').render(probid=probid,text=hust.get_problem(probid))

    @cherrypy.expose()
    def submit(self,probid,source):
        auth()
        probid=int(probid)
        hust=interface.Hust(const.oj_config)
        with connect() as db:
            cur=db.cursor()
            cur.execute(
                "insert into submits (time, uid, hustid, probid, source, status) values (datetime('now','localtime'),?,?,?,?,?)",
                [cherrypy.session['uid'],hust.submit(probid,source),probid,source,'已提交']
            )
            db.commit()
        raise cherrypy.HTTPRedirect('/detail/%d'%cur.lastrowid)

    @cherrypy.expose()
    def detail(self,subid):
        auth()
        subid=int(subid)
        with connect() as db:
            cur=db.cursor()
            cur.execute('select time,hustid,source,status,probid,uid from submits where id=?',[subid])
            result=cur.fetchone()
            if result:
                time,hustid,source,status,probid,uid=result
                if uid!=cherrypy.session['uid']:
                    source="/*************************\n  你只能查看你自己的代码\n*************************/"

                cur.execute('select username from users where id=?',[uid])
                return lookup.get_template('detail.html').render(
                    time=time,hustid=hustid,source=source,status=status,
                    probid=probid,username=(cur.fetchone() or ['???'])[0]
                )
            else:
                raise cherrypy.NotFound()

    @cherrypy.expose()
    def fetch(self,hustid):
        def proc_status():
            st=status.get('Result','未知状态')
            ti=status.get('Time')
            me=status.get('Memory')
            if ti and me:
                return '%s (%s, %s)'%(st,ti,me)
            elif ti:
                return '%s (%s)'%(st,ti)
            elif me:
                return '%s (%s)'%(st,me)
            else:
                return st

        auth()
        hustid=int(hustid)
        hust=interface.Hust(const.oj_config)
        with connect() as db:
            cur=db.cursor()
            cur.execute('select id from submits where hustid=?',[hustid])
            result=cur.fetchone()
            if result:
                subid=result[0]
                source=hust.get_source(hustid)
                status=hust.get_status(source)
                cur.execute('update submits set source=?, status=? where id=?',[source,proc_status(),subid])
                db.commit()
                raise cherrypy.HTTPRedirect('/detail/%d'%subid)
            else:
                return 'No such submission in database.'

cherrypy.quickstart(Bridge(),'/',{
    'global': {
        'engine.autoreload.on':False,
        # 'request.show_tracebacks': False,
        'server.socket_host':'0.0.0.0',
        'server.socket_port':12450,
        # 'error_page.404': lambda status,message,traceback,version:err(status),
    },
    '/': {
        'tools.gzip.on': True,
        'tools.sessions.on': True,
    },
    '/static': {
        'tools.staticdir.on':True,
        'tools.staticdir.dir':os.path.join(os.getcwd(),'static'),
    },
})