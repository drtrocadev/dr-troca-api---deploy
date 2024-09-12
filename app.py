from flask import Flask
from flask_cors import CORS
import os
from admPanel.auth import auth_blueprint
from admPanel.foods import adm_foods_blueprint
from principalApp.products import products_blueprint
from principalApp.help_requests import help_requests_blueprint
from principalApp.food_suggestions import food_suggestions_blueprint
from principalApp.monetization import monetization_blueprint
from admPanel.monetization import adm_monetization_blueprint
from admPanel.clients import clients_blueprint
from principalApp.auth_clients import auth_clients_blueprint
from principalApp.favorites import favorites_blueprint
from admPanel.adm_users import adm_users_blueprint
from flask_jwt_extended import JWTManager

ALLOWED_HOSTS = ["gpt-treinador.herokuapp.com/", "127.0.0.1"]

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JSON_SORT_KEYS'] = False
app.config['JWT_SECRET_KEY'] = 'Lelo_318318'  # Change this!
jwt = JWTManager(app)

app.register_blueprint(auth_blueprint)
app.register_blueprint(products_blueprint)
app.register_blueprint(adm_foods_blueprint)
app.register_blueprint(clients_blueprint)
app.register_blueprint(help_requests_blueprint)
app.register_blueprint(food_suggestions_blueprint)
app.register_blueprint(auth_clients_blueprint)
app.register_blueprint(monetization_blueprint)
app.register_blueprint(adm_monetization_blueprint)
app.register_blueprint(favorites_blueprint)
app.register_blueprint(adm_users_blueprint)

port = int(os.environ.get("PORT", 5000))

if __name__ == '__name__':
    app.run(host="0.0.0.0", port=port)