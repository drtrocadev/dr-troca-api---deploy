from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params

food_suggestions_blueprint = Blueprint('food_suggestions_blueprint', __name__)

@food_suggestions_blueprint.route('/v1/add_food_suggestion', methods=['POST'])
def add_food_suggestion():
    # Extraindo dados do corpo da requisição
    data = request.get_json()
    food_name = data.get('food_name')
    description = data.get('description')
    user_id = data.get('user_id')
    
    if not food_name or not user_id:
        return jsonify({"error": "food_name and user_id are required"}), 400

    # SQL para inserir a nova sugestão de comida na tabela food_suggestions
    sql = """
    INSERT INTO food_suggestions (food_name, description, user_id) 
    VALUES (%s, %s, %s);
    """
    execute_query_with_params(sql, (food_name, description, user_id))
    
    return jsonify({"message": "Food suggestion added successfully"}), 201

@food_suggestions_blueprint.route('/v2/add_food_suggestion', methods=['POST'])
@jwt_required()
def add_food_suggestion_v2():
    # Extraindo dados do corpo da requisição
    data = request.get_json()
    food_name = data.get('food_name')
    description = data.get('description')
    
    jwt_claims = get_jwt()
    user_id = jwt_claims.get('user_id')

    if not food_name:
        return jsonify({"error": "food_name is required"}), 400

    # SQL para inserir a nova sugestão de comida na tabela food_suggestions usando o email do usuário
    sql = """
    INSERT INTO food_suggestions (food_name, description, user_id) 
    VALUES (%s, %s, %s);
    """
    execute_query_with_params(sql, (food_name, description, user_id))
    
    return jsonify({"message": "Food suggestion added successfully"}), 201


@food_suggestions_blueprint.route('/adm/v1/food_suggestions', methods=['GET'])
@jwt_required()
def get_food_suggestions():
    # SQL para selecionar todas as sugestões de comida e informações do usuário correspondente
    sql = """
    SELECT fs.*, u.name, u.email, u.userID, u.cpf, u.paypall_email, u.phone, u.is_subscriber, u.created_at
    FROM food_suggestions fs
    JOIN users u ON fs.user_id = u.userID;
    """
    suggestions_raw = execute_query_without_params(sql, fetch_all=True)
    
    # Reformatando a estrutura de dados para incluir as informações do usuário
    # dentro de um atributo 'user' para cada sugestão de comida
    suggestions = []
    for suggestion in suggestions_raw:
        user_info = {
            "name": suggestion.pop("name"),
            "email": suggestion.pop("email"),
            "userID": suggestion.pop("userID"),
            "cpf": suggestion.pop("cpf"),
            "paypall_email": suggestion.pop("paypall_email"),
            "phone": suggestion.pop("phone"),
            "is_subscriber": suggestion.pop("is_subscriber"),
            "created_at": suggestion.pop("created_at")
        }
        suggestion["user"] = user_info
        suggestions.append(suggestion)
    
    return jsonify(suggestions), 200

@food_suggestions_blueprint.route('/adm/v1/food_suggestion/<int:suggestion_id>', methods=['DELETE'])
@jwt_required()
def delete_food_suggestion(suggestion_id):
    # SQL para deletar a sugestão de comida baseada no id
    sql = "DELETE FROM food_suggestions WHERE id = %s;"
    execute_query_with_params(sql, (suggestion_id,))
    
    return jsonify({"message": "Food suggestion deleted successfully"}), 200