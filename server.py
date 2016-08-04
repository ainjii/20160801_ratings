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

STATUSES = {
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

    movie = get_movie_by_title(title)
    if not movie:
        flash_message("This movie doesn't exist yet.", STATUSES['red'])
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


def get_movie_by_title(title):
    """Returns a movie, given a title."""

    try:
        movie = Movie.query.filter_by(title=title).one()
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

    user = User.query.get(session['user_id'])
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
    """Round a number, if it exists. Else, return None."""

    if val:
        return round(val)
    else:
        return None


@app.route('/update_rating', methods=['POST'])
def update_rating():
    """Adding new or updating existing ratings in the db."""

    new_score = request.form.get('rating')
    title = request.form.get('title')

    if is_logged_in():
        user_id = db.session.query(User.user_id).filter_by(email=session['email']).one()

        try:
            movie_id = db.session.query(Movie.movie_id).filter_by(title=title).one()
        except NoResultFound:

            flash_message("This movie doesn't exist yet.", STATUSES['red'])
            return redirect("/movies")

        rating = db.session.query(Rating).filter_by(user_id=user_id, movie_id=movie_id).first()

        if rating:
            rating.score = new_score
        else:
            new_rating = Rating(movie_id=movie_id,
                                user_id=user_id,
                                score=new_score)
            db.session.add(new_rating)

        db.session.commit()

        flash_message("Your rating has been saved.", STATUSES['green'])

        redirect_url = "/movies/%s" % title
        return redirect(redirect_url)
    else:
        flash_message("Please sign in to submit a rating.", STATUSES['yellow'])
        return redirect("/register")


@app.route('/register', methods=['GET'])
def register_form():
    """Displays login/registration form."""

    if is_logged_in():
        flash_message("You're already logged in.", STATUSES['yellow'])

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
        response = log_user_in(user_email, password)
    except NoResultFound:
        response = add_user_to_db(user_email, password)

    return response


def log_user_in(email, password):
    """Tries to log user in."""

    user = db.session.query(User).filter_by(email=email).one()
    if user.password == password:
        add_session_info(user)
        flash_message("You were successfully logged in.", STATUSES['green'])
        redirect_url = get_user_profile_redirect_url(user.email)

        return redirect(redirect_url)
    else:
        flash_message("Incorrect password.", STATUSES['red'])

        return redirect("/register")


def add_user_to_db(email, password):
    """Adds a new user to the db."""

    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()

    add_session_info(user)
    flash_message("Account created.", STATUSES['green'])
    redirect_url = get_user_profile_redirect_url(user.email)

    return redirect(redirect_url)


def add_session_info(user):
    """Adds user email and user_id to session."""

    session['email'] = user.email
    session['user_id'] = user.user_id


@app.route('/logout')
def logout_user():
    """Logs user out and remove email from session."""

    if is_logged_in():
        remove_session_info()
        flash_message("You have been logged out.", STATUSES['green'])
        return redirect("/")
    else:
        flash_message("You're not logged in.", STATUSES['red'])
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

    if 'email' in session:
        return True
    else:
        return False


def get_user_profile_redirect_url(email):
    """Generates the URL to redirect users to their profile page."""

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

