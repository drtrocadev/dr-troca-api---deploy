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

def finish_pending_transactions():
    print(f"Tarefa diária executada em: {datetime.datetime.now()}")
    try:
        # Obter conexão do pool
        connection = db_connection_pool.get_connection()

        # Iniciar uma transação
        cursor = connection.cursor()

        # 1. Selecionar os registros da tabela pending_transactions que foram criados há 7 dias,
        # e cujo status não seja 'FINISHED', incluindo o campo in_app_transaction_id
        select_query = """
        SELECT user_id, type, amount, status, transaction_date, secondary_user_id, invoice_url, recipe_url, in_app_transaction_id
        FROM pending_transactions
        WHERE transaction_date <= NOW() - INTERVAL 7 DAY
        AND status != 'FINISHED';
        """
        cursor.execute(select_query)
        pending_transactions = cursor.fetchall()

        # 2. Inserir os registros na tabela transactions, incluindo o campo in_app_transaction_id
        if pending_transactions:
            insert_query = """
            INSERT INTO transactions (user_id, type, amount, status, transaction_date, secondary_user_id, invoice_url, recipe_url, in_app_transaction_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.executemany(insert_query, pending_transactions)

            # 3. Atualizar os registros na tabela pending_transactions, alterando o status para 'FINISHED'
            update_query = """
            UPDATE pending_transactions
            SET status = 'FINISHED'
            WHERE transaction_date <= NOW() - INTERVAL 7 DAY
            AND status != 'FINISHED';
            """
            cursor.execute(update_query)

            # Confirmar a transação
            connection.commit()
            print(f"{cursor.rowcount} transações migradas e atualizadas com sucesso.")

        else:
            print("Nenhuma transação pendente para migrar.")
    
    except Exception as e:
        # Caso ocorra um erro, reverter a transação
        if connection:
            connection.rollback()
        print(f"Ocorreu um erro durante a migração: {e}")
    
    finally:
        # Garantir que a conexão seja fechada no final
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
    app.run(host="0.0.0.0", port=port)
