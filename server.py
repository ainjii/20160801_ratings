"""Movie Ratings."""

from jinja2 import StrictUndefined

from flask import Flask, render_template, redirect, request, flash, session
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

ALERT_TYPES = {
    'blue': 'info',
    'red': 'danger',
    'yellow': 'warning',
    'green': 'success'
}

BERATEMENT_MESSAGES = [
        "I suppose you don't have such bad taste after all.",
        "I regret every decision that I've ever made that has " +
            "brought me to listen to your opinion.",
        "Words fail me, as your taste in movies has clearly " +
            "failed you.",
        "That movie is great. For a clown to watch. Idiot.",
        "Words cannot express the awfulness of your taste."
    ]


@app.route('/')
def index():
    """Homepage."""

    return render_template("homepage.html")


@app.route('/users')
def users():
    """Show list of user."""

    users = User.query.all()
    return render_template("users.html", users=users)


@app.route('/users/<user_id>')
def user_profile(user_id):
    """Displays user's details"""

    user = get_user_by_id(user_id)

    if user:
        return render_template("user_profile.html", user=user)
    else:
        flash_message('That user does not exist.', ALERT_TYPES['red'])
        return redirect('/')


def get_user_by_id(user_id):
    """Return a user, given a user_id."""

    try:
        return User.query.get(user_id)
    except NoResultFound:
        return None


@app.route('/movies')
def movies():
    """Show list of movies."""

    movies = Movie.query.order_by('title').all()

    return render_template("movies.html", movies=movies)


@app.route('/movies/<movie_id>')
def movie_details(movie_id):
    """Displays movie details."""

    movie = get_movie_by_id(movie_id)
    if not movie:
        flash_message("This movie doesn't exist yet.", ALERT_TYPES['red'])
        return redirect('/movies')

    user_rating = None
    prediction = None

    if is_logged_in():
        user_rating = get_rating_by_movie_id(movie.movie_id)

        if not user_rating:
            prediction = get_prediction_of_user_rating(movie)

    avg_rating = get_average_rating_for_movie(movie)
    effective_rating = get_effective_rating(prediction, user_rating)
    eye_rating = get_eye_rating(movie)
    beratement = fetch_insult(effective_rating, eye_rating)

    return render_template("movie_details.html",
                           movie=movie,
                           ratings=movie.ratings,
                           prediction=prediction,
                           average=avg_rating,
                           eye_rating=eye_rating,
                           beratement=beratement)


def get_movie_by_id(movie_id):
    """Returns a movie, given an id."""

    try:
        movie = Movie.query.get(movie_id)
        return movie
    except NoResultFound:
        return None


def get_rating_by_movie_id(movie_id):
    """Returns a Movie, given a movie_id."""

    try:
        user_id = session['user_id']
        rating = Rating.query.filter_by(movie_id=movie_id, user_id=user_id).first()
        return rating
    except NoResultFound:
        return None


def get_average_rating_for_movie(movie):
    """Returns the average user rating for a particular movie."""

    rating_score = [rating.score for rating in movie.ratings]
    avg_rating = float(sum(rating_score)) / len(rating_score)

    return safe_round(avg_rating)


def get_prediction_of_user_rating(movie):
    """Returns what a user will probably rate a movie they have not yet seen."""

    prediction = None

    user = get_user_by_id(session['user_id'])
    prediction = user.get_predicted_rating(movie.movie_id)

    return safe_round(prediction)


def get_effective_rating(prediction, user_rating):
    """Returns a value that represents the user's [likely] opinion of a movie."""

    if prediction:
        return prediction
    elif user_rating:
        return user_rating.score
    else:
        return None


def get_eye_rating(movie):
    """Returns a value that represents the eye's [likely] opinion of a movie."""

    the_eye = User.query.filter_by(email='the-eye@of-judgment.com').one()
    eye_rating = Rating.query.filter_by(user_id=the_eye.user_id, movie_id=movie.movie_id).first()

    if eye_rating is None:
        eye_rating = the_eye.get_predicted_rating(movie.movie_id)
    else:
        eye_rating = eye_rating.score

    return safe_round(eye_rating)


