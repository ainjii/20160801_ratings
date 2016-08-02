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


@app.route('/users/<user_id>')
def user_profile(user_id):
    """Displays user's details"""

    try:
        user = User.query.filter_by(user_id=user_id).one()
    except NoResultFound:
        return redirect('/register')

    ratings = Rating.query.filter_by(user_id=user_id).all()

    return render_template("profile.html", user=user, ratings=ratings)


@app.route('/movies')
def movie_list():
    """Show list of movies."""
    
    movies = Movie.query.order_by('title').all()
    
    return render_template("movie_list.html", movies=movies)

@app.route('/movies/<title>')
def movie_details(title):
    """Displays movie details."""

    try:
        movie = Movie.query.filter_by(title=title).one()
    except NoResultFound:
        return redirect('/movies')

    return render_template("movie_details.html", movie=movie, ratings=movie.ratings)


@app.route('/update_rating', methods=['POST'])
def update_rating():

    new_score = request.form.get('rating')
    title = request.form.get('title')

    if is_logged_in():
        user_id = db.session.query(User.user_id).filter_by(email=session['email']).one()
        rating = db.session.query(Rating).filter_by(user_id=user_id).one()
        if rating.score:
            rating.score = new_score
            db.session.commit()
    else:
        redirect("/register")

    

@app.route('/register', methods=['GET'])
def register_form():
    """Displays login/registration form."""

    if is_logged_in():
        flash("You're already logged in.")
        redirect_url = get_user_profile_redirect_url(session['email'])

        return redirect(redirect_url)
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

            session['email'] = user.email
            redirect_url = get_user_profile_redirect_url(user.email)

            return redirect(redirect_url)
        else:
            flash("Incorrect password.")

            return redirect("/register")
    except NoResultFound:
        # add user to db
        u = User(email=user_email, password=password)
        db.session.add(u)
        db.session.commit()

        flash("Account created.")
        session['email'] = u.email
        redirect_url = get_user_profile_redirect_url(u.email)

        return redirect(redirect_url)

@app.route('/logout')
def logout_user():
    """Logs user out and remove email from session."""
    if is_logged_in():
        del session['email']
        flash("You have been logged out.")
        return redirect("/")
    else:
        flash("You're not logged in.")
        return redirect("/register")


def is_logged_in():
    """Determines whether a user is logged in."""

    if 'email' in session:
        return True
    else:
        return False


def get_user_profile_redirect_url(email):
    user_id = db.session.query(User.user_id).filter_by(email=email).one()
    redirect_url = "/users/%s" % user_id

    return redirect_url


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run()
