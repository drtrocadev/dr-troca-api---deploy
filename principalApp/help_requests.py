from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params

help_requests_blueprint = Blueprint('help_requests_blueprint', __name__)

@help_requests_blueprint.route('/v1/add_help_request', methods=['POST'])
@jwt_required()
def add_help_request():
    try:
        # Obter os dados do JSON enviado na requisição
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400

        description = data.get('description')
        jwt_claims = get_jwt()
        
        user_id = jwt_claims.get("user_id")

        # Verificar se todos os campos necessários estão presentes
        if not description or not user_id:
            return jsonify({'error': 'Missing description or user_id'}), 400

        # Criar a consulta SQL para inserir o novo pedido de ajuda
        query = """
        INSERT INTO help_requests (description, user_id)
        VALUES (%s, %s)
        """
        params = (description, user_id)
        
        # Executar a consulta e retornar uma resposta
        try:
            execute_query_with_params(query, params)
            return jsonify({'success': 'Help request added successfully'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        return jsonify({'error': 'Unable to process the request'}), 422
    
@help_requests_blueprint.route('/adm/v1/help_requests', methods=['GET'])
@jwt_required()
def get_help_requests():
    try:
        # Query que realiza o JOIN entre as tabelas 'help_requests' e 'users'
        query = """
        SELECT hr.*, u.name, u.email, u.userID, u.cpf, u.paypall_email, u.phone, u.is_subscriber, u.created_at
        FROM help_requests hr
        JOIN users u ON hr.user_id = u.userID
        """

        help_requests = execute_query_without_params(query, fetch_all=True)

        # Retornar os dados em formato JSON
        return jsonify(help_requests), 200

    except Exception as e:
        # Em caso de erro, retorna uma mensagem de erro
        return jsonify({"error": str(e)}), 500  # Código de status HTTP para Internal Server Error

@help_requests_blueprint.route('/adm/v1/help_requests/<int:request_id>', methods=['DELETE'])
@jwt_required()
def delete_help_request(request_id):
    try:
        # Query para apagar um help request específico pelo ID
        query = "DELETE FROM help_requests WHERE id = %s"
        
        # Executar a query com o parâmetro do ID do help request
        execute_query_with_params(query, (request_id,))
        
        # Verificar se o help request foi realmente apagado, opcionalmente

        # Retornar uma mensagem de sucesso
        return jsonify({"success": "Help request deleted successfully"}), 200

    except Exception as e:
        # Em caso de erro, retorna uma mensagem de erro
        return jsonify({"error": str(e)}), 500  # Código de status HTTP para Internal Server Error