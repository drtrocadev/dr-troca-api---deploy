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
from admPanel.auth import db_connection_pool
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import datetime

ALLOWED_HOSTS = ["gpt-treinador.herokuapp.com/", "127.0.0.1"]

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JSON_SORT_KEYS'] = False
app.config['JWT_SECRET_KEY'] = 'Lelo_318318'
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

import datetime
from mysql.connector import pooling

# exemplo de pool; ajuste conforme sua configuração
db_connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host="seu_host",
    user="seu_usuario",
    password="sua_senha",
    database="seu_banco"
)

def finish_pending_transactions():
    print(f"Tarefa diária executada em: {datetime.datetime.now()}")
    connection = None
    cursor = None

    try:
        # Obter conexão do pool
        connection = db_connection_pool.get_connection()
        cursor = connection.cursor()

        # 1. Selecionar registros criados há 7 dias e ainda não finalizados (status != 1)
        select_query = """
        SELECT user_id, type, amount, status, transaction_date,
               secondary_user_id, invoice_url, recipe_url, in_app_transaction_id
        FROM pending_transactions
        WHERE transaction_date <= NOW() - INTERVAL 7 DAY
          AND status != 1;
        """
        cursor.execute(select_query)
        pending_transactions = cursor.fetchall()

        if pending_transactions:
            # 2. Inserir registros na tabela transactions
            insert_query = """
            INSERT INTO transactions (
                user_id, type, amount, status, transaction_date,
                secondary_user_id, invoice_url, recipe_url, in_app_transaction_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.executemany(insert_query, pending_transactions)

            # 3. Atualizar para marcado como finalizado (status = 1)
            update_query = """
            UPDATE pending_transactions
            SET status = 1
            WHERE transaction_date <= NOW() - INTERVAL 7 DAY
              AND status != 1;
            """
            cursor.execute(update_query)

            connection.commit()
            print(f"{cursor.rowcount} transações migradas e marcadas como finalizadas.")
        else:
            print("Nenhuma transação pendente para migrar.")

    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Ocorreu um erro durante a migração: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

scheduler = BackgroundScheduler()
#scheduler.add_job(func=finish_pending_transactions, trigger="interval", seconds=10)
scheduler.add_job(func=finish_pending_transactions, trigger="cron", hour=2, minute=0)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=5000)
