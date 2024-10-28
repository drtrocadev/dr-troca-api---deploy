from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
import time

from admPanel.auth import db_connection_pool
from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params
from admPanel.functions import execute_query
from admPanel.functions import upload_image_and_get_url
from admPanel.functions import generate_and_upload_thumbnail
from admPanel.functions import upload_category_cover_and_get_url

adm_foods_blueprint = Blueprint('adm_foods_blueprint', __name__)

@adm_foods_blueprint.route('/adm/v2/get_all_foods', methods=['GET'])
@jwt_required()
def adm_get_foods_v2():
    
    try:      
        # SQL Query para buscar todos os alimentos com suas categorias e alergias relacionadas
        sql_query = """
        SELECT 
            f.id, f.food_name_en, f.food_name_pt, f.food_name_es, f.group_id, f.calories,
            f.portion_size_en, f.portion_size_es, f.portion_size_pt,
            f.carbohydrates, f.proteins, f.alcohol, f.total_fats, f.saturated_fats, 
            f.monounsaturated_fats, f.polyunsaturated_fats, f.trans_fats, 
            f.fibers, f.calcium, f.sodium, f.magnesium, f.iron, f.zinc, 
            f.potassium, f.vitamin_a, f.vitamin_c, f.vitamin_d, f.vitamin_e, 
            f.vitamin_b1, f.vitamin_b2, f.vitamin_b3, f.vitamin_b6, 
            f.vitamin_b9, f.vitamin_b12, f.created_at, f.updated_at,
            f.weight_in_grams, f.image_url,
            GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
            GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR ', ') AS allergens
        FROM foods f
        LEFT JOIN food_category fc ON f.id = fc.food_id
        LEFT JOIN categories c ON fc.category_id = c.id
        LEFT JOIN food_allergen fa ON f.id = fa.food_id
        LEFT JOIN allergens a ON fa.allergen_id = a.id
        GROUP BY f.id
        """

        # Chama a função execute_query para buscar todos os itens com as modificações necessárias
        result = execute_query_without_params(sql_query, fetch_all=True)
        
        # Converte as strings 'categories' e 'allergens' em listas
        for item in result:
            item['categories'] = item['categories'].split(', ') if item['categories'] else []
            item['allergens'] = item['allergens'].split(', ') if item['allergens'] else []

        return jsonify(result)

    except Exception as e:
        # Em caso de erro, retorna uma mensagem de erro
        print(f"Erro: {e}")
        return jsonify({"error": str(e)}), 500
    
