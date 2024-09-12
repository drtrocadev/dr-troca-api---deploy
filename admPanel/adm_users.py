from flask import Blueprint, request, jsonify
import mysql.connector.pooling
from admPanel.functions import execute_query_with_params, execute_query_without_params

adm_users_blueprint = Blueprint('adm_users', __name__)

db_config = {
    'host': 'srv1311.hstgr.io',
    'user': 'u994546528_dr_troca_ap',
    'password': '1jdus83@L',
    'database': 'u994546528_dr_troca_ap'
}

db_connection_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="db_pool", pool_size=10, **db_config)

@adm_users_blueprint.route('/adm/v1/adm_users', methods=['GET'])
def list_adm_users():
    sql_query = "SELECT userID, name, email FROM adm_users"
    users = execute_query_without_params(sql_query, fetch_all=True, should_commit=False)
    return jsonify(users)

@adm_users_blueprint.route('/adm/v1/adm_users', methods=['POST'])
def add_adm_user():
    data = request.json
    name = data.get('name', '')
    email = data.get('email', '')
    password = data.get('password', '')

    # Verifica se o email já existe
    check_email_query = "SELECT COUNT(*) as count FROM adm_users WHERE email = %s"
    email_exists = execute_query_with_params(check_email_query, (email,), fetch_all=False, should_commit=False)
    
    if email_exists['count'] > 0:
        return jsonify({'error': 'Email already exists'}), 400

    sql_query = """
    INSERT INTO adm_users (name, email, password, cpf, pix_key, phone, is_subscriber, created_at)
    VALUES (%s, %s, %s, '', '', '', 0, NOW())
    """
    params = (name, email, password)
    
    execute_query_with_params(sql_query, params, should_commit=True)

    # Fetch the ID of the last inserted row
    user_id_query = "SELECT LAST_INSERT_ID() as userID"
    user_id_result = execute_query_without_params(user_id_query, fetch_all=False, should_commit=False)
    user_id = user_id_result['userID']

    return jsonify({'userID': user_id, 'name': name, 'email': email}), 201


@adm_users_blueprint.route('/adm/v1/adm_users/<int:user_id>', methods=['DELETE'])
def remove_adm_user(user_id):
    sql_query = "DELETE FROM adm_users WHERE userID = %s"
    params = (user_id,)
    
    execute_query_with_params(sql_query, params, should_commit=True)
    
    return jsonify({'message': f'User {user_id} deleted successfully.'}), 200
