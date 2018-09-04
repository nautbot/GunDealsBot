import sqlite3


class DataAccess:
    def __init__(self):
        self._sql = sqlite3.connect('sql.db', check_same_thread=False)
        print('Loaded SQLite Database')
        self._cur = self._sql.cursor()

        # Create processedSubmissions table
        self._sql.execute('CREATE TABLE IF NOT EXISTS '
                          'submissions('
                          'id TEXT NOT NULL PRIMARY KEY, '
                          'createdUTC INTEGER NOT NULL)')

        # Create feeds table
        self._sql.execute('CREATE TABLE IF NOT EXISTS '
                          'feeds('
                          'channelID TEXT NOT NULL PRIMARY KEY)')

        # Create subscriptions table
        self._sql.execute('CREATE TABLE IF NOT EXISTS '
                          'subscriptions('
                          'id INTEGER PRIMARY KEY, '
                          'userID TEXT NOT NULL, '
                          'matchPattern TEXT NOT NULL)')

        self._sql.commit()


    def __del__(self):
        self._sql.close()


    def IsProcessedSubmission(self, submissionID):
        self._cur.execute('SELECT id '
                          'FROM submissions '
                          'WHERE id=?',
                          (submissionID,))
        return True if self._cur.fetchone() else False


    def InsertProcessedSubmission(self, submissionID, submissionCreatedUTC):
        self._cur.execute('INSERT INTO submissions VALUES(?,?)',
                    (submissionID, submissionCreatedUTC))
        self._sql.commit()


    def GetAllFeedChannels(self):
        channels = []
        self._cur.execute('SELECT channelID from feeds')
        for row in self._cur:
            channels.append(str(row[0]))
        return channels


    def GetAllSubscriptions(self):
        subscriptions = []
        self._cur.execute('SELECT id, userID, matchPattern '
                          'FROM subscriptions')
        for row in self._cur:
            subscription = {"ID": str(row[0]),
                            "userID": str(row[1]),
                            "matchPattern": str(row[2])}
            subscriptions.append(subscription)
        return subscriptions


    def RemoveOldProcessedSubmissions(self):
        self._cur.execute('DELETE FROM submissions '
                          'WHERE id NOT IN '
                          '(SELECT id FROM submissions '
                          'ORDER BY createdUTC DESC LIMIT 50)')
        self._sql.commit()
        self._cur.execute('VACUUM')












