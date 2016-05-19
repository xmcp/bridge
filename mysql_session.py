#coding=utf-8
import pickle
import threading

from cherrypy.lib.sessions import Session
import const
import mysql.connector
import contextlib

def connect():
    return contextlib.closing(mysql.connector.connect(**const.db_config))

class MysqlSession(Session):

    """ Implementation of the PostgreSQL backend for sessions. It assumes
        a table like this::

            create table session (
                id varchar(40),
                data text,
                expiration_time timestamp
            )

    You must provide your own get_db function.
    """

    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, id=None, **kwargs):
        Session.__init__(self, id, **kwargs)
        self.locks={}

    @classmethod
    def setup(cls, **kwargs):
        """Set up the storage system for Postgres-based sessions.

        This should only be called once per process; this will be done
        automatically when using sessions.init (as the built-in Tool does).
        """
        for k, v in kwargs.items():
            setattr(cls, k, v)

        cls.locks={}

    def cls__del__(self):
        pass

    def _exists(self):
        # Select session data from table
        with connect() as db:
            cursor=db.cursor()
            cursor.execute('select data, expiration_time from session '
                                'where id=%s', (self.id,))
            rows = cursor.fetchall()
        return bool(rows)

    def _load(self):
        # Select session data from table
        with connect() as db:
            cursor=db.cursor()
            cursor.execute('select data, expiration_time from session '
                                'where id=%s', (self.id,))
            rows = cursor.fetchall()
        if not rows:
            return None

        pickled_data, expiration_time = rows[0]
        data = pickle.loads(pickled_data)
        return data, expiration_time

    def _save(self, expiration_time):
        pickled_data = pickle.dumps(self._data, self.pickle_protocol)
        with connect() as db:
            db.cursor().execute('replace into session (data,expiration_time,id) values (%s,%s,%s)',
                                (pickled_data, expiration_time, self.id))
            db.commit()

    def _delete(self):
        with connect() as db:
            db.cursor().execute('delete from session where id=%s', (self.id,))
            db.commit()

    def acquire_lock(self):
        """Acquire an exclusive lock on the currently-loaded session data."""
        self.locked = True
        self.locks.setdefault(self.id, threading.RLock()).acquire()

    def release_lock(self):
        """Release the lock on the currently-loaded session data."""
        self.locks[self.id].release()
        self.locked = False

    def clean_up(self):
        """Clean up expired sessions."""
        with connect() as db:
            db.cursor().execute('delete from session where expiration_time < %s',
                                (self.now(),))
            db.commit()