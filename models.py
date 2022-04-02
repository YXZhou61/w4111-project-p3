from flask_login import UserMixin
from typing import Dict, Optional
import psycopg2
import os

def get_db_connection():
    conn = psycopg2.connect(host=os.environ['DB_HOST'],
                            database=os.environ['DB_NAME'],
                            user=os.environ['DB_USERNAME'],
                            password=os.environ['DB_PASSWORD'])
    return conn

Users: Dict[str, "User"] = {}

    
    
class User(UserMixin):
    def __init__(self, id: str, name: str, phone: str, password: str):
        self.id = id
        self.name = name
        self.phone = phone
        self.password = password

    @staticmethod
    def get(user_id: str) -> Optional["User"]:
        return Users.get(user_id)

    def __str__(self) -> str:
        return f"<Id: {self.id}, Username: {self.name}, Phone: {self.phone}>"

    def __repr__(self) -> str:
        return self.__str__()


conn = get_db_connection()
cur = conn.cursor()
cur.execute(
        """
        SELECT * 
        FROM Users
        """
    )

users = cur.fetchall()

for user in users:
    Users[user[0]] = User(
        id=user[0],
        name=user[1],
        phone = user[2],
        password=user[3],
    )