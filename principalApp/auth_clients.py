from flask import Blueprint, request, jsonify
import mysql.connector.pooling
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt, JWTManager
import bcrypt
import re
from datetime import timedelta
import random
import string
import time
from admPanel.functions import execute_query_with_params
from principalApp.functions import send_email
from admPanel.auth import db_connection_pool

auth_clients_blueprint = Blueprint('auth_clients', __name__)

@auth_clients_blueprint.route('/v1/login_client', methods=['POST'])
def login_clients():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        query = "SELECT * FROM users WHERE email = %s"
        user = execute_query(query, (email,), fetch_all=False)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            # Omita a senha ao preparar a resposta
            user_info = {key: user[key] for key in user if key != 'password'}

            # Verifica se o request é de um dispositivo móvel
            user_agent = request.headers.get('User-Agent').lower()
            is_mobile = bool(re.search(r"android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini", user_agent))

            if is_mobile:
                expires_in = timedelta(days=365)  # Define a expiração para 365 dias para dispositivos móveis
            else:
                expires_in = timedelta(days=15)  # Define a expiração para 15 dias para outros dispositivos
            
            additional_claims = {
                "password_change_timestamp": str(user["password_change_timestamp"]),
                "user_id": str(user_info["userID"])
            }
            
            access_token = create_access_token(identity=email, expires_delta=expires_in, additional_claims=additional_claims)
            return jsonify({"statusCode": "200", "message": "Login successful", "access_token": access_token, "user_info": user_info}), 200
        else:
            return jsonify({"statusCode": "401", "message": "Invalid email or password"}), 401

    except Exception as e:
        # Tratamento de outras exceções
        return jsonify({"error": str(e)}), 500

    
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def is_code_unique(code, cursor):
    sql_query = "SELECT COUNT(*) as count FROM users WHERE referral_code = %s"
    cursor.execute(sql_query, (code,))
    result = cursor.fetchone()
    return result['count'] == 0

def create_unique_code(cursor):
    while True:
        new_code = generate_code()
        if is_code_unique(new_code, cursor):
            return new_code  
    
@auth_clients_blueprint.route('/v1/register_client', methods=['POST'])
def register_clients():
    connection = None
    cursor = None
    try:

        timestamp_atual = int(time.time())

        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        data = request.get_json()
        email = data['email']
        password = data['password']
        name = data['name']

        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            return jsonify({"statusCode": "400", "message": "Invalid email format"}), 400

        check_query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(check_query, (email,))
        if cursor.fetchone():
            return jsonify({"statusCode": "409", "message": "Email already registered"}), 409

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        unique_code = create_unique_code(cursor)

        insert_query = "INSERT INTO users (name, email, password, referral_code, password_change_timestamp, actual_money) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (name, email, hashed_password, unique_code, timestamp_atual, 0.0))

        user_id = cursor.lastrowid 
        additional_claims = {
            "password_change_timestamp": str(timestamp_atual),
            "user_id": str(user_id)
        }

        access_token = create_access_token(identity=email, additional_claims=additional_claims)

        connection.commit()

        # Fetch the actual_money after committing the transaction
        cursor.execute("SELECT actual_money FROM users WHERE userID = %s", (user_id,))
        actual_money = cursor.fetchone()["actual_money"]

        user_info = {
            "name": name,
            "email": email,
            "userID": user_id, 
            "cpf": "",
            "paypall_email": "",
            "phone": "",
            "is_subscriber": 0,
            "created_at": "",
            "referral_code": unique_code,
            "password_change_timestamp": str(timestamp_atual),
            "actual_money": actual_money
        }

        return jsonify({"statusCode": "200", "message": "Registration successful", "access_token": access_token, "user_info": user_info}), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@auth_clients_blueprint.route('/v1/token_validation', methods=['GET'])
@jwt_required()  # Certifique-se de que o token JWT seja fornecido
def validate_token():
    try:
        # Obter o token do cabeçalho da solicitação
        raw_token = request.headers.get("Authorization", "").replace("Bearer ", "")

        # Pega o email e o carimbo de data/hora da última alteração de senha do token JWT
        current_user_email = get_jwt_identity()
        jwt_claims = get_jwt()
        token_pass_changed_at = jwt_claims.get('password_change_timestamp')

        # Buscar o usuário e a data de última alteração de senha do banco de dados usando o email
        user_query = """
            SELECT name, email, userID, cpf, paypall_email, phone, actual_money, is_subscriber, created_at, referral_code, password_change_timestamp 
            FROM users WHERE email = %s
        """
        user_record = execute_query(user_query, (current_user_email,), fetch_all=False)

        if not user_record:
            return jsonify({"statusCode": "404", "message": "User not found"}), 404

        # Converta ambos os timestamps para strings antes da comparação
        token_timestamp_str = str(token_pass_changed_at)
        db_timestamp_str = str(user_record['password_change_timestamp'])

        # Verificar se os timestamps como strings são iguais
        if token_timestamp_str != db_timestamp_str:
            return jsonify({"statusCode": "401", "message": "Token is no longer valid"}), 401

        # Se o token ainda for válido, retorne o JSON com as informações do usuário
        user_info = {
            "name": user_record["name"],
            "email": user_record["email"],
            "userID": user_record["userID"],
            "cpf": user_record["cpf"] or "",
            "paypall_email": user_record["paypall_email"] or "",
            "phone": user_record["phone"] or "",
            "actual_money": user_record["actual_money"] or 0.0,
            "is_subscriber": user_record["is_subscriber"] or 0,
            "created_at": str(user_record["created_at"]) if user_record["created_at"] else "",
            "referral_code": user_record["referral_code"] or "",
            "password_change_timestamp": db_timestamp_str
        }

        return jsonify({
            "statusCode": "200",
            "message": "Token is valid",
            "access_token": raw_token,
            "user_info": user_info
        }), 200

    except Exception as e:
        return jsonify({"statusCode": "500", "error": str(e)}), 500

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

