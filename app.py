# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for, abort, jsonify
from flask import Response
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
from flask_migrate import Migrate

from datetime import datetime
import re

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

# connect to a local postgresql database
migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

# A table to hold genres
class Genre(db.Model):
    __tablename__ = 'Genre'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


# Artist Genre table with a many to many relationship between Genre and Artist
# The content here is restricted by the inputs in forms.py
artist_genre_table = db.Table('artist_genre_table',
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
    db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True)
)


# Venue Genre table with a many to many relationship between Genre and Venue
# The content here is restricted by the inputs in forms.py
venue_genre_table = db.Table('venue_genre_table',
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
    db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True)
)

# A table to hold venues
class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.relationship('Genre', secondary=venue_genre_table, backref=db.backref('venues'))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('Show', backref='venue', lazy=True)

    def __repr__(self):
        return f'<Venue {self.id} {self.name}>'

# A table to hold artists
class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.relationship('Genre', secondary=artist_genre_table, backref=db.backref('artists'))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('Show', backref='artist', lazy=True)

    def __repr__(self):
        return f'<Artist {self.id} {self.name}>'

# A table to hold shows
class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)

    def __repr__(self):
        return f'<Show {self.id} {self.start_time} artist_id={artist_id} venue_id={venue_id}>'


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    venues = Venue.query.all()

    out_data = []

    city_state = set()
    for venue in venues:
        city_state.add((venue.city, venue.state))

    city_state = list(city_state)
    city_state.sort(key=lambda x: (x[1], x[0]))

    now = datetime.now()

    for location in city_state:
        city_state_venues_list = []
        for venue in venues:
            if (venue.city == location[0]) and (venue.state == location[1]):

                venue_shows = Show.query.filter_by(venue_id=venue.id).all()
                upcoming_count = 0
                for show in venue_shows:
                    if show.start_time > now:
                        upcoming_count += 1

                city_state_venues_list.append({
                    "id": venue.id,
                    "name": venue.name,
                    "num_upcoming_shows": upcoming_count
                })

        out_data.append({
            "city": location[0],
            "state": location[1],
            "venues": city_state_venues_list
        })

    return render_template('pages/venues.html', areas=out_data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '').strip()

    # Use case insensitive and position independent search
    venues = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).all()
    venue_list = []

    for venue in venues:
        venue_list.append({
            "id": venue.id,
            "name": venue.name
        })
    response = {
        "count": len(venues),
        "data": venue_list
    }

    return render_template('pages/search_venues.html', results=response, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # Display the venue data for the venue with the given venue_id

    venue = Venue.query.get(venue_id)
    if venue is None:
        return redirect(url_for('index'))
    else:
        # Generate lists and counts of upcoming and past shows
        past_shows = []
        upcoming_shows = []
        now = datetime.now()

        for show in venue.shows:
            if show.start_time > now:
                upcoming_shows.append({
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": format_datetime(str(show.start_time))
                })
            if show.start_time <= now:
                past_shows.append({
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": format_datetime(str(show.start_time))
                })

        upcoming_shows_count = len(upcoming_shows)
        past_shows_count = len(past_shows)

        # Plug in all other data
        genres = [genre.name for genre in venue.genres]

        data = {
            "id": venue_id,
            "name": venue.name,
            "genres": genres,
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": (venue.phone[:3] + '-' + venue.phone[3:6] + '-' + venue.phone[6:]),
            "website": venue.website,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
            "past_shows": past_shows,
            "past_shows_count": past_shows_count,
            "upcoming_shows": upcoming_shows,
            "upcoming_shows_count": upcoming_shows_count
        }

    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data
    address = form.address.data.strip()
    phone = form.phone.data
    # Only keep phone number digits
    phone = re.sub('\D', '', phone)
    genres = form.genres.data
    image_link = form.image_link.data.strip()
    website = form.website.data.strip()
    facebook_link = form.facebook_link.data.strip()
    seeking_talent = True if form.seeking_talent.data == 'Yes' else False
    seeking_description = form.seeking_description.data.strip()

    # If errors, display errors and return back to original form
    if not form.validate():
        flash(form.errors)
        return redirect(url_for('create_venue_submission'))

    else:
        venue_creation_error = False

        # Insert form data into Venue DB
        try:
            # Prep genre field for ingestion into DB
            genres_to_db_list = []
            for genre in genres:
                genre_for_venue = Genre.query.filter_by(name=genre).one_or_none()
                if genre_for_venue:
                    genres_to_db_list.append(genre_for_venue)

                else:
                    # Create genre because none is available
                    new_genre = Genre(name=genre)
                    genres_to_db_list.append(new_genre)
                              
            new_venue = Venue(name=name, city=city, state=state, address=address, phone=phone, genres=genres_to_db_list, \
                image_link=image_link, website=website, facebook_link=facebook_link, \
                seeking_talent=seeking_talent, seeking_description=seeking_description, )
            
            db.session.add(new_venue)
            db.session.commit()
        except Exception as e:
            venue_creation_error = True
            print(f'Exception "{e}" in create_venue_submission()')
            db.session.rollback()
        finally:
            db.session.close()

        if not venue_creation_error:
            # on successful db insert, flash success
            flash('Venue ' + request.form['name'] + ' was successfully listed!')
            return redirect(url_for('index'))
        else:
            flash('An error occurred. Venue ' + name + ' could not be listed.')
            abort(500)


@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue:
        return redirect(url_for('index'))
    else:
        error_on_delete = False
        venue_name = venue.name
        try:
            db.session.delete(venue)
            db.session.commit()
        except:
            error_on_delete = True
            db.session.rollback()
        finally:
            db.session.close()
        if error_on_delete == True:
            flash(f'An error occurred deleting venue {venue_name}.')
            abort(500)
        else:
            flash(f'{venue_name} was successfully removed!')
            return jsonify({
                'deleted': True,
                'url': url_for('venues')
            })


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    artists = Artist.query.order_by(Artist.name).all()

    out_data = []
    for artist in artists:
        out_data.append({
            "id": artist.id,
            "name": artist.name
        })

    return render_template('pages/artists.html', artists=out_data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '').strip()

    # Use case insensitive and position independent search
    artists = Artist.query.filter(Artist.name.ilike('%' + search_term + '%')).all()
    artist_list = []

    for artist in artists:
        artist_list.append({
            "id": artist.id,
            "name": artist.name
        })
    response = {
        "count": len(artists),
        "data": artist_list
    }

    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # Display the venue data for the venue with the given venue_id

    artist = Artist.query.get(artist_id)
    if artist is None:
        return redirect(url_for('index'))
    else:
        # Generate lists and counts of upcoming and past shows
        past_shows = []
        upcoming_shows = []
        now = datetime.now()

        for show in artist.shows:
            if show.start_time > now:
                upcoming_shows.append({
                    "venue_id": show.venue_id,
                    "venue_name": show.venue.name,
                    "venue_image_link": show.venue.image_link,
                    "start_time": format_datetime(str(show.start_time))
                })
            if show.start_time <= now:
                past_shows.append({
                    "venue_id": show.venue_id,
                    "venue_name": show.venue.name,
                    "venue_image_link": show.venue.image_link,
                    "start_time": format_datetime(str(show.start_time))
                })

        upcoming_shows_count = len(upcoming_shows)
        past_shows_count = len(past_shows)

        # Plug in all other data
        genres = [genre.name for genre in artist.genres]

        data = {
            "id": artist_id,
            "name": artist.name,
            "genres": genres,
            "city": artist.city,
            "state": artist.state,
            "phone": (artist.phone[:3] + '-' + artist.phone[3:6] + '-' + artist.phone[6:]),
            "image_link": artist.image_link,
            "website": artist.website,
            "facebook_link": artist.facebook_link,
            "seeking_venue": artist.seeking_venue,
            "seeking_description": artist.seeking_description,
            "past_shows": past_shows,
            "past_shows_count": past_shows_count,
            "upcoming_shows": upcoming_shows,
            "upcoming_shows_count": upcoming_shows_count
        }

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    # Pull artist data from DB
    artist = Artist.query.get(artist_id)
    if artist is None:
        return redirect(url_for('index'))
    else:
        form = ArtistForm(obj=artist)

    genres = [genre.name for genre in artist.genres]

    artist = {
        "id": artist_id,
        "name": artist.name,
        "genres": genres,
        "city": artist.city,
        "state": artist.state,
        "phone": (artist.phone[:3] + '-' + artist.phone[3:6] + '-' + artist.phone[6:]),
        "image_link": artist.image_link,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description
    }

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data
    phone = form.phone.data
    # Only keep phone number digits
    phone = re.sub('\D', '', phone)
    genres = form.genres.data
    image_link = form.image_link.data.strip()
    website = form.website.data.strip()
    facebook_link = form.facebook_link.data.strip()
    seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    seeking_description = form.seeking_description.data.strip()
    
    if not form.validate():
        flash(form.errors)
        return redirect(url_for('edit_artist_submission', artist_id=artist_id))

    else:
        error_in_update = False

        try:
            # Update artist fields in DB
            artist = Artist.query.get(artist_id)

            artist.name = name
            artist.city = city
            artist.state = state
            artist.phone = phone
            artist.image_link = image_link
            artist.website = website
            artist.facebook_link = facebook_link
            artist.seeking_venue = seeking_venue
            artist.seeking_description = seeking_description

            artist.genres = []

            # Prep genre field for ingestion into DB
            for genre in genres:
                genre_for_artist = Genre.query.filter_by(name=genre).one_or_none()
                if genre_for_artist is not None:
                    artist.genres.append(genre_for_artist)

                else:
                    new_genre = Genre(name=genre)
                    db.session.add(new_genre)
                    artist.genres.append(new_genre)

            db.session.commit()
        except Exception as e:
            error_in_update = True
            print(f'Exception "{e}" in edit_artist_submission()')
            db.session.rollback()
        finally:
            db.session.close()

        if not error_in_update:
            # on successful db update, flash success
            flash('Artist ' + request.form['name'] + ' was successfully updated!')
            return redirect(url_for('show_artist', artist_id=artist_id))
        else:
            flash('An error occurred. Artist ' + name + ' could not be updated.')
            print("Error in edit_artist_submission()")
            abort(500)


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if venue is None:
        return redirect(url_for('index'))
    else:
        form = VenueForm(obj=venue)

    genres = [genre.name for genre in venue.genres]
    
    venue = {
        "id": venue_id,
        "name": venue.name,
        "genres": genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": (venue.phone[:3] + '-' + venue.phone[3:6] + '-' + venue.phone[6:]),
        "image_link": venue.image_link,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description
    }

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = VenueForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data
    address = form.address.data.strip()
    phone = form.phone.data
    # Only keep phone number digits
    phone = re.sub('\D', '', phone)
    genres = form.genres.data
    seeking_talent = True if form.seeking_talent.data == 'Yes' else False
    seeking_description = form.seeking_description.data.strip()
    image_link = form.image_link.data.strip()
    website = form.website.data.strip()
    facebook_link = form.facebook_link.data.strip()
    
    if not form.validate():
        flash(form.errors)
        return redirect(url_for('edit_venue_submission', venue_id=venue_id))

    else:
        error_in_update = False

        # Update artist fields in DB
        try:
            
            venue = Venue.query.get(venue_id)

            venue.name = name
            venue.city = city
            venue.state = state
            venue.address = address
            venue.phone = phone
            venue.image_link = image_link
            venue.website = website
            venue.facebook_link = facebook_link
            venue.seeking_talent = seeking_talent
            venue.seeking_description = seeking_description

            venue.genres = []

            for genre in genres:
                genre_for_venue = Genre.query.filter_by(name=genre).one_or_none()
                if genre_for_venue is not None:
                    venue.genres.append(genre_for_venue)

                else:
                    new_genre = Genre(name=genre)
                    db.session.add(new_genre)
                    venue.genres.append(new_genre)

            db.session.commit()
        except Exception as e:
            error_in_update = True
            print(f'Exception "{e}" in edit_venue_submission()')
            db.session.rollback()
        finally:
            db.session.close()

        if not error_in_update:
            # on successful db update, flash success
            flash('Venue ' + request.form['name'] + ' was successfully updated!')
            return redirect(url_for('show_venue', venue_id=venue_id))
        else:
            flash('An error occurred. Venue ' + name + ' could not be updated.')
            print("Error in edit_venue_submission()")
            abort(500)

#  Create Artist
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    form = ArtistForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data
    phone = form.phone.data
    # Only keep phone number digits
    phone = re.sub('\D', '', phone)
    genres = form.genres.data
    seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    seeking_description = form.seeking_description.data.strip()
    image_link = form.image_link.data.strip()
    website = form.website.data.strip()
    facebook_link = form.facebook_link.data.strip()
    
    # Redirect back to form if errors in form validation
    if not form.validate():
        flash(form.errors)
        return redirect(url_for('create_artist_submission'))

    else:
        artist_creation_error = False

        # Insert form data into Artist DB
        try:
            genres_to_db_list = []
            for genre in genres:
                genre_for_artist = Genre.query.filter_by(name=genre).one_or_none()
                if genre_for_artist:
                    genres_to_db_list.append(genre_for_artist)

                else:
                    # Create genre because none is available
                    new_genre = Genre(name=genre)
                    genres_to_db_list.append(new_genre)
            
            # creates the new artist with all fields but not genre yet
            new_artist = Artist(name=name, city=city, state=state, phone=phone, genres=genres_to_db_list, \
                seeking_venue=seeking_venue, seeking_description=seeking_description, image_link=image_link, \
                website=website, facebook_link=facebook_link)

            db.session.add(new_artist)
            db.session.commit()

        except Exception as e:
            artist_creation_error = True
            print(f'Exception "{e}" in create_artist_submission()')
            db.session.rollback()
        finally:
            db.session.close()

        if not artist_creation_error:
            # on successful db insert, flash success
            flash('Artist ' + request.form['name'] + ' was successfully listed!')
            return redirect(url_for('index'))
        else:
            flash('An error occurred. Artist ' + name + ' could not be listed.')
            print("Error in create_artist_submission()")
            abort(500)

@app.route('/artists/<artist_id>/delete', methods=['GET'])
def delete_artist(artist_id):
    artist = Artist.query.get(artist_id)
    if not artist:
        return redirect(url_for('index'))
    else:
        error_on_delete = False
        artist_name = artist.name
        try:
            db.session.delete(artist)
            db.session.commit()
        except:
            error_on_delete = True
            db.session.rollback()
        finally:
            db.session.close()
        if error_on_delete:
            flash(f'An error occurred deleting artist {artist_name}.')
            abort(500)
        else:
            flash(f'Successfully removed artist {artist_name}')
            return jsonify({
                'deleted': True,
                'url': url_for('artists')
            })


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    data = []
    shows = Show.query.all()
    
    for show in shows:
        data.append({
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create', methods=['GET'])
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm()

    artist_id = form.artist_id.data.strip()
    venue_id = form.venue_id.data.strip()
    start_time = form.start_time.data

    new_show_error = False
    
    try:
        new_show = Show(start_time=start_time, artist_id=artist_id, venue_id=venue_id)
        db.session.add(new_show)
        db.session.commit()
    except:
        new_show_error = True
        print(f'Exception "{e}" in create_show_submission()')
        db.session.rollback()
    finally:
        db.session.close()

    if new_show_error:
        flash(f'An error occurred.  Show could not be listed.')
        print("Error in create_show_submission()")
    else:
        flash('Show was successfully listed!')
    
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
