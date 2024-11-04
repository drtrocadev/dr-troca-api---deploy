from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from datetime import datetime

from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params
from principalApp.functions import process_food_items
from principalApp.functions import process_foods_flat
from principalApp.functions import get_food_by_id
from principalApp.functions import find_similar_foods
from principalApp.functions import find_daily_similar_foods
from principalApp.functions import find_hangry_similar_foods
from principalApp.functions import find_not_hangry_similar_foods
from principalApp.cache import cache_foods

products_blueprint = Blueprint('products_blueprint', __name__)

# Função para obter todos os alimentos do banco de dados
def fetch_all_foods():
    global cache_foods
    if cache_foods == []:
        sql_query = """
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
                f.vitamin_b9, f.vitamin_b12, f.caffeine, f.taurine, f.featured, f.created_at, f.updated_at,
                f.weight_in_grams, f.image_url, f.thumb_url,
                GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR '; ') AS allergens,
                GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '; ') AS categories
            FROM foods f
            LEFT JOIN groups g ON f.group_id = g.id
            LEFT JOIN food_allergen fa ON f.id = fa.food_id
            LEFT JOIN allergens a ON fa.allergen_id = a.id
            LEFT JOIN food_category fc ON f.id = fc.food_id
            LEFT JOIN categories c ON fc.category_id = c.id
            GROUP BY f.id, g.id
        """
        cache_foods = execute_query_without_params(sql_query, fetch_all=True)
        return cache_foods
    else:
        return cache_foods
    
# Função para obter todos os alimentos do banco de dados
def update_cache_all_foods():
    global cache_foods
    sql_query = """
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
            f.vitamin_b9, f.vitamin_b12, f.caffeine, f.taurine, f.featured, f.created_at, f.updated_at,
            f.weight_in_grams, f.image_url, f.thumb_url,
            GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR '; ') AS allergens,
            GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '; ') AS categories
        FROM foods f
        LEFT JOIN groups g ON f.group_id = g.id
        LEFT JOIN food_allergen fa ON f.id = fa.food_id
        LEFT JOIN allergens a ON fa.allergen_id = a.id
        LEFT JOIN food_category fc ON f.id = fc.food_id
        LEFT JOIN categories c ON fc.category_id = c.id
        GROUP BY f.id, g.id
    """
    cache_foods = execute_query_without_params(sql_query, fetch_all=True)


# Função para remover duplicados
def remove_duplicates_by_food_name_pt(response):
    unique_response = {}
    for item in response:
        food_name_pt = item["food_name"]["pt"]
        if food_name_pt not in unique_response:
            unique_response[food_name_pt] = item
    return list(unique_response.values())

# Rota para obter todos os alimentos, agrupando conforme necessário
@products_blueprint.route('/v1/get_all_foods', methods=['GET'])
def get_foods():
    try:
        result = fetch_all_foods()
        foods_by_group = process_food_items(result)
        return jsonify(foods_by_group)
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"error": str(e)}), 500

# Funções de Processamento
def process_foods(change_type_id, food_id, group_id, grams_or_calories, value_to_convert):
    if change_type_id == 0:
        foods_of_group = daily_changes(food_id, group_id, grams_or_calories, value_to_convert)
    elif change_type_id == 2:
        foods_of_group = hangry(food_id, group_id, grams_or_calories, value_to_convert)
    elif change_type_id == 1:
        foods_of_group = not_hangry(food_id, group_id, grams_or_calories, value_to_convert)
    elif change_type_id == 3:
        foods_of_group = emergency(food_id, grams_or_calories, value_to_convert)
    else:
        return {'status': 'error', 'message': 'still not implemented'}, 900

    return process_foods_flat(foods_of_group), 200

