from flask import Blueprint, request, jsonify
import threading
from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params
from admPanel.functions import execute_insert_query_with_params
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from principalApp.auth_clients import verify_password_change_timestamp
from principalApp.products import process_foods_flat

from flask_jwt_extended import jwt_required, get_jwt
import mysql.connector
from admPanel.auth import db_connection_pool

favorites_blueprint = Blueprint('favorites_blueprint', __name__)

@favorites_blueprint.route('/v1/get_favorite_foods', methods=['GET'])
@jwt_required()
def get_favorites():
    try:
        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()

        user_id = jwt_claims.get('user_id')

        # Consulta SQL para buscar os alimentos favoritos do usuário
        query = """
        SELECT 
            f.id, f.food_name_en, f.food_name_pt, f.food_name_es, f.portion_size_en, f.portion_size_es, f.portion_size_pt, f.group_id,
            f.calories, f.carbohydrates, f.proteins, f.alcohol, f.total_fats, f.saturated_fats, 
            f.monounsaturated_fats, f.polyunsaturated_fats, f.trans_fats, 
            f.fibers, f.calcium, f.sodium, f.magnesium, f.iron, f.zinc, 
            f.potassium, f.vitamin_a, f.vitamin_c, f.vitamin_d, f.vitamin_e, 
            f.vitamin_b1, f.vitamin_b2, f.vitamin_b3, f.vitamin_b6, 
            f.vitamin_b9, f.vitamin_b12, f.created_at, f.updated_at,
            f.weight_in_grams, f.image_url,
            GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR '; ') AS allergens,
            GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '; ') AS categories
        FROM favorites fav
        JOIN foods f ON fav.food_id = f.id
        LEFT JOIN food_allergen fa ON f.id = fa.food_id
        LEFT JOIN allergens a ON fa.allergen_id = a.id
        LEFT JOIN food_category fc ON f.id = fc.food_id
        LEFT JOIN categories c ON fc.category_id = c.id
        WHERE fav.user_id = %s
        GROUP BY f.id
        """

        params = (user_id,)
        favorite_foods = execute_query_with_params(query, params, fetch_all=True, should_commit=False)
        return_foods = process_foods_flat(favorite_foods)

        return jsonify(return_foods), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def process_foods_flat_add_favorite(result):
    if not isinstance(result, dict):
        raise ValueError("Expected a dictionary for processing food data")

    foods = []

    # Transforma food_name e portion_size em dicionários
    food_name = {
            "en": result['food_name_en'],
            "pt": result['food_name_pt'],
            "es": result['food_name_es']
        }
    portion_size = {
        "en": result['portion_size_en'] or "",
        "es": result['portion_size_es'] or "",
        "pt": result['portion_size_pt'] or ""
    }
    # Prepara o item com as informações do alimento, excluindo os campos não necessários para este contexto
    food_item = {key: result[key] for key in result if key not in [
        'group_name_en', 'group_name_pt', 'group_name_es',
        'group_description_en', 'group_description_pt', 'group_description_es',
        'group_image_url', 'food_name_en', 'food_name_pt', 'food_name_es',
        'portion_size_en', 'portion_size_es', 'portion_size_pt']}
    
    food_item['food_name'] = food_name
    food_item['portion_size'] = portion_size
    food_item['allergens'] = result.get('allergens', "").split('; ') if result.get('allergens') else []
    food_item['categories'] = result.get('categories', "").split('; ') if result.get('categories') else []

    foods.append(food_item)

    return foods

class ThreadResult:
    def __init__(self):
        self.result = None
        self.exception = None

