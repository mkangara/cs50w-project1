import os
import requests

from flask import Flask, session, render_template, request, url_for, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
# Add DATABASE_URL environment variable by using "set on the command line"
# DATABASE_URL = "postgres://syfavtixrvalbk:e6493cc91094e6d1bb0498589c257d2eaf589e394101c8d9153455035ade26fd@ec2-174-129-240-67.compute-1.amazonaws.com:5432/d40ujt7n3e1ri8"
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

@app.route("/", methods=["GET","POST"])
def RegistrationForm():
    session["user_id"] = None

    return render_template('registerForm.html')

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    if password == confirm_password:
        # check if user already exists
        if db.execute("SELECT * FROM users WHERE (username = :username)", {"username":username}).rowcount != 0:
            return render_template("error.html", message="username already exists", gohere="/" )
        else:
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                {"username":username, "password":password})
            db.commit()
        return render_template("success_register.html", username=username ) # once registered go to update database
    else:
        return  redirect(url_for(RegistrationForm))
    # create an instance of the RegistrationForm which was created in the Forms.py file
    # pass the instance to the register.html template@app.route("/login")
# @app.route("/user_data", methods={"POST"})

@app.route("/loginForm", methods=["GET","POST"])
def loginForm():
    # create an instance of the loginForm which was created in the Forms.py file
    # pass the instance to the login.html template
    # once logged in go to the search page
    return render_template('loginForm.html')

@app.route("/verifylogin", methods=["POST"])
def verifylogin():
    #get user information
    username = request.form.get("username")
    password = request.form.get("password")
    if db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username":username, "password":password}).rowcount == 0:
        return render_template("error.html", message="Invalid username", gohere="/loginForm")
    else:
        user = db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).fetchone()
        session["user_id"]=user.id
        return redirect(url_for("search"))


@app.route("/search", methods=["POST", "GET"])
def search():
    # check if user is logged in
    try:
        if session["user_id"] == None:
            return redirect(url_for("loginForm"))
        return render_template("searchpage.html")
    except KeyError:
        return render_template("error.html", message="Please login", gohere="/loginForm")

@app.route("/book_search", methods=["POST"])
def book_search():
    query = request.form.get("searchbook")
    query = "%"+query+"%" # concatenate wild card to search for matches when the isbn is a few characters

    books = db.execute("SELECT * FROM books WHERE (isbn LIKE :stext) OR (title LIKE :stext) OR (author LIKE :stext)", {"stext":query}).fetchall()
        #check if book exists
    if books is None:
        return render_template("error.html", message="No such book", gohere="/searchpage") #if book does not exist return to searchpage
    return render_template("searchpage.html", books=books)     #if book exists pass the list to searchpage

    #    return render_template("bookreview.html", book=book)
@app.route("/bookreview/<book_isbn>")
def bookreview(book_isbn):
    if session["user_id"] != None:
        book_info= db.execute("SELECT * FROM books WHERE isbn = :book_isbn", {"book_isbn":book_isbn}).fetchone()
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"8qIcqhBcOM7c6YqBYm3g","isbns":book_isbn})
        data = res.json()
        rate = data['books'][0]['average_rating']
    # check if book has been reviewed. if record does not exist insert initial isbn number and zero all counters
        if db.execute("SELECT ratings_id FROM bookreviews WHERE ratings_id = :ratings_id", {"ratings_id":book_isbn}).fetchone() == None:
            db.execute("INSERT INTO bookreviews (ratings_id, ratings_count, total_rating, average_rating) VALUES (:ratings_id, :zero, :zero, :zero)", {"ratings_id":book_isbn, "zero":0})
            db.commit()
        my_rate = db.execute("SELECT average_rating FROM bookreviews WHERE ratings_id=:ratings_id", {"ratings_id" :book_isbn}).fetchone()
#        return (f"{my_rate}")
        return render_template("bookreview.html", rate=rate, book_info=book_info, my_rate=my_rate[0])
    else:
        return redirect(url_for("loginForm"))

@app.route("/bookrating/<book_isbn>", methods=['POST','GET'])
def bookrating(book_isbn):
    #check session exists
    if session["user_id"] == None:
        return redirect(url_for("loginForm"))
    # compute the rating and update the database
    userRating = request.form.get("rating")
    sumRating = db.execute("SELECT total_rating FROM bookreviews WHERE ratings_id = :ratings_id", {"ratings_id":book_isbn}).fetchone()
    reviewers = db.execute("SELECT ratings_count FROM bookreviews WHERE ratings_id = :ratings_id", {"ratings_id":book_isbn}).fetchone()
# output from above db execute is a tuple. To get integer index the 1st element in the tuple
    reviewers = reviewers[0] + 1
    sumRating = sumRating[0] + int(userRating)
    average_rating = sumRating / reviewers
    db.execute("UPDATE bookreviews SET average_rating = :average_rating, total_rating = :sumRating, ratings_count = :reviewers WHERE ratings_id = :ratings_id", {"average_rating" :average_rating, "sumRating" :sumRating, "reviewers":reviewers, "ratings_id":book_isbn})
    db.commit()
    return redirect(url_for("bookreview",book_isbn=book_isbn))

@app.route("/api/<book_isbn>")
def book_api(book_isbn):
    # make sure book exists
    book_info= db.execute("SELECT * FROM books WHERE isbn = :book_isbn", {"book_isbn":book_isbn}).fetchone()
    if book_info == None:
        return jsonify({"error": "Invalid isbn number"}), 422
    # get book information from both books and bookreview tables
    book_info= db.execute("SELECT * FROM books INNER JOIN bookreviews ON books.isbn=bookreviews.ratings_id WHERE isbn = :book_isbn", {"book_isbn":book_isbn}).fetchone()

    return jsonify({
    "title": book_info.title,
    "author": book_info.author,
    "year": book_info.year,
    "isbn": book_info.isbn,
    "review_count": book_info.ratings_count,
    "average_score": book_info.average_rating
    })



if __name__ == "__main__":
    app.run(debug=True)