def is_potentially_malicious(param):
    # Lista de palavras-chave a serem verificadas
    malicious_keywords = ["DELETE", "DROP", "INSERT", "UPDATE", "ALTER", "EXEC", "CREATE", "UNION"]
    
    # Verifica se alguma palavra-chave está presente no parâmetro
    for keyword in malicious_keywords:
        if keyword.lower() in str(param).lower():
            return True
    return False


@auth_clients_blueprint.route('/v1/check_referral', methods=['POST'])
@jwt_required()
def check_referral():
    referral_code = request.json.get('referral_code', None)
    # Obter o ID do usuário a partir do token JWT
    jwt_claims = get_jwt()

    user_id = jwt_claims.get('user_id')
    
    if not referral_code:
        return jsonify({"error": "Referral code is required"}), 400

    # Verificar se o código de referência existe
    sql_query = "SELECT * FROM users WHERE referral_code = %s"
    params = (referral_code,)

    try:
        result = execute_query(sql_query, params, fetch_all=False)
        if result:
            # Agora verificar se o campo invited_by do usuário atual está vazio ou nulo
            check_invited_by_query = "SELECT invited_by FROM users WHERE id = %s"
            check_params = (user_id,)
            invited_by_result = execute_query(check_invited_by_query, check_params, fetch_all=False)

            if invited_by_result and (invited_by_result['invited_by'] is None or invited_by_result['invited_by'] == ""):
                # Se o campo invited_by for nulo ou vazio, então faça o update
                update_query = "UPDATE users SET invited_by = %s WHERE id = %s"
                update_params = (referral_code, user_id)
                execute_query(update_query, update_params, fetch_all=False)

                return jsonify({"success": "Referral code is valid and invited_by updated", "user_id": user_id}), 200
            else:
                return jsonify({"error": "invited_by is already set"}), 400
        else:
            return jsonify({"error": "Invalid referral code"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


# ROTAS DE EDITAR INFORMAÇÕES DOS USUÁRIOS

def verify_password_change_timestamp(current_user_email, jwt_claims):

    # Buscar o timestamp do banco de dados usando o e-mail
    query = "SELECT password_change_timestamp FROM users WHERE email = %s"
    user_record = execute_query(query, (current_user_email,))

    if not user_record:
        return False, "User not found"

    # Comparar o timestamp do token com o do banco de dados
    db_timestamp_str = str(user_record["password_change_timestamp"])
    token_timestamp_str = str(jwt_claims.get("password_change_timestamp"))

    if token_timestamp_str != db_timestamp_str:
        print("Token is no longer valid.")
        return False, "Token is no longer valid"

    print("Token is valid.")
    return True, None

@auth_clients_blueprint.route('/v2/update_user', methods=['POST'])
@jwt_required()
def update_user():
    try:
        current_user_email = get_jwt_identity()
        jwt_claims = get_jwt()
        
        valid, error_message = verify_password_change_timestamp(current_user_email, jwt_claims)
        if not valid:
            return jsonify({"statusCode": "401", "message": error_message}), 401

        try:
            data = request.get_json(force=True)
        except Exception as e:
            return jsonify({"error": "Invalid JSON in request"}), 400

        # Extrai os campos que podem ser atualizados
        name = data.get('name')
        phone = data.get('phone')
        paypall_email = data.get('paypall_email')
        cpf = data.get('cpf')
        
        # Constrói a cláusula SET da consulta SQL com base nos dados fornecidos
        set_clauses = []
        values = []

        if name:
            set_clauses.append("name = %s")
            values.append(name)
        if phone:
            set_clauses.append("phone = %s")
            values.append(phone)
        if paypall_email:
            set_clauses.append("paypall_email = %s")
            values.append(paypall_email)
        if cpf:
            set_clauses.append("cpf = %s")
            values.append(cpf)

        # Garante que pelo menos um campo seja atualizado
        if not set_clauses:
            return jsonify({"error": "No valid fields provided for update"}), 400

        # Adiciona o e-mail aos valores, pois ele será usado na cláusula WHERE
        set_clauses = ', '.join(set_clauses)
        values.append(current_user_email)  # Usar o email atual do usuário autenticado na cláusula WHERE

        # Monta a consulta SQL
        update_query = f"UPDATE users SET {set_clauses} WHERE email = %s"

        # Debug: Imprime a consulta e os valores
        print(f"Executing query: {update_query}")
        print(f"With values: {values}")

        # Executa a consulta
        try:
            execute_query(update_query, values)
        except Exception as e:
            print(f"Error executing query: {str(e)}")  # Debug: Imprime o erro da execução da consulta
            return jsonify({"error": "Error updating user information"}), 500

        return jsonify({"user": data}), 200

    except Exception as e:
        print(f"Internal server error: {str(e)}")  # Debug: Imprime o erro interno do servidor
        return jsonify({"error": "Internal server error"}), 500



@auth_clients_blueprint.route('/v1/delete_user', methods=['DELETE'])
@jwt_required()  # Certifique-se de que o token JWT seja fornecido
def delete_user():
    try:
        # Obter o e-mail do usuário autenticado e o timestamp do token JWT
        current_user_email = get_jwt_identity()
        jwt_claims = get_jwt()
        token_pass_changed_at = jwt_claims.get("password_change_timestamp")

        # Buscar o timestamp do banco de dados usando o e-mail
        query = "SELECT password_change_timestamp FROM users WHERE email = %s"
        user_record = execute_query(query, (current_user_email,), fetch_all=False)

        if not user_record:
            return jsonify({"statusCode": "404", "message": "User not found"}), 404

        # Comparar o timestamp do token com o do banco de dados
        db_timestamp_str = str(user_record["password_change_timestamp"])
        token_timestamp_str = str(token_pass_changed_at)

        if token_timestamp_str != db_timestamp_str:
            return jsonify({"statusCode": "401", "message": "Token is no longer valid"}), 401

        # Excluir o usuário do banco de dados
        delete_query = "DELETE FROM users WHERE email = %s"
        execute_query(delete_query, (current_user_email,))

        return jsonify({
            "statusCode": "200",
            "message": "User deleted successfully"
        }), 200

    except Exception as e:
        return jsonify({"statusCode": "500", "error": str(e)}), 500
    
@auth_clients_blueprint.route('/v1/request_password_reset', methods=['POST'])
def request_password_reset():
    try:
        email = request.json.get('email')  # Email tratado normalmente

        # Verificar se o email existe na tabela users
        sql_query = "SELECT userID FROM users WHERE email = %s"
        params = (email,)
        result = execute_query_with_params(sql_query, params, fetch_all=True)

        if not result:
            return jsonify({"error": "Nenhuma conta encontrada com o email informado."}), 404

        # Gerar código de verificação
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Salvar código no banco de dados associado ao email
        sql_query = "UPDATE users SET verification_code = %s WHERE email = %s"
        params = (code, email)
        execute_query_with_params(sql_query, params)

        # Enviar email
        send_email(subject="Use o código para recuperar sua senha", recipient_email=email, code=code)

        return jsonify({"message": "Código de recuperação enviado para seu email."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_clients_blueprint.route('/v1/verify_reset_code', methods=['POST'])
def verify_reset_code():
    try:
        email = request.json.get('email')  # Email tratado normalmente
        code = request.json.get('code')

        sql_query = "SELECT verification_code FROM users WHERE email = %s"
        params = (email,)
        result = execute_query_with_params(sql_query, params, fetch_all=True)

        # Comparação do código de verificação de forma insensível a maiúsculas
        if result and result[0]['verification_code'].lower() == code.lower():
            return jsonify({"message": "Código verificado com sucesso."})
        else:
            return jsonify({"message": "Código inválido."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_clients_blueprint.route('/v1/reset_password', methods=['POST'])
def reset_password():
    try:
        email = request.json.get('email')  # Email tratado normalmente
        code = request.json.get('code')
        new_password = request.json.get('new_password')

        sql_query = "SELECT verification_code FROM users WHERE email = %s"
        params = (email,)
        result = execute_query_with_params(sql_query, params, fetch_all=True)

        # Comparação do código de verificação de forma insensível a maiúsculas
        if result and result[0]['verification_code'].lower() == code.lower():
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            sql_query = "UPDATE users SET password = %s WHERE email = %s"
            params = (hashed_password, email)
            execute_query_with_params(sql_query, params)
            message = "Senha alterada com sucesso."
        else:
            message = "Código inválido."

        # Limpar o código de verificação
        sql_query = "UPDATE users SET verification_code = '' WHERE email = %s"
        execute_query_with_params(sql_query, (email,))

        return jsonify({"message": message})
    except Exception as e:
        # Tentar limpar o código mesmo que ocorra um erro
        try:
            sql_query = "UPDATE users SET verification_code = '' WHERE email = %s"
            execute_query_with_params(sql_query, (email,))
        except:
            pass
        return jsonify({"error": str(e)}), 500
