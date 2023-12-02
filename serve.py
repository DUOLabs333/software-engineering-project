
from routes import users, posts, jobs, search

from utils.common import app

app.run(threaded=True,debug=True)
