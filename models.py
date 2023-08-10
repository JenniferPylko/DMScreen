import mysql.connector
import logging
import os
import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.callbacks import get_openai_callback
from openaihandler import OpenAIHandler
from pydantic import BaseModel, Field
from typing import List
import datetime
import random

logging.basicConfig(level=logging.DEBUG)

class NotesQuery(BaseModel):
    summary: str = Field(description="A summary of the provided sesison notes")
    nouns: List[str] = Field(description="A list of people's proper names in the answer. Do not include locations, spells nor groups of people")

class Model():
    def __init__(self) -> None:
        self._root_dir = os.path.dirname(os.path.abspath(__file__))
        #self.__db = sqlite3.connect(os.path.join(self.__root_dir, 'db.sqlite3'))
        #self.__db.row_factory = sqlite3.Row
        self._db = mysql.connector.connect(
            host = os.getenv("MYSQL_HOST"),
            user = os.getenv("MYSQL_USER"),
            password = os.getenv("MYSQL_PASS"),
            database = os.getenv("MYSQL_DB")
        )
        self._table = None

    def __del__(self) -> None:
        self._db.close()

    def get_row(self, query: str, params: tuple = ()) -> dict:
        cursor = self._db.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        cursor.close()

        # Convert to dict
        if row is not None:
            row = dict(zip(cursor.column_names, row))

        return row
    
    def get_array(self, query: str, params: tuple = ()) -> list:
        cursor = self._db.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for i, row in enumerate(rows):
            rows[i] = row[0]
        cursor.close()
        return rows
    
    def do_insert(self, query: str, params: tuple = None) -> None:
        cursor = self._db.cursor()
        try:
            cursor.execute(query, params)
        except Exception as e:
            logging.error("Error inserting into database: "+str(e))
            logging.error("Query: "+query)
            logging.error("Params: "+str(params))
            raise e
        self._db.commit()
        lastrowid = cursor.lastrowid
        cursor.close()
        return lastrowid

    def delete_row(self, table: str, id: int) -> None:
        cursor = self._db.cursor()
        logging.debug(f"DELETE FROM {table} WHERE id={id}")
        cursor.execute(f"DELETE FROM {table} WHERE id=%s", (id,))
        self._db.commit()
        cursor.close()

    def update_row(self, query: str, params: tuple = None) -> None:
        cursor = self._db.cursor()
        cursor.execute(query, params)
        self._db.commit()
        cursor.close()

class NPCs(Model):
    def __init__(self, game_id:int) -> None:
        super().__init__()
        self.__game_id = game_id

    def get_all(self) -> list:
        where = ""
        sql_args = ()
        if self.__game_id is not None:
            where = " WHERE game_id=%s"
            sql_args = (self.__game_id,)
        else:
            where = " WHERE game_id IS NULL"

        cursor = self._db.cursor()
        cursor.execute("SELECT id FROM npcs " + where, sql_args)
        npcs = cursor.fetchall()
        cursor.close()
        return [NPC(npc[0]) for npc in npcs]
    
    def add_npc(self, name, attributes: dict = None) -> dict:
        id = self.do_insert("INSERT INTO npcs (name) VALUES (%s)", (name,))
        npc = NPC(id)
        if attributes is not None:
            attributes['placeholder'] = attributes.get('placeholder') or True
            npc.update(**attributes)
        return npc
    
    def delete_npc(self, id: int):
        self.delete_row('npcs', id)
    
    def get_npc_by_name(self, name: str):
        id = self.get_row("SELECT id FROM npcs WHERE name=%s", (name,))
        return NPC(id) if id is not None else None

