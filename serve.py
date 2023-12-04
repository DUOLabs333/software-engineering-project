
from routes import users, posts, jobs, search, balance

from utils.common import app

app.run(threaded=True,debug=True)