@favorites_blueprint.route('/v1/add_favorite_food', methods=['POST'])
@jwt_required()
def add_favorite_food():
    try:
        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()
        user_id = jwt_claims.get('user_id')

        # Obter o food_id do corpo da requisição
        try:
            data = request.get_json(force=True)  # Force parsing the JSON payload
        except Exception as e:
            print("JSON parsing error:", str(e))
            return jsonify({"statusCode": "400", "message": "Invalid JSON format"}), 400

        if not data:
            return jsonify({"statusCode": "400", "message": "Request body is required"}), 400

        food_id = data.get('food_id')

        if not food_id:
            return jsonify({"statusCode": "400", "message": "Food ID is required"}), 400

        insert_result = ThreadResult()
        fetch_result = ThreadResult()

        # Função para inserir o favorito
        def insert_favorite(result):
            try:
                insert_favorite_query = """
                    INSERT IGNORE INTO favorites (user_id, food_id) 
                    VALUES (%s, %s);
                """
                execute_query_with_params(insert_favorite_query, (user_id, food_id), should_commit=True)
                result.result = True
            except Exception as e:
                result.exception = e

        # Função para recuperar os dados do alimento
        def fetch_food_data(result):
            try:
                food_query = """
                    SELECT 
                        f.id, f.food_name_en, f.food_name_pt, f.food_name_es, f.portion_size_en, f.portion_size_es, f.portion_size_pt, f.group_id,
                        f.calories, f.carbohydrates, f.proteins, f.alcohol, f.total_fats, f.saturated_fats, 
                        f.monounsaturated_fats, f.polyunsaturated_fats, f.trans_fats, 
                        f.fibers, f.calcium, f.sodium, f.magnesium, f.iron, f.zinc, 
                        f.potassium, f.vitamin_a, f.vitamin_c, f.vitamin_d, f.vitamin_e, 
                        f.vitamin_b1, f.vitamin_b2, f.vitamin_b3, f.vitamin_b6, 
                        f.vitamin_b9, f.vitamin_b12, f.created_at, f.updated_at,
                        f.weight_in_grams, f.image_url,
                        GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR '; ') AS allergens,
                        GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '; ') AS categories
                    FROM foods f
                    LEFT JOIN food_allergen fa ON f.id = fa.food_id
                    LEFT JOIN allergens a ON fa.allergen_id = a.id
                    LEFT JOIN food_category fc ON f.id = fc.food_id
                    LEFT JOIN categories c ON fc.category_id = c.id
                    WHERE f.id = %s
                    GROUP BY f.id
                """
                result.result = execute_query_with_params(food_query, (food_id,), fetch_all=False)
            except Exception as e:
                result.exception = e

        # Executar as funções em threads paralelas
        insert_thread = threading.Thread(target=insert_favorite, args=(insert_result,))
        fetch_thread = threading.Thread(target=fetch_food_data, args=(fetch_result,))

        insert_thread.start()
        fetch_thread.start()

        insert_thread.join()
        fetch_thread.join()

        if insert_result.exception:
            raise insert_result.exception
        if fetch_result.exception:
            raise fetch_result.exception

        food_data = fetch_result.result

        # Processar os dados do alimento
        processed_foods = process_foods_flat_add_favorite(food_data)
        if not processed_foods:
            return jsonify({"error": "No food data found"}), 404

        return jsonify(processed_foods[0]), 201

    except Exception as e:
        print("Exception occurred:", str(e))
        return jsonify({"error": str(e)}), 500