class NPC(Model):
    def __init__(self, id: int):
        super().__init__()
        self.id = id
        self.data = self.get_row("SELECT * FROM npcs WHERE id = %s", (id,))

    def update(self, race=None, class_=None, background=None, alignment=None, gender=None, age=None,
               height=None, weight=None, eyes=None, hair=None, eyes_description=None, hair_style=None,
               ears=None, nose=None, mouth=None, features=None, flaws=None, ideals=None, bonds=None,
               personality=None, mannerisms=None, talents=None, abilities=None, skills=None,
               languages=None, inventory=None, body=None, clothing=None, hands=None, jewelry=None,
               voice=None, attitude=None, deity=None, occupation=None, wealth=None, family=None,
               faith=None, summary=None, chin=None, name=None, game_id=None, placeholder=None):
        
        query = "UPDATE npcs SET "
        vals = []
        params = locals().copy()
        for k,v in params.items():
            if k == 'self' or k == 'id' or v is None or k == 'params' or k == 'query' or k == 'vals':
                continue
            query += k + "=%s,"
            vals.append(v)
            self.data[k] = v
        query = query[:-1]
        query += " WHERE id=%s"
        vals.append(self.data['id'])

        self.update_row(query, tuple(vals))
        return self    

class GameNotes(Model):
    def __init__(self, game: str) -> None:
        super().__init__()
        self.game = game
        self.__notes_parser = PydanticOutputParser(pydantic_object=NotesQuery)
        self.__notes_prompt = PromptTemplate(
            template="""You are a High Fantasy Storyteller, like George R.R. Martin, Robert Jordan,
            or J.R.R. Tolkein. Give me a summary of the following game session notes as though they
            were a part of an epic story. Including any important NPCs, locations, and events.
            
            {format_instructions}
            
            {notes}""",
            input_variables=["notes"],
            partial_variables={"format_instructions": self.__notes_parser.get_format_instructions()}
        )

    def get_newest(self):
        note = self.get_row("SELECT id FROM games_notes WHERE game=%s ORDER BY date DESC LIMIT 1", (self.game,))
        return GameNote(note['id']) if note is not None else None
    
    def get_by_date(self, date:str):
        note = self.get_row("SELECT id FROM games_notes WHERE game=%s AND date=%s", (self.game, date))
        return GameNote(note['id']) if note is not None else None
    
    def preprocess_and_add(self, note, date, user_id):
        summary:NotesQuery = self._preprocess(note, user_id)
        return self.add(note, date, summary.summary)
    
    def add(self, note, date, summary):
        id = self.do_insert('INSERT INTO games_notes (game, date, orig, summary) VALUES (%s, %s, %s, %s);', (self.game, date, note, summary))
        return GameNote(id)
    
    def get_all(self):
        notes = self.get_array("SELECT id FROM games_notes WHERE game=%s ORDER BY date DESC", (self.game,))
        for i, note_id in enumerate(notes):
            notes[i] = GameNote(note_id)
        return notes
    
    def get_dates(self):
        dates = self.get_array("SELECT date FROM games_notes WHERE game=%s ORDER BY date DESC", (self.game,))
        return dates
    
    def _preprocess(self, note, user_id, temperature=0.5, model=OpenAIHandler.MODEL_GPT3):
        _input = self.__notes_prompt.format_prompt(notes=note)
        messages = _input.to_messages()

        chat = ChatOpenAI(model_name=model, temperature=temperature)
        logging.debug("Sending prompt to OpenAI using model: "+model+"\n\n"+_input.to_messages().pop().content)
        with get_openai_callback() as cb:
            answer = chat(_input.to_messages())
            TokenLog().add("Add Game Notes", cb.prompt_tokens, cb.completion_tokens, cb.total_cost, user_id)
        logging.debug("Received answer from OpenAI: "+answer.content+"\n\nType: "+str(type(answer)))

        parsed_answer = ""
        try:
            parsed_answer = self.__notes_parser.parse(answer.content)
        except:
            if (type(answer) == str):
                try:
                    parsed_answer = NotesQuery(answer=json.loads(answer), nouns=[])
                except:
                    parsed_answer = NotesQuery(answer=answer, nouns=[])
            else:
                content = json.loads(answer.content)
                parsed_answer = NotesQuery(summary=content["summary"], nouns=[])

        return parsed_answer
    
