
import Queue
import sqlite3

from dictmaster.util import CancelableThread, FLAGS

class QueueThread(CancelableThread):
    queue = None

    def __init__(self):
        super(QueueThread, self).__init__()
        self.queue = Queue.Queue()

    def process_item(self, item): return None
    def put(self, item): self.queue.put(item)

    def run(self):
        while True:
            try: item = self.queue.get(timeout=1)
            except Queue.Empty:
                if self._canceled: break
                else: continue
            self.process_item(item)
            self.queue.task_done()

class RawDbQueue(QueueThread):
    output_db = ""

    _conn = None
    _c = None

    def __init__(self, db_file):
        super(RawDbQueue, self).__init__()
        self.output_db = db_file

    def process_item(self, item):
        rawid, uri, data, flag = item
        test_flag = FLAGS["RAW_FETCHER"] | FLAGS["FETCHED"]
        if flag & test_flag == test_flag:
            self._c.execute("SELECT id FROM raw WHERE data=?", (data,))
            dupid = self._c.fetchone()
            if dupid != None:
                data = dupid[0]
                flag |= FLAGS["DUPLICATE"]
        if rawid == None:
            self._c.execute('''
                INSERT INTO raw(uri,data,flag)
                VALUES (?,?,?)
            ''', (uri, data, flag))
        else:
            self._c.execute('''
                UPDATE raw
                SET uri=?, data=?, flag=?
                WHERE id=?
            ''', (uri, data, flag, rawid))

    def run(self):
        self._conn = sqlite3.connect(self.output_db)
        self._c = self._conn.cursor()
        QueueThread.run(self)
        self._conn.commit()
        self._conn.close()

