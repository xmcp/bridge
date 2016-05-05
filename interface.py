#coding=utf-8

import urllib.request
import urllib.parse
import bs4
import time

class Hust:
    _last_submit=0
    _global_headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2414.0 Safari/537.36',
        'Accept-Language':'zh-CN,zh;q=0.8,en;q=0.6',
    }
    
    def __init__(self,config):
        """ Log in and initialize OJ configs.

        :param config: a dict including key `username` and `url`
        :return: None
        """
        self.username,self.url=config['username'],config['url']

        cookie=urllib.request.HTTPCookieProcessor()
        self.opener=urllib.request.build_opener(cookie)

        result=self.opener.open(urllib.request.Request(
            url='%s/login.php'%self.url,
            data=urllib.parse.urlencode({
                'user_id':self.username,
                'password':config['password'],
                'submit':'Submit',
            }).encode(),
        )).read()
        if b'history.go(-2);' not in result:
            raise RuntimeError('login failed')

        #set language
        self.opener.open(urllib.request.Request(
            url='%s/setlang.php?lang=cn'%self.url,
            headers=self._global_headers,
        ))

    def submit(self,problem_id,source):
        """ Submit a source code to a certain problem.

        :param problem_id: an integer or string indicating the Problem ID
        :param source: the source code
        :return: the Run ID for this submission
        """
        delta=self._last_submit+10-time.time()+.05
        if delta>0:
            time.sleep(delta)

        result=self.opener.open(urllib.request.Request(
            url='%s/submit.php'%self.url,
            data=urllib.parse.urlencode({
                'id':problem_id,
                'language':'1',
                'source':source,
            }).encode(),
            headers=self._global_headers,
        )).read()
        if b'<form id=simform action="status.php" method="get">' not in result:
            raise RuntimeError('submit failed')
        else:
            self._last_submit=time.time()
            soup=bs4.BeautifulSoup(result,'html5lib')
            return int(soup.find_all('tbody')[-1].find(
                lambda x:x.name=='tr' and ((not x.has_attr('class')) or x['class']!=['toprow']) and x.contents[1].text==self.username
            ).contents[0].text)

    def get_status(self,source):
        """ Extract status message in source code.

        :param source: the source code returned by `get_source` method
        :return: a dict indicating the status (`{}` if failed)
        """
        status_lines=map(
            lambda x:x.partition(':'),
            source.partition('****************************************************************/')[0].split('\n')[1:]
        )

        return {x[0].strip():x[2].strip() for x in status_lines if x[1]}

    def get_source(self,run_id):
        """ Get source code by Run ID.

        :param run_id: Run ID returned by `submit` method
        :return: the source code
        """
        soup=bs4.BeautifulSoup(self.opener.open(urllib.request.Request(
            url='{url}/showsource.php?id={runid}'.format(url=self.url,runid=run_id),
            headers=self._global_headers,
        )).read(),'html5lib')
        return soup.pre.text

    def get_problem(self,problem_id):
        """ Get the description of specific problem.

        :param problem_id: Problem ID in the OJ
        :return: the problem description in HTML format
        """
        soup=bs4.BeautifulSoup(self.opener.open(urllib.request.Request(
            url='{url}/problem.php?id={p}'.format(url=self.url,p=problem_id),
            headers=self._global_headers,
        )).read(),'html5lib')
        return ''.join(map(str,soup.body.contents[6:-12]))
