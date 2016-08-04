"""Models and database functions for Ratings project."""

from flask_sqlalchemy import SQLAlchemy
import correlation
# This is the connection to the PostgreSQL database; we're getting this through
# the Flask-SQLAlchemy helper library. On this, we can find the `session`
# object, where we do most of our interactions (like committing, etc.)

db = SQLAlchemy()


##############################################################################
# Model definitions

class User(db.Model):
    """User of ratings website."""

    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<User user_id=%s email=%s>" % (self.user_id,
                                               self.email)
        
    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String(64), nullable=True)
    password = db.Column(db.String(64), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    zipcode = db.Column(db.String(15), nullable=True)


    def get_predicted_rating(self, movie_id):
        """Predict a user's rating for a movie based on other users' ratings."""

        movie = db.session.query(Movie).filter_by(movie_id=movie_id).one()
        ratings = movie.ratings
        user_sim_and_score_pairs = [(self.similarity(rating.user), rating) 
                                    for rating in ratings]

        user_sim_and_score_pairs.sort(reverse=True)
        similarity, rating = user_sim_and_score_pairs[0]

        numerator = sum([rating.score * sim for sim, rating in user_sim_and_score_pairs])
        denominator = sum([sim for sim, r in user_sim_and_score_pairs])

        if denominator != 0:
            return numerator/denominator
        else:
            return None

    def similarity(self, other_user):
        """Determine how similar two users' tastes in movies are."""

        pairs = []
        my_ratings = User.generate_dict_of_ratings(self)
        other_ratings = User.generate_dict_of_ratings(other_user)

        for movie_id, my_score in my_ratings.iteritems():
            other_rating = other_ratings.get(movie_id)
            if other_rating:
                pairs.append((my_score, other_rating))

        if pairs:
            return correlation.pearson(pairs)
        else:
            return 0


    @staticmethod
    def generate_dict_of_ratings(user):
        """Generate a dictionary of movie_id:rating pairs."""

        user_ratings = {}

        for rating in user.ratings:
            user_ratings[rating.movie_id] = rating.score

        return user_ratings


class Movie(db.Model):
    """Movies to be rated."""

    __tablename__ = "movies"

    movie_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    released_at = db.Column(db.DateTime, nullable=True)
    imdb_url = db.Column(db.String(512), nullable=False)


class Rating(db.Model):
    """User written movie ratings."""

    __tablename__ = "ratings"

    rating_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.movie_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)

    user = db.relationship("User", backref=db.backref("ratings", order_by=rating_id))
    movie = db.relationship("Movie", backref=db.backref("ratings", order_by=rating_id))

    def __repr__(self):
        """Provide helpful representation when printed."""

        s = "<Rating rating_id=%s movie_id=%s user_id=%s score=%s>"
        return s % (self.rating_id, self.movie_id, self.user_id,
                    self.score)


##############################################################################
# Helper functions

def connect_to_db(app):
    """Connect the database to our Flask app."""

    # Configure to use our PstgreSQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///ratings'
    app.config['SQLALCHEMY_ECHO'] = True
    # app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

    db.app = app
    db.init_app(app)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print "Connected to DB."