@favorites_blueprint.route('/v1/remove_favorite_food', methods=['DELETE'])
@jwt_required()
def remove_favorite():
    try:
        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()

        user_id = jwt_claims.get('user_id')

        # Obter o food_id do corpo da requisição
        data = request.get_json()
        food_id = data.get('food_id')

        if not food_id:
            return jsonify({"statusCode": "400", "message": "Food ID is required"}), 400

        # Consulta SQL para remover o favorito
        query = "DELETE FROM favorites WHERE user_id = %s AND food_id = %s"
        params = (user_id, food_id)
        execute_query_with_params(query, params, should_commit=True)

        return jsonify({"statusCode": "200", "message": "Favorite removed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@favorites_blueprint.route('/v1/add_favorite_exchange', methods=['POST'])
@jwt_required()
def add_exchange():
    try:
        # Log the request headers and body
        print("Request Headers:", request.headers)
        print("Request Body:", request.get_data(as_text=True))

        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()
        user_id = jwt_claims.get('user_id')

        try:
            data = request.get_json(force=True)  # Force parsing the JSON payload
        except Exception as e:
            print("JSON parsing error:", str(e))
            return jsonify({"statusCode": "400", "message": "Invalid JSON format"}), 400

        food_id = data.get('food_id')
        group_id = data.get('group_id')

        # Combined query to check existence of food and group
        check_query = """
            SELECT 
                (SELECT COUNT(*) FROM foods WHERE id = %s) AS food_exists, 
                (SELECT COUNT(*) FROM groups WHERE id = %s) AS group_exists
        """
        check_params = (food_id, group_id)
        
        result = execute_query_with_params(check_query, check_params)
        
        if result['food_exists'] == 0:
            return jsonify({'error': 'Food item not found'}), 404
        if result['group_exists'] == 0:
            return jsonify({'error': 'Group not found'}), 404

        # Insert new exchange if checks pass
        insert_query = """
            INSERT INTO exchanges_favorite (user_id, food_id, group_id, change_type_id, grams_or_calories, value_to_convert)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        insert_params = (user_id, food_id, group_id, data['change_type_id'], data['grams_or_calories'], data['value_to_convert'])
        execute_query_with_params(insert_query, insert_params, should_commit=True)

        return jsonify({'message': 'Exchange added successfully'}), 201
    except Exception as e:
        print("Exception occurred:", str(e))
        return jsonify({'error': str(e)}), 400

@favorites_blueprint.route('/v1/remove_favorite_exchange', methods=['DELETE'])
@jwt_required()
def remove_exchange():

    # Obter o ID do usuário a partir do token JWT
    jwt_claims = get_jwt()

    user_id = jwt_claims.get('user_id')
    
    # Obter o food_id do corpo da requisição
    data = request.get_json()
    food_id = data.get('food_id')
    if not food_id:
        return jsonify({"error": "Missing food_id in request body"}), 400

    sql_query = "DELETE FROM exchanges_favorite WHERE food_id = %s AND user_id = %s"
    params = (food_id, user_id)
    try:
        execute_query_with_params(sql_query, params)
        return jsonify({'message': 'Exchange removed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@favorites_blueprint.route('/v1/get_favorite_exchages', methods=['GET'])
@jwt_required()
def list_favorite_xchanges():
    try:
        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()

        user_id = jwt_claims.get('user_id')

        # Consulta SQL para buscar as trocas favoritas do usuário com todas as informações do alimento
        query = """
        SELECT 
            ef.id,
            ef.user_id,
            ef.food_id,
            ef.group_id,
            ef.change_type_id,
            ef.grams_or_calories,
            ef.value_to_convert,
            f.id as food_id,
            f.food_name_en,
            f.food_name_pt,
            f.food_name_es,
            f.portion_size_en,
            f.portion_size_es,
            f.portion_size_pt,
            f.group_id as food_group_id,
            f.calories,
            f.carbohydrates,
            f.proteins,
            f.alcohol,
            f.total_fats,
            f.saturated_fats,
            f.monounsaturated_fats,
            f.polyunsaturated_fats,
            f.trans_fats,
            f.fibers,
            f.calcium,
            f.sodium,
            f.magnesium,
            f.iron,
            f.zinc,
            f.potassium,
            f.vitamin_a,
            f.vitamin_c,
            f.vitamin_d,
            f.vitamin_e,
            f.vitamin_b1,
            f.vitamin_b2,
            f.vitamin_b3,
            f.vitamin_b6,
            f.vitamin_b9,
            f.vitamin_b12,
            f.created_at,
            f.updated_at,
            f.weight_in_grams,
            f.image_url,
            GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR '; ') AS allergens,
            GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '; ') AS categories
        FROM exchanges_favorite ef
        JOIN foods f ON ef.food_id = f.id
        LEFT JOIN food_allergen fa ON f.id = fa.food_id
        LEFT JOIN allergens a ON fa.allergen_id = a.id
        LEFT JOIN food_category fc ON f.id = fc.food_id
        LEFT JOIN categories c ON fc.category_id = c.id
        WHERE ef.user_id = %s
        GROUP BY ef.id, f.id
        """
        
        params = (user_id,)
        favorite_foods = execute_query_with_params(query, params, fetch_all=True, should_commit=False)
        
        # Processar os resultados usando a função process_foods_flat
        result = process_foods_flat_favorite(favorite_foods)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

def process_foods_flat_favorite(result):
    foods = []
    for item in result:
        # Transforma food_name e portion_size em dicionários
        food_name = {
            "en": item['food_name_en'],
            "pt": item['food_name_pt'],
            "es": item['food_name_es']
        }
        portion_size = {
            "en": item['portion_size_en'] or "",
            "es": item['portion_size_es'] or "",
            "pt": item['portion_size_pt'] or ""
        }
        
        # Prepara o item com as informações do alimento, excluindo os campos não necessários para este contexto
        food_info = {
            'food_id': item['food_id'],
            'food_name': food_name,
            'portion_size': portion_size,
            'group_id': item['food_group_id'],
            'calories': item['calories'],
            'carbohydrates': item['carbohydrates'],
            'proteins': item['proteins'],
            'alcohol': item['alcohol'],
            'total_fats': item['total_fats'],
            'saturated_fats': item['saturated_fats'],
            'monounsaturated_fats': item['monounsaturated_fats'],
            'polyunsaturated_fats': item['polyunsaturated_fats'],
            'trans_fats': item['trans_fats'],
            'fibers': item['fibers'],
            'calcium': item['calcium'],
            'sodium': item['sodium'],
            'magnesium': item['magnesium'],
            'iron': item['iron'],
            'zinc': item['zinc'],
            'potassium': item['potassium'],
            'vitamin_a': item['vitamin_a'],
            'vitamin_c': item['vitamin_c'],
            'vitamin_d': item['vitamin_d'],
            'vitamin_e': item['vitamin_e'],
            'vitamin_b1': item['vitamin_b1'],
            'vitamin_b2': item['vitamin_b2'],
            'vitamin_b3': item['vitamin_b3'],
            'vitamin_b6': item['vitamin_b6'],
            'vitamin_b9': item['vitamin_b9'],
            'vitamin_b12': item['vitamin_b12'],
            'created_at': item['created_at'],
            'updated_at': item['updated_at'],
            'weight_in_grams': item['weight_in_grams'],
            'image_url': item['image_url'],
            'allergens': item['allergens'].split('; ') if item['allergens'] else [],
            'categories': item['categories'].split('; ') if item['categories'] else []
        }
        
        # Prepara o item com as informações da troca favorita
        favorite_item = {
            'id': item['id'],
            'user_id': item['user_id'],
            'food_id': item['food_id'],
            'group_id': item['group_id'],
            'change_type_id': item['change_type_id'],
            'grams_or_calories': item['grams_or_calories'],
            'value_to_convert': item['value_to_convert'],
            'food_info': food_info
        }
        
        foods.append(favorite_item)
    
    return foods

@favorites_blueprint.route('/v2/add_favorite_exchange', methods=['POST'])
@jwt_required()
def add_exchange_v2():
    try:
        # Log the request headers and body
        print("Request Headers:", request.headers)
        print("Request Body:", request.get_data(as_text=True))

        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()
        user_id = jwt_claims.get('user_id')

        try:
            data = request.get_json(force=True)  # Force parsing the JSON payload
        except Exception as e:
            print("JSON parsing error:", str(e))
            return jsonify({"statusCode": "400", "message": "Invalid JSON format"}), 400
        
        food_info = data.get('food_info')
        if food_info:
            food_id = food_info.get('id')
            group_id = food_info.get('group_id')
        else:
            food_id = ""
            group_id = ""

        # Combined query to check existence of food and group
        check_query = """
            SELECT 
                (SELECT COUNT(*) FROM foods WHERE id = %s) AS food_exists, 
                (SELECT COUNT(*) FROM groups WHERE id = %s) AS group_exists
        """
        check_params = (food_id, group_id)
        
        result = execute_query_with_params(check_query, check_params, fetch_all=False, should_commit=False)
        
        if result['food_exists'] == 0:
            return jsonify({'error': 'Food item not found'}), 404
        if result['group_exists'] == 0:
            return jsonify({'error': 'Group not found'}), 404

        # Insert new exchange if checks pass
        insert_query = """
            INSERT INTO exchanges_favorite (user_id, food_id, group_id, change_type_id, grams_or_calories, value_to_convert)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        insert_params = (user_id, food_id, group_id, data['change_type_id'], data['grams_or_calories'], data['value_to_convert'])
        
        # Execute the insert query and get the lastrowid
        lastrowid = execute_insert_query_with_params(insert_query, insert_params)

        # Add the new id to the response data
        data['id'] = lastrowid

        return jsonify(data), 201
    except Exception as e:
        print("Exception occurred:", str(e))
        return jsonify({'error': str(e)}), 400

