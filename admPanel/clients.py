from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from admPanel.auth import db_connection_pool
from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params

clients_blueprint = Blueprint('clients_blueprint', __name__)

@clients_blueprint.route('/adm/v1/users', methods=['GET'])
@jwt_required()
def get_users():
    try:
        # SQL Query para buscar todos os campos dos usuários exceto a senha
        sql_query = """
        SELECT 
            name, email, userID, cpf, paypall_email, phone, is_subscriber, created_at
        FROM users
        """

        # Chama a função execute_query para buscar todos os usuários
        result = execute_query_without_params(sql_query, fetch_all=True)

        # Não há necessidade de converter strings em listas aqui

        return jsonify(result)
    except Exception as e:
        # Em caso de erro, retorna uma mensagem de erro
        return jsonify({"error": str(e)}), 500  # Código de status HTTP para Internal Server Error

@clients_blueprint.route('/adm/v2/users', methods=['GET'])
def get_users_with_transactions_and_withdraws():
    try:
        # SQL Query para buscar todos os usuários com suas respectivas transações e requisições de saque
        sql_query = """
        SELECT 
            u.name, u.email, u.userID, u.cpf, u.paypall_email, u.phone, u.is_subscriber, u.created_at,
            t.transaction_id, t.type, t.amount as transaction_amount, t.status as transaction_status, t.transaction_date, t.secondary_user_id, t.invoice_url, t.recipe_url,
            w.id as withdraw_id, w.amount as withdraw_amount, w.status as withdraw_status, w.created_at as withdraw_created_at
        FROM users u
        LEFT JOIN transactions t ON u.userID = t.user_id
        LEFT JOIN withdraw_requests w ON u.userID = w.userID
        """

        # Chama a função execute_query para buscar todos os usuários com suas transações e requisições de saque
        result = execute_query_without_params(sql_query, fetch_all=True)

        # Dicionário para armazenar os usuários e suas transações e requisições de saque
        users_dict = {}

        for row in result:
            user_id = row['userID']
            
            # Se o usuário ainda não foi adicionado ao dicionário, adiciona-o
            if user_id not in users_dict:
                users_dict[user_id] = {
                    'name': row['name'],
                    'email': row['email'],
                    'userID': row['userID'],
                    'cpf': row['cpf'],
                    'paypall_email': row['paypall_email'],
                    'phone': row['phone'],
                    'is_subscriber': row['is_subscriber'],
                    'created_at': row['created_at'],
                    'transactions': [],
                    'withdraw_requests': []
                }
            
            # Se houver uma transação associada (t.transaction_id não for None), adiciona à lista de transações
            if row['transaction_id'] is not None:
                transaction = {
                    'transaction_id': row['transaction_id'],
                    'type': row['type'],
                    'amount': row['transaction_amount'],
                    'status': row['transaction_status'],
                    'transaction_date': row['transaction_date'],
                    'secondary_user_id': row['secondary_user_id'],
                    'invoice_url': row['invoice_url'],
                    'recipe_url': row['recipe_url']
                }
                users_dict[user_id]['transactions'].append(transaction)

            # Se houver uma requisição de saque associada (w.withdraw_id não for None) e o status não for APPROVED, adiciona à lista de requisições de saque
            if row['withdraw_id'] is not None and row['withdraw_status'] != 'APPROVED':
                withdraw_request = {
                    'withdraw_id': row['withdraw_id'],
                    'amount': row['withdraw_amount'],
                    'status': row['withdraw_status'],
                    'created_at': row['withdraw_created_at']
                }
                users_dict[user_id]['withdraw_requests'].append(withdraw_request)

        # Convertendo o dicionário de usuários para uma lista
        users_list = list(users_dict.values())

        return jsonify(users_list)
    except Exception as e:
        # Em caso de erro, retorna uma mensagem de erro
        return jsonify({"error": str(e)}), 500  # Código de status HTTP para Internal Server Error

