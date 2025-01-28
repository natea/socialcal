# SocialCal

An experiment to build a generic events scraper and publish them to a curated and personalized calendar.

# How to run:

1. Create a virtual environment `python -m venv venv`
2. Activate the virtual environment `source venv/bin/activate`
3. Install dependencies `pip install -r requirements.txt`
4. Create a `.env file with the following variables (see .env-dummy for reference):
    - `OPENAI_API_KEY`
    - `SPOTIFY_CLIENT_ID`
    - `SPOTIFY_CLIENT_SECRET`
5. Run `python manage.py migrate`
6. Run `python manage.py createsuperuser`
7. Run `python manage.py runserver`
8. Go to `http://localhost:8000/` and login with the superuser credentials