class GameNote(Model):
    def __init__(self, id: int = None, date:str = None) -> None:
        super().__init__()
        if id is None and date is None:
            raise Exception("Either id or date must be provided")
        
        where = ""
        where_args = ()

        if id is not None:
            where = " WHERE id=%s"
            where_args = (id,)
        elif date is not None:
            where = " WHERE date=%s"
            where_args = (date,)

        self.data=self.get_row("SELECT * FROM games_notes "+where, where_args)         

    def update(self, note) -> None:
        return self.update_row("UPDATE games_notes SET orig=%s WHERE id=%s", (note, self.data['id']))
    
    def update_date(self, date) -> None:
        return self.update_row("UPDATE games_notes SET date=%s WHERE id=%s", (date, self.data['id']))

    def delete(self) -> None:
        return self.delete_row('games_notes', self.data['id'])

class Games(Model):
    def __init__(self) -> None:
        super().__init__()
    
    def get_all(self):
        games = self.get_array("SELECT id FROM games ORDER BY name ASC")
        for i, game in enumerate(games):
            games[i] = Game(game)
        return games

    def get_by_owner(self, owner_id):
        games = self.get_array("SELECT id FROM games WHERE owner_id=%s ORDER BY name ASC", (owner_id,))
        for i, game in enumerate(games):
            games[i] = Game(game)
        return games

    def add(self, name, abbr, owner_id):
        id = self.do_insert("INSERT INTO games (abbr, name, owner_id) VALUES (%s, %s, %s)", (abbr, name, owner_id))
        return Game(id)
    
    def delete(self, abbr):
        cursor = self._db.cursor()
        cursor.execute("DELETE FROM games WHERE abbr=%s", (abbr,))
        self._db.commit()
        cursor.close()

class Game(Model):
    def __init__ (self, game: int) -> None:
        super().__init__()
        self.game = game
        self.data = self.get_row("SELECT * FROM games WHERE id = %s", (game,))        

class PlotPoints(Model):
    def __init__(self, game_id: int) -> None:
        super().__init__()
        self.game_id = game_id

    def get_all(self):
        cursor = self._db.cursor()
        cursor.execute("SELECT id FROM plotpoints WHERE game_id = %s", (self.game_id,))
        rows = cursor.fetchall()
        cursor.close()
        r = []
        for row in rows:
            r.append(PlotPoint(row['id']))
        return r
    
    def add(self, game_id, title, details=None):
        date_new = datetime.datetime.now()
        cursor = self._db.cursor()
        cursor.execute("INSERT INTO plotpoints (game_id, title, details, date_new, date_mod, status) VALUES (%s, %s, %s, %s, %s, %s)", (game_id, title, details, date_new, date_new, "NEW"))
        self._db.commit()
        cursor.close()
        return PlotPoint(cursor.lastrowid)
    
class PlotPoint(Model):
    def __init__(self, id: int) -> None:
        super().__init__()
        self.id = id
        self.data = self.get_row("SELECT * FROM plotpoints WHERE id = %s", (id,))

class Reminders(Model):
    def __init__(self, game_id:int) -> None:
        super().__init__()
        self.game_id = game_id
    
    def get_all(self):
        cursor = self._db.cursor()
        cursor.execute("SELECT id FROM reminders WHERE game_id = %s", (self.game_id,))
        rows = cursor.fetchall()
        cursor.close()
        r = []
        for row in rows:
            r.append(Reminder(row[0]))
        return r
    
    def add(self, title, details, trigger):
        id = self.do_insert("INSERT INTO reminders (game_id, title, details, trigger_) VALUES (%s, %s, %s, %s)", (self.game_id, title, details, trigger))
        return Reminder(id)
    
class Reminder(Model):
    def __init__(self, id: int) -> None:
        super().__init__()
        self.id = id
        self.data = self.get_row("SELECT * FROM reminders WHERE id = %s", (id,))
    
    def delete(self):
        return self.delete_row('reminders', self.id)