@adm_foods_blueprint.route('/adm/v1/delete_food/<int:food_id>', methods=['DELETE'])
@jwt_required()
def adm_delete_food(food_id):
    identity = get_jwt_identity()
    try:
        sql_query = """
        DELETE FROM foods
        WHERE id = %s
        """

        # Execute the query to delete the food
        execute_query(sql_query, params=(food_id,))

        return jsonify({"message": "Food deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Crie um dicionário apenas com os campos necessários
        log_data = {
            'food_id': f'{food_id}',
            'changed_by': identity,  # Usando a variável identity para identificar quem fez a alteração
            'log_type': "DELETE"  # Definindo o tipo de log como "CREATE"
        }

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = ", ".join([f"{key}={value}" for key, value in log_data.items()])
        print(f"{identity} criou um item as [{timestamp}]. Created fields: {log_message}")

        # Construindo a query de inserção apenas com os campos necessários
        sql_insert_log = """
        INSERT INTO food_update_logs (
            food_id, changed_by, log_type
        ) VALUES (%(food_id)s, %(changed_by)s, %(log_type)s)
        """

        execute_query(sql_insert_log, log_data)
  
@adm_foods_blueprint.route('/adm/v4/add_food', methods=['POST'])
@jwt_required()
def adm_add_food_v4():
    identity = get_jwt_identity()
    conn = None
    expected_params = {}
    food_id = 0
    image_url = ""
    conn = None
    try:
        data = request.json
        expected_params = [
            'food_name_en', 'food_name_pt', 'food_name_es', 'portion_size_en', 'portion_size_es', 'portion_size_pt', 'group_id', 'image_url', 'weight_in_grams',
            'calories', 'carbohydrates', 'proteins', 'alcohol', 'total_fats', 'saturated_fats', 'monounsaturated_fats',
            'polyunsaturated_fats', 'trans_fats', 'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc',
            'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_b1', 'vitamin_b2',
            'vitamin_b3', 'vitamin_b6', 'vitamin_b9', 'vitamin_b12'
        ]
        missing_params = [param for param in expected_params if param not in data]

        if missing_params:
            return jsonify({
                "error": "Missing parameters",
                "missing_parameters": missing_params
            }), 400

        conn = db_connection_pool.get_connection()  # Substitua pela sua função real de conexão ao banco
        conn.autocommit = False  # Desativa o commit automático
        cursor = conn.cursor()

        # Atualiza a URL da imagem se fornecida, caso contrário, mantém a existente
        if data['image_url'].startswith("http"):
            data['image_url'] = data['image_url']
            image_url = data['image_url']
        else:
            image_url = upload_image_and_get_url(data['image_url'])
            data['image_url'] = image_url

        sql_insert_food = """
        INSERT INTO foods (food_name_en, food_name_pt, food_name_es, portion_size_en, portion_size_es, portion_size_pt, group_id, image_url, weight_in_grams, calories, carbohydrates, proteins, alcohol, total_fats, 
        saturated_fats, monounsaturated_fats, polyunsaturated_fats, trans_fats, fibers, calcium, sodium, magnesium, 
        iron, zinc, potassium, vitamin_a, vitamin_c, vitamin_d, vitamin_e, vitamin_b1, vitamin_b2, vitamin_b3, 
        vitamin_b6, vitamin_b9, vitamin_b12) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Parâmetros para a inserção do alimento
        params = (
            data['food_name_en'], data['food_name_pt'], data['food_name_es'],
            data['portion_size_en'], data['portion_size_es'], data['portion_size_pt'],
            data['group_id'], image_url, data['weight_in_grams'],
            data['calories'], data['carbohydrates'], data['proteins'], data ['alcohol'],
            data['total_fats'], data['saturated_fats'], data['monounsaturated_fats'], 
            data['polyunsaturated_fats'], data['trans_fats'], data['fibers'], data['calcium'], data['sodium'], 
            data['magnesium'], data['iron'], data['zinc'], data['potassium'], data['vitamin_a'], data['vitamin_c'], 
            data['vitamin_d'], data['vitamin_e'], data['vitamin_b1'], data['vitamin_b2'], data['vitamin_b3'], 
            data['vitamin_b6'], data['vitamin_b9'], data['vitamin_b12']
        )
        
        cursor.execute(sql_insert_food, params)
        food_id = cursor.lastrowid

        if 'categories' in data:
            for category in data['categories']:
                category_id = find_category(category)
                if category_id:
                    insert_into_food_category(cursor, food_id, category_id)

        if 'allergens' in data:
            for allergen in data['allergens']:
                allergen_id = find_allergen(allergen)
                if allergen_id:
                    insert_into_food_allergen(cursor, food_id, allergen_id)

        conn.commit()  # Commita a transação se tudo ocorrer bem

        return jsonify({"success": True, "message": "Food added successfully", "food_id": food_id})
    except Exception as e:
        if conn:
            conn.rollback()  # Desfaz todas as operações se ocorrer um err
        print(e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

        if cursor:
            cursor.close()

        # Crie um dicionário para armazenar os parâmetros esperados e adicionar o food_id
        log_data = {}
        log_data['food_id'] = f'{food_id}'

        # Adicione todos os parâmetros que estavam originalmente em expected_params
        for param in [
            'food_name_en', 'food_name_pt', 'food_name_es', 'portion_size_en', 'portion_size_es', 'portion_size_pt',
            'group_id', 'image_url', 'weight_in_grams', 'calories', 'carbohydrates', 'proteins', 'alcohol', 'total_fats',
            'saturated_fats', 'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats', 'fibers', 'calcium', 'sodium',
            'magnesium', 'iron', 'zinc', 'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_b1',
            'vitamin_b2', 'vitamin_b3', 'vitamin_b6', 'vitamin_b9', 'vitamin_b12'
        ]:
            log_data[param] = data.get(param)

        log_data['categories'] = ','.join(data.get('categories', [])) if 'categories' in data else None
        log_data['allergens'] = ','.join(data.get('allergens', [])) if 'allergens' in data else None
        log_data['changed_by'] = identity  # Usando a variável identity para identificar quem fez a alteração
        log_data['log_type'] = "CREATE"  # Definindo o tipo de log como "CREATE"
        log_data['image_url'] = image_url

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = ", ".join([f"{key}={value}" for key, value in log_data.items()])
        print(f"{identity} criou um item as [{timestamp}]. Created fields: {log_message}")

        # Construindo a query de inserção atualizada
        sql_insert_log = """
        INSERT INTO food_update_logs (
            food_id, food_name_en, food_name_pt, food_name_es, portion_size_en, portion_size_es, portion_size_pt,
            group_id, image_url, weight_in_grams, calories, carbohydrates, proteins, alcohol, total_fats,
            saturated_fats, monounsaturated_fats, polyunsaturated_fats, trans_fats, fibers, calcium, sodium,
            magnesium, iron, zinc, potassium, vitamin_a, vitamin_c, vitamin_d, vitamin_e, vitamin_b1,
            vitamin_b2, vitamin_b3, vitamin_b6, vitamin_b9, vitamin_b12, categories, allergens, changed_by, log_type
        ) VALUES (%(food_id)s, %(food_name_en)s, %(food_name_pt)s, %(food_name_es)s, %(portion_size_en)s, %(portion_size_es)s, %(portion_size_pt)s,
                %(group_id)s, %(image_url)s, %(weight_in_grams)s, %(calories)s, %(carbohydrates)s, %(proteins)s, %(alcohol)s, %(total_fats)s,
                %(saturated_fats)s, %(monounsaturated_fats)s, %(polyunsaturated_fats)s, %(trans_fats)s,
                %(fibers)s, %(calcium)s, %(sodium)s, %(magnesium)s, %(iron)s, %(zinc)s, %(potassium)s,
                %(vitamin_a)s, %(vitamin_c)s, %(vitamin_d)s, %(vitamin_e)s, %(vitamin_b1)s, %(vitamin_b2)s,
                %(vitamin_b3)s, %(vitamin_b6)s, %(vitamin_b9)s, %(vitamin_b12)s, %(categories)s, %(allergens)s,
                %(changed_by)s, %(log_type)s)
        """

        execute_query(sql_insert_log, log_data)


@adm_foods_blueprint.route('/adm/v2/edit_food', methods=['POST'])
@jwt_required()
def adm_edit_food_v2():
    identity = get_jwt_identity()
    updated_data = {}
    try:
        data = request.json

        # Certifica-se de que o ID do alimento está presente
        if 'id' not in data:
            return jsonify({"error": "Missing food ID"}), 400

        # Atualiza a URL da imagem se fornecida, caso contrário, mantém a existente
        if 'image_url' in data:
            if data['image_url'].startswith("http"):
                data['image_url'] = data['image_url']
            else:
                image_url = upload_image_and_get_url(data['image_url'])
                data['image_url'] = image_url
            updated_data['image_url'] = data['image_url']  # Armazena a atualização

        # Campos que podem ser atualizados
        updatable_fields = [
            'food_name_en', 'food_name_pt', 'food_name_es', 'portion_size_en', 'portion_size_es', 'portion_size_pt', 'group_id', 'image_url',
            'weight_in_grams', 'calories', 'carbohydrates', 'proteins', 'alcohol', 'total_fats', 
            'saturated_fats', 'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats', 
            'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc', 'potassium', 
            'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_b1', 'vitamin_b2', 
            'vitamin_b3', 'vitamin_b6', 'vitamin_b9', 'vitamin_b12'
        ]

        set_clause = ', '.join([f"{field} = %s" for field in updatable_fields if field in data])
        params = [data[field] for field in updatable_fields if field in data]
        updated_data.update({field: data[field] for field in updatable_fields if field in data})

        if not params:
            return jsonify({"error": "No updatable fields provided"}), 400

        params.append(data['id'])  # Adiciona o ID do produto ao final dos parâmetros para a cláusula WHERE

        # Consulta SQL para atualizar o produto
        sql_update_food = f"UPDATE foods SET {set_clause} WHERE id = %s"

        # Executa a atualização
        execute_query(sql_update_food, params)

        delete_existing_allergens(data['id'])
        delete_existing_categories(data['id'])

        # Associa apenas com categorias existentes
        if 'categories' in data:
            category_ids = [find_category(category) for category in data['categories'] if find_category(category)]
            if category_ids:  # Só associa se existirem categorias válidas
                update_food_categories(data['id'], category_ids)
            updated_data['categories'] = category_ids

        # Associa apenas com alergênicos existentes
        if 'allergens' in data:
            allergen_ids = [find_allergen(allergen) for allergen in data['allergens'] if find_allergen(allergen)]
            if allergen_ids:  # Só associa se existirem alergênicos válidos
                update_food_allergens(data['id'], allergen_ids)
            updated_data['allergens'] = allergen_ids

        return jsonify({"success": True, "message": "Food updated successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if updated_data:
            # Garante que o ID do alimento esteja incluído nos dados a serem logados
            updated_data['id'] = data.get('id')

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = ", ".join([f"{key}={value}" for key, value in updated_data.items()])
            print(f"{identity} editou um item as [{timestamp}]. Updated fields: {log_message}")

            log_data = {field: updated_data.get(field, None) for field in updatable_fields}
            log_data['id'] = data.get('id')  # Certifica-se de que o 'id' está presente
            log_data['categories'] = ','.join(data.get('categories', [])) if 'categories' in data else None
            log_data['allergens'] = ','.join(data.get('allergens', [])) if 'allergens' in data else None
            log_data['changed_by'] = identity  # Usando a variável identity para identificar quem fez a alteração
            log_data['log_type'] = "EDIT"

            # Construindo a query de inserção atualizada
            sql_insert_log = """
                INSERT INTO food_update_logs (
                    food_id, food_name_en, food_name_pt, food_name_es, portion_size_en, portion_size_es, portion_size_pt, group_id, image_url,
                    weight_in_grams, calories, carbohydrates, proteins, alcohol, total_fats,
                    saturated_fats, monounsaturated_fats, polyunsaturated_fats, trans_fats,
                    fibers, calcium, sodium, magnesium, iron, zinc, potassium,
                    vitamin_a, vitamin_c, vitamin_d, vitamin_e, vitamin_b1, vitamin_b2,
                    vitamin_b3, vitamin_b6, vitamin_b9, vitamin_b12, categories, allergens,
                    changed_by, log_type
                ) VALUES (
                    %(id)s, %(food_name_en)s, %(food_name_pt)s, %(food_name_es)s, %(portion_size_en)s, %(portion_size_es)s, %(portion_size_pt)s, %(group_id)s, %(image_url)s,
                    %(weight_in_grams)s, %(calories)s, %(carbohydrates)s, %(proteins)s, %(alcohol)s, %(total_fats)s,
                    %(saturated_fats)s, %(monounsaturated_fats)s, %(polyunsaturated_fats)s, %(trans_fats)s,
                    %(fibers)s, %(calcium)s, %(sodium)s, %(magnesium)s, %(iron)s, %(zinc)s, %(potassium)s,
                    %(vitamin_a)s, %(vitamin_c)s, %(vitamin_d)s, %(vitamin_e)s, %(vitamin_b1)s, %(vitamin_b2)s,
                    %(vitamin_b3)s, %(vitamin_b6)s, %(vitamin_b9)s, %(vitamin_b12)s, %(categories)s, %(allergens)s,
                    %(changed_by)s, %(log_type)s
                )
            """

            execute_query(sql_insert_log, log_data)

    
def find_category(category_name):
    # Dicionário estático com os mapeamentos de nome de categoria para ID
    categories = {
        'vegan': 2,
        'vegetarian': 3
    }
    
    # Retorna o ID da categoria correspondente ao nome, se existir
    return categories.get(category_name)

def find_allergen(allergen_name):
    # Dicionário estático com os mapeamentos de nome de alergênico para ID
    allergens = {
        'gluten': 2,
        'peanut': 3,
        'eggs': 4,
        'soy': 5,
        'tropomyosin': 6,
        'dairy': 7,
        'phenylalanine': 8,
        'lactose': 9
    }
    
    # Retorna o ID do alergênico correspondente ao nome, se existir
    return allergens.get(allergen_name)

def insert_into_food_category(cursor, food_id, category_id):
    sql = "INSERT INTO food_category (food_id, category_id) VALUES (%s, %s)"
    try:
        cursor.execute(sql, (food_id, category_id))
    except Exception as e:
        raise Exception(f"Erro ao inserir na tabela food_category: {e}")

def insert_into_food_allergen(cursor, food_id, allergen_id):
    sql = "INSERT INTO food_allergen (food_id, allergen_id) VALUES (%s, %s)"
    try:
        cursor.execute(sql, (food_id, allergen_id))
    except Exception as e:
        raise Exception(f"Erro ao inserir na tabela food_allergen: {e}")

def update_food_categories(food_id, category_ids):
    # Em seguida, insere as novas categorias, se houver
    if category_ids:
        # Constrói uma lista de tuplas (food_id, category_id) para inserção em lote
        values_to_insert = [(food_id, category_id) for category_id in category_ids]

        # Consulta SQL para inserir várias linhas ao mesmo tempo
        sql = "INSERT INTO food_category (food_id, category_id) VALUES (%s, %s)"
        
        try:
            # Executa a consulta uma vez com todos os valores
            execute_query(sql, values_to_insert, many=True)
        except Exception as e:
            print(f"Erro ao inserir na tabela food_category: {e}")

def update_food_allergens(food_id, allergen_ids):
    # Em seguida, insere os novos alergênicos, se houver
    if allergen_ids:
        # Constrói uma lista de tuplas (food_id, allergen_id) para inserção em lote
        values_to_insert = [(food_id, allergen_id) for allergen_id in allergen_ids]

        # Consulta SQL para inserir várias linhas ao mesmo tempo
        sql = "INSERT INTO food_allergen (food_id, allergen_id) VALUES (%s, %s)"
        
        try:
            # Executa a consulta uma vez com todos os valores
            execute_query(sql, values_to_insert, many=True)
        except Exception as e:
            print(f"Erro ao inserir na tabela food_allergen: {e}")

def delete_existing_categories(food_id):
    sql = "DELETE FROM food_category WHERE food_id = %s"
    try:
        execute_query(sql, (food_id,))
    except Exception as e:
        print(f"Erro ao deletar categorias existentes para o alimento com ID {food_id}: {e}")

def delete_existing_allergens(food_id):
    sql = "DELETE FROM food_allergen WHERE food_id = %s"
    try:
        execute_query(sql, (food_id,))
    except Exception as e:
        print(f"Erro ao deletar alergênicos existentes para o alimento com ID {food_id}: {e}")

# Grupos alimentares

@adm_foods_blueprint.route('/adm/v1/get_groups', methods=['GET'])
def get_items():
    # Consulta SQL para obter todos os itens
    query = "SELECT * FROM groups"  # Substitua 'nome_da_tabela' pelo nome real da sua tabela
    
    # Executar a consulta
    try:
        items = execute_query_without_params(query, fetch_all=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # Retornar a resposta em formato JSON
    return jsonify(items)

@adm_foods_blueprint.route('/adm/v1/add_group', methods=['POST'])
def add_group():
    data = request.json
    if 'image_url' not in data:
        return jsonify({'error': 'Image is required'}), 400
    
    # Verificar se a chave 'image_url' está presente
    if 'image_url' in data:
        if data['image_url'].startswith("http"):
            # Se a URL começar com "http", usar como está
            image_url = data['image_url']
        else:
            # Caso contrário, tratar como imagem em base64
                image_url = upload_category_cover_and_get_url(data['image_url'])
    else:
        image_url = ''

    # Preparar os dados para salvar no banco de dados
    db_data = {
        'name_en': data.get('name_en', ''),
        'name_pt': data.get('name_pt', ''),
        'name_es': data.get('name_es', ''),
        'description_en': data.get('description_en', ''),
        'description_pt': data.get('description_pt', ''),
        'description_es': data.get('description_es', ''),
        'image_url': image_url,
        'main_nutrient': data.get('main_nutrient', '')
    }

    # Query para inserir os dados na tabela
    query = """
        INSERT INTO groups (name_en, name_pt, name_es, description_en, description_pt, description_es, image_url, main_nutrient)
        VALUES (%(name_en)s, %(name_pt)s, %(name_es)s, %(description_en)s, %(description_pt)s, %(description_es)s, %(image_url)s, %(main_nutrient)s)
    """

    # Obter uma conexão do pool
    connection = db_connection_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute(query, db_data)
    group_id = cursor.lastrowid
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'message': 'Data saved successfully', 'group_id': group_id}), 201


@adm_foods_blueprint.route('/adm/v1/delete_group/<int:id>', methods=['DELETE'])
def delete_item(id):
    # Query SQL para deletar um item pelo id
    query = "DELETE FROM groups WHERE id = %(id)s"
    
    try:
        # Executar a query usando a função existente
        execute_query(query, {'id': id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'message': 'Item deleted successfully'}), 200

@adm_foods_blueprint.route('/adm/v1/edit_group/<int:id>', methods=['PUT'])
def edit_item(id):
    data = request.json
    
    # Verificar se a chave 'image_url' está presente
    if 'image_url' in data:
        if data['image_url'].startswith("http"):
            # Se a URL começar com "http", usar como está
            image_url = data['image_url']
        else:
            # Caso contrário, tratar como imagem em base64
            image_url = upload_category_cover_and_get_url(data['image_url'])
    else:
        image_url = ''
    
    # Preparar os dados para atualização
    db_data = {
        'id': id,
        'name_en': data.get('name_en', ''),
        'name_pt': data.get('name_pt', ''),
        'name_es': data.get('name_es', ''),
        'description_en': data.get('description_en', ''),
        'description_pt': data.get('description_pt', ''),
        'description_es': data.get('description_es', ''),
        'image_url': image_url,
        'main_nutrient': data.get('main_nutrient', '')
    }
    
    # Query SQL para atualizar um item pelo id
    query = """
        UPDATE groups
        SET name_en = %(name_en)s,
            name_pt = %(name_pt)s,
            name_es = %(name_es)s,
            description_en = %(description_en)s,
            description_pt = %(description_pt)s,
            description_es = %(description_es)s,
            image_url = %(image_url)s,
            main_nutrient = %(main_nutrient)s
        WHERE id = %(id)s
    """
    
    try:
        # Executar a query usando a função existente
        execute_query(query, db_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'message': 'Item updated successfully'}), 200


# NOVAS ROTAS COM VERSÕES INCREMENTADAS E MODIFICAÇÕES

@adm_foods_blueprint.route('/adm/v3/get_all_foods', methods=['GET'])
@jwt_required()
def adm_get_foods_v3():
    try:
        sql_query = """
        SELECT 
            f.id, f.food_name_en, f.food_name_pt, f.food_name_es, f.group_id, f.calories,
            f.portion_size_en, f.portion_size_es, f.portion_size_pt,
            f.carbohydrates, f.proteins, f.alcohol, f.total_fats, f.saturated_fats,
            f.monounsaturated_fats, f.polyunsaturated_fats, f.trans_fats,
            f.fibers, f.calcium, f.sodium, f.magnesium, f.iron, f.zinc,
            f.potassium, f.vitamin_a, f.vitamin_c, f.vitamin_d, f.vitamin_e,
            f.vitamin_b1, f.vitamin_b2, f.vitamin_b3, f.vitamin_b6,
            f.vitamin_b9, f.vitamin_b12, f.caffeine, f.taurine, f.featured,
            f.created_at, f.updated_at,
            f.weight_in_grams, f.image_url,
            GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
            GROUP_CONCAT(DISTINCT a.allergen_name SEPARATOR ', ') AS allergens
        FROM foods f
        LEFT JOIN food_category fc ON f.id = fc.food_id
        LEFT JOIN categories c ON fc.category_id = c.id
        LEFT JOIN food_allergen fa ON f.id = fa.food_id
        LEFT JOIN allergens a ON fa.allergen_id = a.id
        GROUP BY f.id
        """

        result = execute_query_without_params(sql_query, fetch_all=True)
        
        # Processar categorias e alergênicos
        for item in result:
            item['categories'] = item['categories'].split(', ') if item['categories'] else []
            item['allergens'] = item['allergens'].split(', ') if item['allergens'] else []

        # Dicionário para rastrear o menor ID para cada food_name_pt
        first_food_ids = {}
        for item in result:
            food_name_pt = item.get('food_name_pt')
            current_id = item.get('id')
            if food_name_pt:
                if food_name_pt not in first_food_ids:
                    first_food_ids[food_name_pt] = current_id
                else:
                    if current_id < first_food_ids[food_name_pt]:
                        first_food_ids[food_name_pt] = current_id

        # Adicionar o atributo 'is_first' a cada item
        for item in result:
            food_name_pt = item.get('food_name_pt')
            if food_name_pt and item.get('id') == first_food_ids.get(food_name_pt):
                item['is_first'] = True
            else:
                item['is_first'] = False

        return jsonify(result)

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"error": str(e)}), 500

@adm_foods_blueprint.route('/adm/v3/edit_food', methods=['POST'])
@jwt_required()
def adm_edit_food_v3():
    identity = get_jwt_identity()
    updated_data = {}
    try:
        data = request.json

        # Certifica-se de que o ID do alimento está presente
        if 'id' not in data:
            return jsonify({"error": "Missing food ID"}), 400

        # Atualiza a URL da imagem se fornecida, caso contrário, mantém a existente
        if 'image_url' in data:
            if data['image_url'].startswith("http"):
                data['image_url'] = data['image_url']
            else:
                # Se não for uma URL válida, faz o upload da imagem e gera o link
                image_url = upload_image_and_get_url(data['image_url'])
                data['image_url'] = image_url

                # Gera e faz o upload da miniatura
                thumb_url = generate_and_upload_thumbnail(data['image_url'])
                data['thumb_url'] = thumb_url  # Armazena o thumb_url no dicionário de dados

            updated_data['image_url'] = data['image_url']  # Armazena a atualização
            updated_data['thumb_url'] = data.get('thumb_url', '')  # Armazena a miniatura gerada (se houver)

        # Campos que podem ser atualizados
        updatable_fields = [
            'food_name_en', 'food_name_pt', 'food_name_es', 'portion_size_en', 'portion_size_es', 'portion_size_pt', 'group_id', 'image_url', 'thumb_url',
            'weight_in_grams', 'calories', 'carbohydrates', 'proteins', 'alcohol', 'total_fats', 
            'saturated_fats', 'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats', 
            'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc', 'potassium', 
            'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_b1', 'vitamin_b2', 
            'vitamin_b3', 'vitamin_b6', 'vitamin_b9', 'vitamin_b12', 'caffeine', 'featured', 'taurine'
        ]

        set_clause = ', '.join([f"{field} = %s" for field in updatable_fields if field in data])
        params = [data[field] for field in updatable_fields if field in data]
        updated_data.update({field: data[field] for field in updatable_fields if field in data})

        if not params:
            return jsonify({"error": "No updatable fields provided"}), 400

        params.append(data['id'])  # Adiciona o ID do produto ao final dos parâmetros para a cláusula WHERE

        # Consulta SQL para atualizar o produto
        sql_update_food = f"UPDATE foods SET {set_clause} WHERE id = %s"

        # Executa a atualização
        execute_query(sql_update_food, params)

        delete_existing_allergens(data['id'])
        delete_existing_categories(data['id'])

        # Associa apenas com categorias existentes
        if 'categories' in data:
            category_ids = [find_category(category) for category in data['categories'] if find_category(category)]
            if category_ids:  # Só associa se existirem categorias válidas
                update_food_categories(data['id'], category_ids)
            updated_data['categories'] = category_ids

        # Associa apenas com alergênicos existentes
        if 'allergens' in data:
            allergen_ids = [find_allergen(allergen) for allergen in data['allergens'] if find_allergen(allergen)]
            if allergen_ids:  # Só associa se existirem alergênicos válidos
                update_food_allergens(data['id'], allergen_ids)
            updated_data['allergens'] = allergen_ids

        return jsonify({"success": True, "message": "Food updated successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if updated_data:
            # Garante que o ID do alimento esteja incluído nos dados a serem logados
            updated_data['id'] = data.get('id')

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = ", ".join([f"{key}={value}" for key, value in updated_data.items()])
            print(f"{identity} editou um item as [{timestamp}]. Updated fields: {log_message}")

            log_data = {field: updated_data.get(field, None) for field in updatable_fields}
            log_data['id'] = data.get('id')  # Certifica-se de que o 'id' está presente
            log_data['categories'] = ','.join(data.get('categories', [])) if 'categories' in data else None
            log_data['allergens'] = ','.join(data.get('allergens', [])) if 'allergens' in data else None
            log_data['changed_by'] = identity  # Usando a variável identity para identificar quem fez a alteração
            log_data['log_type'] = "EDIT"

            # Construindo a query de inserção atualizada
            sql_insert_log = """
                INSERT INTO food_update_logs (
                    food_id, food_name_en, food_name_pt, food_name_es, portion_size_en, portion_size_es, portion_size_pt, group_id, image_url, thumb_url,
                    weight_in_grams, calories, carbohydrates, proteins, alcohol, total_fats,
                    saturated_fats, monounsaturated_fats, polyunsaturated_fats, trans_fats,
                    fibers, calcium, sodium, magnesium, iron, zinc, potassium,
                    vitamin_a, vitamin_c, vitamin_d, vitamin_e, vitamin_b1, vitamin_b2,
                    vitamin_b3, vitamin_b6, vitamin_b9, vitamin_b12, categories, allergens,
                    changed_by, log_type, caffeine, featured, taurine
                ) VALUES (
                    %(id)s, %(food_name_en)s, %(food_name_pt)s, %(food_name_es)s, %(portion_size_en)s, %(portion_size_es)s, %(portion_size_pt)s, %(group_id)s, %(image_url)s, %(thumb_url)s,
                    %(weight_in_grams)s, %(calories)s, %(carbohydrates)s, %(proteins)s, %(alcohol)s, %(total_fats)s,
                    %(saturated_fats)s, %(monounsaturated_fats)s, %(polyunsaturated_fats)s, %(trans_fats)s,
                    %(fibers)s, %(calcium)s, %(sodium)s, %(magnesium)s, %(iron)s, %(zinc)s, %(potassium)s,
                    %(vitamin_a)s, %(vitamin_c)s, %(vitamin_d)s, %(vitamin_e)s, %(vitamin_b1)s, %(vitamin_b2)s,
                    %(vitamin_b3)s, %(vitamin_b6)s, %(vitamin_b9)s, %(vitamin_b12)s, %(categories)s, %(allergens)s,
                    %(changed_by)s, %(log_type)s, %(caffeine)s, %(featured)s, %(taurine)s
                )
            """

            execute_query(sql_insert_log, log_data)

@adm_foods_blueprint.route('/adm/v5/add_food', methods=['POST'])
@jwt_required()
def adm_add_food_v5():
    identity = get_jwt_identity()
    conn = None
    cursor = None
    expected_params = {}
    food_id = 0
    image_url = ""
    thumb_url = ""
    conn = None
    try:
        data = request.json
        expected_params = [
            'food_name_en', 'food_name_pt', 'food_name_es', 'portion_size_en', 'portion_size_es', 'portion_size_pt', 'group_id', 'image_url', 'weight_in_grams',
            'calories', 'carbohydrates', 'proteins', 'alcohol', 'total_fats', 'saturated_fats', 'monounsaturated_fats',
            'polyunsaturated_fats', 'trans_fats', 'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc',
            'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_b1', 'vitamin_b2',
            'vitamin_b3', 'vitamin_b6', 'vitamin_b9', 'vitamin_b12', 'taurine', 'caffeine', 'featured'
        ]
        missing_params = [param for param in expected_params if param not in data]

        if missing_params:
            print(missing_params)
            return jsonify({
                "error": "Missing parameters",
                "missing_parameters": missing_params
            }), 400
        
        print(data['featured'])

        conn = db_connection_pool.get_connection()  # Substitua pela sua função real de conexão ao banco
        conn.autocommit = False  # Desativa o commit automático
        cursor = conn.cursor()

        # Atualiza a URL da imagem se fornecida, caso contrário, mantém a existente
        if data['image_url'].startswith("http"):
            data['image_url'] = data['image_url']
            image_url = data['image_url']
            thumb_url = data.get('thumb_url', '')  # Use existing thumb_url or set to empty string
        else:
            image_url = upload_image_and_get_url(data['image_url'])
            data['image_url'] = image_url
            thumb_url = generate_and_upload_thumbnail(data['image_url'])

        sql_insert_food = """
        INSERT INTO foods (food_name_en, food_name_pt, food_name_es, portion_size_en, portion_size_es, portion_size_pt, group_id, image_url, weight_in_grams, calories, carbohydrates, proteins, alcohol, total_fats, 
        saturated_fats, monounsaturated_fats, polyunsaturated_fats, trans_fats, fibers, calcium, sodium, magnesium, 
        iron, zinc, potassium, vitamin_a, vitamin_c, vitamin_d, vitamin_e, vitamin_b1, vitamin_b2, vitamin_b3, 
        vitamin_b6, vitamin_b9, vitamin_b12, caffeine, taurine, featured, thumb_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Parâmetros para a inserção do alimento
        params = (
            data['food_name_en'], data['food_name_pt'], data['food_name_es'],
            data['portion_size_en'], data['portion_size_es'], data['portion_size_pt'],
            data['group_id'], image_url, data['weight_in_grams'],
            data['calories'], data['carbohydrates'], data['proteins'], data ['alcohol'],
            data['total_fats'], data['saturated_fats'], data['monounsaturated_fats'], 
            data['polyunsaturated_fats'], data['trans_fats'], data['fibers'], data['calcium'], data['sodium'], 
            data['magnesium'], data['iron'], data['zinc'], data['potassium'], data['vitamin_a'], data['vitamin_c'], 
            data['vitamin_d'], data['vitamin_e'], data['vitamin_b1'], data['vitamin_b2'], data['vitamin_b3'], 
            data['vitamin_b6'], data['vitamin_b9'], data['vitamin_b12'],
            data['taurine'], data['caffeine'], data['featured'], thumb_url
        )
        
        cursor.execute(sql_insert_food, params)
        food_id = cursor.lastrowid

        if 'categories' in data:
            for category in data['categories']:
                category_id = find_category(category)
                if category_id:
                    insert_into_food_category(cursor, food_id, category_id)

        if 'allergens' in data:
            for allergen in data['allergens']:
                allergen_id = find_allergen(allergen)
                if allergen_id:
                    insert_into_food_allergen(cursor, food_id, allergen_id)

        conn.commit()  # Commita a transação se tudo ocorrer bem

        return jsonify({"success": True, "message": "Food added successfully", "food_id": food_id})
    except Exception as e:
        if conn:
            conn.rollback()  # Desfaz todas as operações se ocorrer um err
        if cursor:
            cursor.close()
        print(e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

        if cursor:
            cursor.close()

        # Crie um dicionário para armazenar os parâmetros esperados e adicionar o food_id
        log_data = {}
        log_data['food_id'] = f'{food_id}'

        # Adicione todos os parâmetros que estavam originalmente em expected_params
        for param in [
            'food_name_en', 'food_name_pt', 'food_name_es', 'portion_size_en', 'portion_size_es', 'portion_size_pt',
            'group_id', 'image_url', 'weight_in_grams', 'calories', 'carbohydrates', 'proteins', 'alcohol', 'total_fats',
            'saturated_fats', 'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats', 'fibers', 'calcium', 'sodium',
            'magnesium', 'iron', 'zinc', 'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_b1',
            'vitamin_b2', 'vitamin_b3', 'vitamin_b6', 'vitamin_b9', 'vitamin_b12'
        ]:
            log_data[param] = data.get(param)

        log_data['categories'] = ','.join(data.get('categories', [])) if 'categories' in data else None
        log_data['allergens'] = ','.join(data.get('allergens', [])) if 'allergens' in data else None
        log_data['changed_by'] = identity  # Usando a variável identity para identificar quem fez a alteração
        log_data['log_type'] = "CREATE"  # Definindo o tipo de log como "CREATE"
        log_data['image_url'] = image_url

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = ", ".join([f"{key}={value}" for key, value in log_data.items()])
        print(f"{identity} criou um item as [{timestamp}]. Created fields: {log_message}")

        # Construindo a query de inserção atualizada
        sql_insert_log = """
        INSERT INTO food_update_logs (
            food_id, food_name_en, food_name_pt, food_name_es, portion_size_en, portion_size_es, portion_size_pt,
            group_id, image_url, weight_in_grams, calories, carbohydrates, proteins, alcohol, total_fats,
            saturated_fats, monounsaturated_fats, polyunsaturated_fats, trans_fats, fibers, calcium, sodium,
            magnesium, iron, zinc, potassium, vitamin_a, vitamin_c, vitamin_d, vitamin_e, vitamin_b1,
            vitamin_b2, vitamin_b3, vitamin_b6, vitamin_b9, vitamin_b12, categories, allergens, changed_by, log_type
        ) VALUES (%(food_id)s, %(food_name_en)s, %(food_name_pt)s, %(food_name_es)s, %(portion_size_en)s, %(portion_size_es)s, %(portion_size_pt)s,
                %(group_id)s, %(image_url)s, %(weight_in_grams)s, %(calories)s, %(carbohydrates)s, %(proteins)s, %(alcohol)s, %(total_fats)s,
                %(saturated_fats)s, %(monounsaturated_fats)s, %(polyunsaturated_fats)s, %(trans_fats)s,
                %(fibers)s, %(calcium)s, %(sodium)s, %(magnesium)s, %(iron)s, %(zinc)s, %(potassium)s,
                %(vitamin_a)s, %(vitamin_c)s, %(vitamin_d)s, %(vitamin_e)s, %(vitamin_b1)s, %(vitamin_b2)s,
                %(vitamin_b3)s, %(vitamin_b6)s, %(vitamin_b9)s, %(vitamin_b12)s, %(categories)s, %(allergens)s,
                %(changed_by)s, %(log_type)s)
        """

        execute_query(sql_insert_log, log_data)