def fetch_insult(effective_rating, eye_rating):
    """Return the appropriate beratement based on differences in eye rating and user rating."""

    difference = None
    beratement = None

    if eye_rating and effective_rating:
        difference = abs(eye_rating - effective_rating)

    if difference:
        beratement = BERATEMENT_MESSAGES[int(difference)]

    return beratement


def safe_round(val):
    """Round a number, if it exists. Else, return None.

    >>> safe_round(5.0)
    5.0

    >>> safe_round(6.789)
    7.0

    """

    number_types = (float, int, complex, long)

    if isinstance(val, number_types):
        return round(val)
    else:
        return None


@app.route('/update_rating', methods=['POST'])
def update_rating():
    """Adding new or updating existing ratings in the db."""

    new_score = request.form.get('rating')
    movie_id = request.form.get('movieId')

    if is_logged_in():
        movie = get_movie_by_id(movie_id)

        if movie:
            update_rating_in_db(movie.movie_id, new_score)

            flash_message("Your rating has been saved.", ALERT_TYPES['green'])
            redirect_url = "/movies/%s" % movie_id

            return redirect(redirect_url)
        else:
            flash_message("This movie doesn't exist yet.", ALERT_TYPES['red'])
            return redirect("/movies")
    else:
        flash_message("Please sign in to submit a rating.", ALERT_TYPES['yellow'])
        return redirect("/register")


def update_rating_in_db(movie_id, new_score):
    """Update a user's rating if it exists, if not, create a new rating."""

    rating = get_rating_by_movie_id(movie_id)
    user_id = session['user_id']

    if rating:
        rating.score = new_score
    else:
        new_rating = Rating(movie_id=movie_id,
                            user_id=user_id,
                            score=new_score)
        db.session.add(new_rating)

    db.session.commit()


@app.route('/register', methods=['GET'])
def register():
    """Displays login/registration form."""

    if is_logged_in():
        flash_message("You're already logged in.", ALERT_TYPES['yellow'])
        redirect_url = "/users/%s" % session['user_id']

        return redirect(redirect_url)
    else:
        return render_template("register.html")


@app.route('/process_registration', methods=["POST"])
def process_registration():
    """Check if user exists and redirect appropriately."""

    user_email = request.form.get('username')
    password = request.form.get('password')

    try:
        response = log_user_in(user_email, password)
    except NoResultFound:
        response = add_user_to_db(user_email, password)

    return response


def log_user_in(email, password):
    """Tries to log user in."""

    user = db.session.query(User).filter_by(email=email).one()
    if user.password == password:
        add_session_info(user)
        flash_message("You were successfully logged in.", ALERT_TYPES['green'])
        redirect_url = "/users/%s" % session['user_id']

        return redirect(redirect_url)
    else:
        flash_message("Incorrect password.", ALERT_TYPES['red'])

        return redirect("/register")


def add_user_to_db(email, password):
    """Adds a new user to the db."""

    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()

    add_session_info(user)
    flash_message("Account created.", ALERT_TYPES['green'])
    redirect_url = "/users/%s" % session['user_id']

    return redirect(redirect_url)


def add_session_info(user):
    """Adds user email and user_id to session."""

    session['email'] = user.email
    session['user_id'] = user.user_id


@app.route('/logout')
def logout():
    """Logs user out and remove email from session."""

    if is_logged_in():
        remove_session_info()
        flash_message("You have been logged out.", ALERT_TYPES['green'])
        return redirect("/")
    else:
        flash_message("You're not logged in.", ALERT_TYPES['red'])
        return redirect("/register")


def remove_session_info():
    """Removes user info from session."""

    del session['email']
    del session['user_id']


def flash_message(msg, status):
    """Creates a stylized flash message."""

    formatted_msg = '<div class="alert alert-%s" role="alert">%s</div>' % (status, msg)
    flash(formatted_msg)


def is_logged_in():
    """Determines whether a user is logged in."""

    if ('email' in session) and ('user_id' in session):
        return True
    else:
        return False


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run()