class TokenLog(Model):
    def __init__(self) -> None:
        super().__init__()

    def add(self, query_type: str, prompt_tokens: int, completion_tokens: int, cost: float, user: int):
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.do_insert("INSERT INTO log_tokens (query_type, prompt_tokens, completion_tokens, cost, date_new, user_id) VALUES (%s, %s, %s, %s, %s, %s)", (query_type, prompt_tokens, completion_tokens, cost, date, user))

class Users(Model):
    def __init__(self) -> None:
        super().__init__()

    def add(self, email, password):
        date_new = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        verify = random.randint(100000, 999999)

        # First make sure this doesn't already exist, so we don't throw a duplicate key error
        user = self.get_by_email(email)
        if user is not None:
            return user

        id = self.do_insert("INSERT INTO users (email, password, date_new, verify) VALUES (%s, %s, %s, %s)", (email, password, date_new, verify))
        return User(id)
    
    def get_by_email(self, email):
        user = self.get_row("SELECT id FROM users WHERE email=%s", (email,))
        return User(user['id']) if user is not None else None

    def get_by_stripe_invoice_id(self, stripe_invoice_id):
        user = self.get_row("SELECT id FROM users WHERE stripe_invoice_id=%s", (stripe_invoice_id,))
        return User(user['id']) if user is not None else None

    def count(self) -> int:
        return self.get_row("SELECT COUNT(*) AS count FROM users")['count']

class User(Model):
    def __init__(self, id: int) -> None:
        super().__init__()
        self.id = id
        self.data = self.get_row("SELECT * FROM users WHERE id = %s", (id,))

    def pre_reset_password(self):
        reset = random.randint(100000, 999999)
        cursor = self._db.cursor()
        cursor.execute("UPDATE users SET reset=%s WHERE id=%s", (reset, self.id))
        self._db.commit()
        cursor.close()
        self.data['reset'] = reset
        return reset
    
    def update(self, email=None, password=None, verify=None, reset=None,
               stripe_invoice_id=None, membership=None, stripe_subscription_id=None,
               stripe_customer_id=None):
        params = locals().copy()
        query = "UPDATE users SET "
        vals = []
        for k,v in params.items():
            if k == 'self' or k == 'id' or v is None:
                continue
            query += k + "=%s,"
            vals.append(v)
            self.data[k] = v
        query = query[:-1]
        query += " WHERE id=%s"
        vals.append(self.data['id'])
        logging.debug(query)
        logging.debug(str(vals))
        cursor = self._db.cursor()
        cursor.execute(query, vals)
        self._db.commit()
        cursor.close()
        return self  

class Tasks(Model):
    def __init__(self) -> None:
        super().__init__()
    
    def add(self, game_id: int, name: str, status:str="Queued"):
        date_new = datetime.datetime.now()
        id = self.do_insert("INSERT INTO tasks (game_id, name, status, date_new, date_mod) VALUES (%s, %s, %s, %s, %s)", (game_id, name, status, date_new, date_new))
        return Task(id)

class Task(Model):
    def __init__(self, id: int) -> None:
        super().__init__()
        self.id = id
        self.data = self.get_row("SELECT * FROM tasks WHERE id = %s", (id,))

    def update(self, name=None, status=None, message=None):
        params = locals().copy()
        date_mod = datetime.datetime.now()
        query = "UPDATE tasks SET date_mod=%s,"
        vals = [date_mod]
        for k,v in params.items():
            if k == 'self' or k == 'id' or v is None:
                continue
            query += k + "=%s,"
            vals.append(v)
            self.data[k] = v
        query = query[:-1]
        query += " WHERE id=%s"
        vals.append(self.data['id'])
        logging.debug(query)
        logging.debug(str(vals))
        cursor = self._db.cursor()
        cursor.execute(query, vals)
        self._db.commit()
        cursor.close()
        return self

class Waitlist(Model):
    def __init__(self) -> None:
        super().__init__()
    
    def add(self, email: str):
        date_new = datetime.datetime.now()
        id = self.do_insert("INSERT INTO waitlist (email, date_new) VALUES (%s, %s)", (email, date_new))
        return id
