import logging
from waitress import serve

from app import create_app


app = create_app()

if __name__ == "__main__":
    logging.info("Flask app started")
    serve(app, host="0.0.0.0", port=8000) #waitress
    #app.run(host="0.0.0.0", port=8000) 'flask'