@favorites_blueprint.route('/v2/remove_favorite_exchange', methods=['DELETE'])
@jwt_required()
def remove_exchange_v2():

    # Obter o ID do usuário a partir do token JWT
    jwt_claims = get_jwt()

    user_id = jwt_claims.get('user_id')
    
    # Obter o food_id do corpo da requisição
    data = request.get_json()
    exchange_id = data.get('exchange_id')
    if not exchange_id:
        return jsonify({"error": "Missing exchange_id in request body"}), 400

    sql_query = "DELETE FROM exchanges_favorite WHERE id = %s AND user_id = %s"
    params = (exchange_id, user_id)
    try:
        execute_query_with_params(sql_query, params)
        return jsonify({'message': 'Exchange removed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@favorites_blueprint.route('/v2/get_favorite_exchanges', methods=['GET'])
@jwt_required()
def list_exchanges_v2():
    try:
        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()

        user_id = jwt_claims.get('user_id')

        # Consulta SQL para buscar as trocas favoritas do usuário com todas as informações do alimento
        query = """
        SELECT 
            ef.id,
            ef.user_id,
            ef.food_id,
            ef.group_id,
            ef.change_type_id,
            ef.grams_or_calories,
            ef.value_to_convert,
            f.id as food_id,
            f.food_name_en,
            f.food_name_pt,
            f.food_name_es,
            f.portion_size_en,
            f.portion_size_es,
            f.portion_size_pt,
            f.group_id as food_group_id,
            f.calories,
            f.carbohydrates,
            f.proteins,
            f.alcohol,
            f.total_fats,
            f.saturated_fats,
            f.monounsaturated_fats,
            f.polyunsaturated_fats,
            f.trans_fats,
            f.fibers,
            f.calcium,
            f.sodium,
            f.magnesium,
            f.iron,
            f.zinc,
            f.potassium,
            f.vitamin_a,
            f.vitamin_c,
            f.vitamin_d,
            f.vitamin_e,
            f.vitamin_b1,
            f.vitamin_b2,
            f.vitamin_b3,
            f.vitamin_b6,
            f.vitamin_b9,
            f.vitamin_b12,
            f.created_at,
            f.updated_at,
            f.weight_in_grams,
            f.image_url,
            GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR '; ') AS allergens,
            GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '; ') AS categories
        FROM exchanges_favorite ef
        JOIN foods f ON ef.food_id = f.id
        LEFT JOIN food_allergen fa ON f.id = fa.food_id
        LEFT JOIN allergens a ON fa.allergen_id = a.id
        LEFT JOIN food_category fc ON f.id = fc.food_id
        LEFT JOIN categories c ON fc.category_id = c.id
        WHERE ef.user_id = %s
        GROUP BY ef.id, f.id
        """
        
        params = (user_id,)
        favorite_foods = execute_query_with_params(query, params, fetch_all=True, should_commit=False)
        
        # Processar os resultados usando a função process_foods_flat
        result = process_foods_flat_favorite_v2(favorite_foods)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

def process_foods_flat_favorite_v2(result):
    foods = []
    for item in result:
        print(item)  # Adiciona um log para inspecionar o conteúdo de 'item'

        # Transforma food_name e portion_size em dicionários
        food_name = {
            "en": item.get('food_name_en', ''),
            "pt": item.get('food_name_pt', ''),
            "es": item.get('food_name_es', '')
        }
        portion_size = {
            "en": item.get('portion_size_en', ''),
            "es": item.get('portion_size_es', ''),
            "pt": item.get('portion_size_pt', '')
        }
        
        # Prepara o item com as informações do alimento, excluindo os campos não necessários para este contexto
        food_info = {
            'id': item.get('food_id'),
            'food_name': food_name,
            'portion_size': portion_size,
            'group_id': item.get('food_group_id'),
            'calories': item.get('calories'),
            'carbohydrates': item.get('carbohydrates'),
            'proteins': item.get('proteins'),
            'alcohol': item.get('alcohol'),
            'total_fats': item.get('total_fats'),
            'saturated_fats': item.get('saturated_fats'),
            'monounsaturated_fats': item.get('monounsaturated_fats'),
            'polyunsaturated_fats': item.get('polyunsaturated_fats'),
            'trans_fats': item.get('trans_fats'),
            'fibers': item.get('fibers'),
            'calcium': item.get('calcium'),
            'sodium': item.get('sodium'),
            'magnesium': item.get('magnesium'),
            'iron': item.get('iron'),
            'zinc': item.get('zinc'),
            'potassium': item.get('potassium'),
            'vitamin_a': item.get('vitamin_a'),
            'vitamin_c': item.get('vitamin_c'),
            'vitamin_d': item.get('vitamin_d'),
            'vitamin_e': item.get('vitamin_e'),
            'vitamin_b1': item.get('vitamin_b1'),
            'vitamin_b2': item.get('vitamin_b2'),
            'vitamin_b3': item.get('vitamin_b3'),
            'vitamin_b6': item.get('vitamin_b6'),
            'vitamin_b9': item.get('vitamin_b9'),
            'vitamin_b12': item.get('vitamin_b12'),
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at'),
            'weight_in_grams': item.get('weight_in_grams'),
            'image_url': item.get('image_url'),
            'allergens': item.get('allergens', '').split('; ') if item.get('allergens') else [],
            'categories': item.get('categories', '').split('; ') if item.get('categories') else []
        }
        
        # Prepara o item com as informações da troca favorita
        favorite_item = {
            'id': item.get('id'),
            'change_type_id': item.get('change_type_id'),
            'grams_or_calories': item.get('grams_or_calories'),
            'value_to_convert': item.get('value_to_convert'),
            'food_info': food_info
        }
        
        foods.append(favorite_item)
    
    return foods

@favorites_blueprint.route('/v2/get_meals', methods=['GET'])
@jwt_required()
def get_meals():
    try:
        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()

        user_id = jwt_claims.get('user_id')

        # Consulta SQL para buscar as trocas favoritas do usuário com todas as informações do alimento
        query = "SELECT * FROM meals WHERE user_id = %s"
        
        params = (user_id,)
        meals = execute_query_with_params(query, params, fetch_all=True, should_commit=False)
        
        return jsonify(meals), 200
    except Exception as e: 
        return jsonify({'error': str(e)}), 400

@favorites_blueprint.route('/v1/get_foods_from_favorite_meal', methods=['POST'])
def get_meal_exchanges():

    print(request.get_json())
    try:
        # Verifica se o body contém o meal_id
        data = request.get_json()
        if not data or 'meal_id' not in data:
            return jsonify({'status': 'error', 'message': 'meal_id is required'}), 400

        meal_id = data['meal_id']

        # Buscar os meal_exchanges_favorites
        meal_exchanges_query = """
            SELECT * FROM meal_exchanges_favorite WHERE meal_id = %s
        """
        exchanges = execute_query_with_params(meal_exchanges_query, (meal_id,), fetch_all=True)

        # Buscar o alimento completo para cada meal_exchange
        food_query = """
        SELECT 
            f.id, f.food_name_en, f.food_name_pt, f.food_name_es, f.portion_size_en, f.portion_size_es, f.portion_size_pt, f.group_id,
            g.name_en AS group_name_en, g.name_pt AS group_name_pt, g.name_es AS group_name_es,
            g.description_en AS group_description_en, g.description_pt AS group_description_pt, g.description_es AS group_description_es,
            g.image_url AS group_image_url, g.main_nutrient AS group_main_nutrient,
            f.calories, f.carbohydrates, f.proteins, f.alcohol, f.total_fats, f.saturated_fats, 
            f.monounsaturated_fats, f.polyunsaturated_fats, f.trans_fats, 
            f.fibers, f.calcium, f.sodium, f.magnesium, f.iron, f.zinc, 
            f.potassium, f.vitamin_a, f.vitamin_c, f.vitamin_d, f.vitamin_e, 
            f.vitamin_b1, f.vitamin_b2, f.vitamin_b3, f.vitamin_b6, 
            f.vitamin_b9, f.vitamin_b12, f.created_at, f.updated_at,
            f.weight_in_grams, f.image_url,
            GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR '; ') AS allergens,
            GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '; ') AS categories
        FROM foods f
        LEFT JOIN groups g ON f.group_id = g.id
        LEFT JOIN food_allergen fa ON f.id = fa.food_id
        LEFT JOIN allergens a ON fa.allergen_id = a.id
        LEFT JOIN food_category fc ON f.id = fc.food_id
        LEFT JOIN categories c ON fc.category_id = c.id
        WHERE f.id = %s
        GROUP BY f.id;
        """

        for exchange in exchanges:
            exchange["value_to_convert"] = str(exchange["value_to_convert"])

        return jsonify(exchanges), 200
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'message': str(e)}), 401

