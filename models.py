import sqlite3
import logging
import os
logging.basicConfig(level=logging.DEBUG)

class NPCs():
    __root_dir = os.path.dirname(os.path.abspath(__file__))

    def __init__(self) -> None:
        self.__db = sqlite3.connect(os.path.join(self.__root_dir, 'db.sqlite3'))
        self.__db.row_factory = sqlite3.Row

    def get_all(self, game_id: int = None) -> list:
        where = ""
        sql_args = ()
        if game_id is not None:
            where = " WHERE game_id=?"
            sql_args = (game_id,)
        else:
            where = " WHERE game_id IS NULL"

        cursor = self.__db.cursor()
        cursor.execute("SELECT id FROM npcs " + where, sql_args)
        npcs = cursor.fetchall()
        cursor.close()
        r = []
        for npc in npcs:
            tmp = NPC(npc['id'])
            r.append(tmp)
        return r
    
    def get_npc(self, key, game_id=None) -> dict:
        if isinstance(key, int):
            return NPC(key)
        elif isinstance(key, str):
            cursor = self.__db.cursor()
            sql = "SELECT id FROM npcs WHERE name=?"
            vars = (key,)
            if game_id is not None:
                sql += " AND game_id IS NULL OR game_id=?"
                vars = vars + (game_id,)
            else:
                sql += " AND game_id IS NULL"

            cursor.execute(sql, vars)

            row = cursor.fetchone()
            cursor.close()
            if row is None:
                return None
            return NPC(row['id'])
    
    def add_npc(self, name, attributes: dict = None) -> dict:
        cursor = self.__db.cursor()
        cursor.execute("INSERT INTO npcs (name) VALUES (?)", (name,))
        self.__db.commit()
        cursor.close()
        npc = NPC(cursor.lastrowid)
        if attributes is not None:
            npc.update(**attributes)
        return NPC(cursor.lastrowid)
    
    def delete_npc(self, id: int):
        cursor = self.__db.cursor()
        cursor.execute("DELETE FROM npcs WHERE id=?", (id,))
        self.__db.commit()
        cursor.close()
    
class NPC():
    __root_dir = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, id: int):
        self.id = id
        self.data = {}
        self.__db = sqlite3.connect(os.path.join(self.__root_dir, 'db.sqlite3'))
        self.__db.row_factory = sqlite3.Row
        self.cursor = self.__db.cursor()
        logging.debug("NPC: " + str(id))
        self.cursor.execute("SELECT * FROM npcs WHERE id = ?", (id,))

        row = self.cursor.fetchone()
        if row is None:
            raise Exception("NPC not found")
        for key in row.keys():
            self.data[key] = row[key]

        self.cursor.close()

    def update(self, race=None, npc_class=None, background=None, alignment=None, gender=None, age=None,
               height=None, weight=None, eyes=None, hair=None, eyes_description=None, hair_style=None,
               ears=None, nose=None, mouth=None, features=None, flaws=None, ideals=None, bonds=None,
               personality=None, mannerisms=None, talents=None, abilities=None, skills=None,
               languages=None, inventory=None, body=None, clothing=None, hands=None, jewelry=None,
               voice=None, attitude=None, deity=None, occupation=None, wealth=None, family=None,
               faith=None, summary=None, chin=None, name=None, game_id=None):
        
        query = "UPDATE npcs SET "
        vals = []
        params = locals()
        print (params)
        for k,v in params.items():
            if k == 'self' or k == 'id' or v is None or k == 'params' or k == 'query' or k == 'vals':
                continue
            query += k + "=?,"
            vals.append(v)
            self.data[k] = v
        query = query[:-1]
        query += " WHERE id=?"
        vals.append(self.data['id'])
        logging.debug(query)
        logging.debug(str(vals))
        cursor = self.__db.cursor()
        cursor.execute(query, vals)
        self.__db.commit()
        cursor.close()
        return self    
        
    def __del__(self):
        self.__db.close()

class GameNotes():
    __root_dir = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, game: str) -> None:
        self.game = game
        self.__db = sqlite3.connect(os.path.join(self.__root_dir, 'db.sqlite3'))
        self.__db.row_factory = sqlite3.Row

    def get_newest(self):
        cursor = self.__db.cursor()
        cursor.execute("SELECT id FROM games_notes WHERE game=? ORDER BY date DESC LIMIT 1", (self.game, ))
        note = cursor.fetchone()
        cursor.close()

        if note is None:
            return None        
        return GameNote(note['id'])
    
    def add(self, note, filename, summary):
        cursor = self.__db.cursor()
        cursor.execute('INSERT INTO games_notes (game, date, orig, summary) VALUES (?, ?, ?, ?);', (self.game, filename, note, summary))
        self.__db.commit()
        cursor.close()
        return GameNote(cursor.lastrowid)
    
    def __del__(self) -> None:
        self.__db.close()

class GameNote():
    __root_dir = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, id: int) -> None:
        self.__db = sqlite3.connect(os.path.join(self.__root_dir, 'db.sqlite3'))
        self.__db.row_factory = sqlite3.Row
        self.data = {}
        cursor = self.__db.cursor()
        cursor.execute("SELECT * FROM games_notes WHERE id = ?", (id,))

        row = cursor.fetchone()
        for key in row.keys():
            self.data[key] = row[key]

        cursor.close()

class Game():
    def __init__ (self, game: str) -> None:
        self.game = game
        self.__root_dir = os.path.dirname(os.path.abspath(__file__))
        self._db = sqlite3.connect(os.path.join(self.__root_dir, 'db.sqlite3'))
        self._db.row_factory = sqlite3.Row

        cursor = self._db.cursor()
        cursor.execute("SELECT * FROM games WHERE abbr = ?", (game,))
        row = cursor.fetchone()
        self.data = {}
        for key in row.keys():
            self.data[key] = row[key]
        cursor.close()