# Exemplo de rota utilizando process_foods
@products_blueprint.route('/v3/get_exchanges', methods=['POST'])
def get_exchanges():
    data = request.json
    change_type_id = data.get('change_type_id')
    food_id = data['food_id']
    group_id = data['group_id']
    grams_or_calories = data['grams_or_calories']
    value_to_convert = data['value_to_convert']

    if group_id is None:
        return jsonify({'error': 'groupId is required in food data'}), 400
    if value_to_convert == 0:
        return jsonify({'error': 'value_to_convert need to be more than 0'}), 401
    
    try:
        response, status_code = process_foods(change_type_id, food_id, group_id, grams_or_calories, value_to_convert)
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Funções de Processamento de Alimentos
def daily_changes(food_id, group_id, grams_or_calories, value_to_convert):
    try:
        all_foods = fetch_all_foods()
        
        # Filtra apenas os alimentos com o group_id especificado
        foods_in_group = [food for food in all_foods if food.get('group_id') == group_id]
        
        actual_food = get_food_by_id(food_id=food_id, foods=foods_in_group)
        dia_a_dia_foods = find_daily_similar_foods(
            all_foods_of_group=foods_in_group,
            actual_food=actual_food,
            grams_or_calories=grams_or_calories,
            value_to_convert=value_to_convert,
            main_nutrient=actual_food["group_main_nutrient"]
        )
        return dia_a_dia_foods
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


def hangry(food_id, group_id, grams_or_calories, value_to_convert):
    try:
        all_foods = fetch_all_foods()
        foods_in_group = [food for food in all_foods if food.get('group_id') == group_id]
        actual_food = get_food_by_id(food_id=food_id, foods=all_foods)
        hangry_foods = find_hangry_similar_foods(
            all_foods_of_group=foods_in_group,
            actual_food=actual_food,
            grams_or_calories=grams_or_calories,
            value_to_convert=value_to_convert,
            main_nutrient=actual_food["group_main_nutrient"]
        )
        return hangry_foods
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def not_hangry(food_id, group_id, grams_or_calories, value_to_convert):
    try:
        all_foods = fetch_all_foods()
        actual_food = get_food_by_id(food_id=food_id, foods=all_foods)
        not_hangry_foods = find_not_hangry_similar_foods(
            all_foods_of_group=all_foods,
            actual_food=actual_food,
            grams_or_calories=grams_or_calories,
            value_to_convert=value_to_convert,
            main_nutrient=actual_food["group_main_nutrient"]
        )
        return not_hangry_foods
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def emergency(food_id, grams_or_calories, value_to_convert):
    try:
        all_foods = fetch_all_foods()
        actual_food = get_food_by_id(food_id=food_id, foods=all_foods)

        # Obter o grupo do alimento atual
        all_groups = {food['group_id']: food['group_main_nutrient'] for food in all_foods}
        actual_group_main_nutrient = all_groups.get(actual_food['group_id'])
        
        if not actual_group_main_nutrient:
            return jsonify({'error': 'Group not found for the actual food'}), 404

        # Filtrar alimentos com o mesmo nutriente principal
        similar_foods = [food for food in all_foods if all_groups[food['group_id']] == actual_group_main_nutrient]
        
        dia_a_dia_foods = find_daily_similar_foods(
            all_foods_of_group=similar_foods,
            actual_food=actual_food,
            grams_or_calories=grams_or_calories,
            value_to_convert=value_to_convert,
            main_nutrient=actual_group_main_nutrient
        )
        
        return dia_a_dia_foods
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@products_blueprint.route('/v3/get_meal_exchanges', methods=['POST'])
def get_exchanges_multiple_v3():
    data = request.json
    print(data)
    foods = data.get('foods', [])
    change_type_id = data.get('change_type_id')

    if change_type_id is None:
        return jsonify({'error': 'change_type_id is required'}), 405
    if not isinstance(foods, list) or not foods:
        return jsonify({'error': 'foods must be a non-empty list'}), 404

    results = {}  # Inicializa o dicionário para armazenar os resultados

    for food in foods:
        food_id = food.get('food_id')
        group_id = food.get('group_id')
        grams_or_calories = food.get('grams_or_calories')
        value_to_convert = food.get('value_to_convert')

        if group_id is None:
            return jsonify({'error': 'group_id is required for all foods'}), 403

        # Conversão de value_to_convert para float se for uma string numérica
        try:
            value_to_convert = float(value_to_convert)
        except ValueError:
            return jsonify({'error': 'value_to_convert must be a valid number'}), 402

        if value_to_convert == 0:
            return jsonify({'error': 'value_to_convert must be more than 0'}), 401

        try:
            response, status_code = process_foods(change_type_id, food_id, group_id, grams_or_calories, value_to_convert)
            if status_code == 200:
                results[food_id] = remove_duplicates_by_food_name_pt(response)  # Adiciona o food_id como chave no dicionário
            else:
                return jsonify(response), status_code
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Retorna o dicionário de resultados após o processamento dos alimentos
    return jsonify(results), 200