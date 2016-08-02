"""Movie Ratings."""

from jinja2 import StrictUndefined

from flask import Flask, render_template, redirect, url_for, request, flash, session 
from flask_debugtoolbar import DebugToolbarExtension

from model import connect_to_db, db, User, Rating, Movie

from sqlalchemy.orm.exc import NoResultFound

app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

# Normally, if you use an undefined variable in Jinja2, it fails
# silently. This is horrible. Fix this so that, instead, it raises an
# error.
app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""

    return render_template("homepage.html")

@app.route('/users')
def user_list():
    """Show list of user."""

    users = User.query.all()
    return render_template("user_list.html", users=users)

@app.route('/register', methods=['GET'])
def register_form():
    """Displays login/registration form."""

    if session.get('email', None):
        flash("You're already logged in.")
        return redirect("/")
    else:
        return render_template("register_form.html")

@app.route('/process_registration', methods=["POST"])
def process_registration():
    """Check if user exists and redirect appropriately."""

    user_email = request.form.get('username')
    password = request.form.get('password')

    try:
        # log user in
        user = db.session.query(User).filter_by(email=user_email).one()
        if user.password == password:
            flash("You were successfully logged in.")

            session['email'] = user_email
            return redirect("/")
        else:
            flash("Incorrect password.")

            return redirect("register")
    except NoResultFound:
        # add user to db
        u = User(email=user_email, password=password)
        db.session.add(u)
        db.session.commit()

        flash("Account created.")
        session['email'] = u.email

        return redirect("/")

@app.route('/logout')
def logout_user():
    """Logs user out and remove email from session."""
    if 'email' in session:
        del session['email']
        flash("You have been logged out.")
        return redirect("/")
    else:
        flash("You're not logged in.")
        return redirect("/register")


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run()