@favorites_blueprint.route('/v1/save_meal', methods=['POST'])
@jwt_required()
def save_meal():
    data = request.json
    meal_name = data.get('meal_name')
    jwt_claims = get_jwt()
    user_id = jwt_claims.get('user_id')
    change_type_id = data.get('change_type_id')
    meal_exchanges_favorites = data.get('meal_exchanges_favorites', [])

    if not meal_exchanges_favorites:
        return jsonify({'status': 'error', 'message': 'No meal exchanges provided'}), 400

    try:
        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        # Inserir o meal e obter o meal_id
        meal_insert_query = """
            INSERT INTO meals (meal_name, user_id, change_type_id) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(meal_insert_query, (meal_name, user_id, change_type_id))
        meal_id = cursor.lastrowid

        if not meal_id:
            connection.rollback()
            return jsonify({'status': 'error', 'message': 'Failed to insert meal'}), 400

        # Inserir os meal_exchanges_favorites
        meal_exchange_insert_query = """
            INSERT INTO meal_exchanges_favorite 
            (meal_id, food_id, group_id, grams_or_calories, value_to_convert) 
            VALUES (%s, %s, %s, %s, %s)
        """
        for exchange in meal_exchanges_favorites:
            cursor.execute(meal_exchange_insert_query, (
                meal_id, 
                exchange['food_id'], 
                exchange['group_id'], 
                exchange['grams_or_calories'], 
                exchange['value_to_convert']
            ))

        # Consultar o meal recém-criado para retornar no formato especificado
        meal_select_query = """
            SELECT meal_id, meal_name, change_type_id, created_at 
            FROM meals 
            WHERE meal_id = %s
        """
        cursor.execute(meal_select_query, (meal_id,))
        meal = cursor.fetchone()

        if not meal:
            connection.rollback()
            return jsonify({'status': 'error', 'message': 'Failed to retrieve meal'}), 400

        connection.commit()
        return jsonify(meal), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400

    finally:
        cursor.close()
        connection.close()

@favorites_blueprint.route('/v1/delete_meal', methods=['DELETE'])
@jwt_required()
def delete_meal():
    try:
        # Obter o ID do usuário a partir do token JWT
        jwt_claims = get_jwt()
        user_id = jwt_claims.get('user_id')

        # Obter o meal_id do corpo da requisição
        data = request.get_json()
        meal_id = data.get('meal_id')

        if not meal_id:
            return jsonify({"statusCode": "400", "message": "Meal ID is required"}), 400

        # Verificar se o meal existe e pertence ao usuário antes de deletar
        check_meal_query = "SELECT meal_id FROM meals WHERE meal_id = %s AND user_id = %s"
        meal_exists = execute_query_with_params(check_meal_query, (meal_id, user_id), fetch_all=False)

        if not meal_exists:
            return jsonify({"statusCode": "404", "message": "Meal not found or does not belong to the user"}), 404

        # Deletar o meal
        delete_meal_query = "DELETE FROM meals WHERE meal_id = %s AND user_id = %s"
        execute_query_with_params(delete_meal_query, (meal_id, user_id), should_commit=True)

        return jsonify({"statusCode": "200", "message": "Meal deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
