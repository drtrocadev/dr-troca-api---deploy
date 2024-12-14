from flask import Blueprint, request, jsonify
import mysql.connector.pooling
from flask_jwt_extended import create_access_token
import bcrypt
import re
from datetime import timedelta

auth_blueprint = Blueprint('auth', __name__)

db_config = {
    'host': 'srv1311.hstgr.io',
    'user': 'u994546528_dr_troca_ap',
    'password': '1jdus83@L',
    'database': 'u994546528_dr_troca_ap',
}

db_connection_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="db_pool", pool_size=7, **db_config)

@auth_blueprint.route('/v1/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        query = "SELECT * FROM adm_users WHERE email = %s"
        user = execute_query(query, (email,), fetch_all=False)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            # Verifica se o request é de um dispositivo móvel
            user_agent = request.headers.get('User-Agent').lower()
            print(user_agent)
            is_mobile = bool(re.search(r"android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini", user_agent))

            if is_mobile:
                expires_in = timedelta(days=365)  # Define a expiração para 365 dias para dispositivos móveis
            else:
                expires_in = timedelta(days=15)  # Define a expiração para 15 dias para outros dispositivos

            access_token = create_access_token(identity=email, expires_delta=expires_in)
            return jsonify({"statusCode": "200", "message": "Login successful", "access_token": access_token}), 200
        else:
            return jsonify({"statusCode": "401", "message": "Invalid email or password"}), 401

    except ValueError as ve:
        return jsonify({"error": "IP Blocked. Suspicious activity detected."}), 403

    except Exception as e:
        # Tratamento de outras exceções
        return jsonify({"error": str(e)}), 500
    
@auth_blueprint.route('/v1/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        # Check if user already exists
        check_query = "SELECT * FROM adm_users WHERE email = %s"
        existing_user = execute_query(check_query, (email,), fetch_all=False)
        if existing_user:
            return jsonify({"statusCode": "409", "message": "Email already registered"}), 409

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create new user record in the database
        insert_query = "INSERT INTO adm_users (email, password) VALUES (%s, %s)"
        execute_query(insert_query, (email, hashed_password))

        # Generate JWT token for the new user
        access_token = create_access_token(identity=email)

        return jsonify({"statusCode": "200", "message": "Registration successful", "access_token": access_token}), 200
    
    except ValueError as ve:
        return jsonify({"error": "IP Blocked. Suspicious activity detected."}), 403
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def is_potentially_malicious(param):
    # Lista de palavras-chave a serem verificadas
    malicious_keywords = ["DELETE", "DROP", "INSERT", "UPDATE", "ALTER", "EXEC", "CREATE", "UNION"]
    
    # Verifica se alguma palavra-chave está presente no parâmetro
    for keyword in malicious_keywords:
        if keyword.lower() in str(param).lower():
            return True
    return False

def execute_query(sql_query, params=None, fetch_all=False):
    connection = None
    cursor = None
    try:
        # Verifica se os parâmetros contêm termos potencialmente maliciosos
        if params and any(is_potentially_malicious(param) for param in params):
            raise ValueError("Potentially malicious SQL keywords found in parameters.")
        
        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        if params:
            cursor.execute(sql_query, params)
        else:
            cursor.execute(sql_query)

        if fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()

        # Commit a transação para aplicar a atualização no banco de dados
        connection.commit()

        return result

    except Exception as e:
        # Em caso de erro, faça um rollback da transação para evitar atualizações incompletas
        if connection:
            connection.rollback()
        raise e

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()