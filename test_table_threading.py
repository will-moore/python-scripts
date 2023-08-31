# https://forum.image.sc/t/server-error-after-populating-metadata-for-images-using-web-script/27844/14

import omero
import omero.cli
import threading

THREADS = 10
LOOPS = 20

class T(threading.Thread):
    def __init__(self, table, index):
        threading.Thread.__init__(self)
        self.table = table
        self.index = index
        self.exc = None
    def run(self, *args, **kwargs):
        try:
            if self.index < (THREADS-1):
                for x in range(LOOPS):
                    try:
                        self.table.getHeaders()
                    except Exception as e:
                        self.exc = e
                        break
            else:
                print("exiting...")
        finally:
            self.table.close()

with omero.cli.cli_login() as cli:
    client = cli.get_client()
    t = client.sf.sharedResources().newTable(1, "foo.h5")
    t.initialize([omero.grid.LongColumn("foo")])
    file = t.getOriginalFile()
    threads = []
    for x in range(THREADS):
        threads.append(T(t, x))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # Final thread closes

for idx, thread in enumerate(threads):
    print ("%s\t%s" % (idx, str(thread.exc).split("\n")[0]))
