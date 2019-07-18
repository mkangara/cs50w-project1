import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
DATABASE_URL = "postgres://syfavtixrvalbk:e6493cc91094e6d1bb0498589c257d2eaf589e394101c8d9153455035ade26fd@ec2-174-129-240-67.compute-1.amazonaws.com:5432/d40ujt7n3e1ri8"

engine = create_engine(os.getenv("DATABASE_URL")) # database engine object from SQLAlchemy that manages connections to the database
db = scoped_session(sessionmaker(bind=engine)) #create a 'scoped session' that ensures different users' interactions with the database are kept separate

f = open("books.csv")
reader = csv.reader(f)
for isbn, title, author, year in reader: # loop gives each column a name
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
    {"isbn":isbn, "title":title, "author":author, "year":year}) # substitute values from CSV line into SQL command, as per this dict
    print(f" {isbn} Title: {title} by {author} printed in {year} added ")
db.commit()
