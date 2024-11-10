import json
import requests


multiplier_lower = 0.75
multiplier_upper = 1.25

def process_foods_flat(result):
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

        notes = {
            "en": item['notes_en'] or "",
            "pt": item['notes_pt'] or "",
            "es": item['notes_es'] or ""
        }

        # Garante que 'featured' seja um booleano
        featured = bool(item.get('featured', False))

        # Prepara o item com as informações do alimento, excluindo os campos não necessários para este contexto
        food_item = {key: item[key] for key in item if key not in ['group_name_en', 'group_name_pt', 'group_name_es',
                                                                    'group_description_en', 'group_description_pt', 'group_description_es',
                                                                    'group_image_url', 'food_name_en', 'food_name_pt', 'food_name_es',
                                                                    'portion_size_en', 'portion_size_es', 'portion_size_pt']}
        food_item['food_name'] = food_name
        food_item['portion_size'] = portion_size
        food_item['notes'] = notes
        food_item['allergens'] = item['allergens'].split('; ') if item['allergens'] else []
        food_item['categories'] = item['categories'].split('; ') if item['categories'] else []
        food_item['featured'] = featured  # Adiciona o campo 'featured' como booleano
        food_item['eicosapentaenoic_acid'] = item.get('eicosapentaenoic_acid', "")
        food_item['docosahexaenoic_acid'] = item.get('docosahexaenoic_acid', "")
        food_item['creatine_mg'] = item.get('creatine_mg', "")


        # Garante que os campos 'taurine', 'caffeine' e 'thumb_url' estejam presentes, mesmo se estiverem ausentes
        food_item['taurine'] = item.get('taurine', "")  # Garantindo que 'taurine' exista
        food_item['caffeine'] = item.get('caffeine', "")  # Garantindo que 'caffeine' exista
        food_item['thumb_url'] = item.get('thumb_url', "")  # Garantindo que 'thumb_url' exista

        foods.append(food_item)

    return foods

def process_food_items(result):
    # Inicializa um dicionário para agrupar os alimentos por group_id
    foods_by_group = {}
    for item in result:
        group_id = item['group_id']

        if group_id == 99:
            continue

        if group_id not in foods_by_group:
            foods_by_group[group_id] = {
                "group_id": group_id,
                "group_name": {
                    "en": item['group_name_en'],
                    "pt": item['group_name_pt'],
                    "es": item['group_name_es']
                },
                "group_description": {
                    "en": item['group_description_en'],
                    "pt": item['group_description_pt'],
                    "es": item['group_description_es']
                },
                "notes": {
                    "en": item['notes_en'] or "",
                    "pt": item['notes_pt'] or "",
                    "es": item['notes_es'] or ""
                },
                "group_image_url": item['group_image_url'],
                "foods": []
            }

        # Transforma food_name em um dicionário
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

        # Garante que 'featured' seja um booleano
        featured = bool(item.get('featured', False))

        # Prepara o item com as informações do alimento
        food_item = {key: item[key] for key in item if key not in ['group_name_en', 'group_name_pt', 'group_name_es',
                                                                    'group_description_en', 'group_description_pt', 'group_description_es',
                                                                    'group_image_url', 'food_name_en', 'food_name_pt', 'food_name_es',
                                                                    'portion_size_en', 'portion_size_es', 'portion_size_pt']}
        food_item['food_name'] = food_name
        food_item['portion_size'] = portion_size
        food_item['allergens'] = item['allergens'].split('; ') if item['allergens'] else []
        food_item['categories'] = item['categories'].split('; ') if item['categories'] else []
        food_item['featured'] = featured  # Adiciona o campo 'featured' como booleano
        food_item['taurine'] = item.get('taurine', "")
        food_item['caffeine'] = item.get('caffeine', "")
        food_item['thumb_url'] = item.get('thumb_url', "")
        food_item['eicosapentaenoic_acid'] = item.get('eicosapentaenoic_acid', "")
        food_item['docosahexaenoic_acid'] = item.get('docosahexaenoic_acid', "")
        food_item['creatine_mg'] = item.get('creatine_mg', "")

        foods_by_group[group_id]["foods"].append(food_item)

    return foods_by_group

def get_food_by_id(food_id, foods):
    print(food_id)
    # Percorre todos os alimentos na lista
    for food in foods:
        # Verifica se o id do alimento atual corresponde ao food_id fornecido
        if food['id'] == food_id:
            # Retorna o alimento correspondente
            return food
    # Se nenhum alimento com o id correspondente for encontrado, retorna None
    print("retornou none")
    return None

# Lista de todos os nutrientes a serem verificados
nutrients = [
    'carbohydrates', 'proteins', 'total_fats', 'saturated_fats',
    'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats',
    'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc',
    'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e',
    'vitamin_b1', 'vitamin_b2', 'vitamin_b3', 'vitamin_b6',
    'vitamin_b9', 'vitamin_b12', 'caffeine', 'taurine',
    'eicosapentaenoic_acid', 'docosahexaenoic_acid', 'creatine_mg'
]

properties_to_update = [
    'carbohydrates', 'proteins', 'total_fats', 'saturated_fats',
    'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats',
    'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc',
    'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e',
    'vitamin_b1', 'vitamin_b2', 'vitamin_b3', 'vitamin_b6',
    'vitamin_b9', 'vitamin_b12', 'calories', 'weight_in_grams',
    'caffeine', 'taurine', 'eicosapentaenoic_acid', 'docosahexaenoic_acid', 'creatine_mg'
]

def find_daily_similar_foods(all_foods_of_group, actual_food, grams_or_calories, value_to_convert, main_nutrient):
    try:
        similar_foods = []
        update_factor = 0.0

        if grams_or_calories == "grams":
            weight_in_grams = float(actual_food['weight_in_grams'])
            update_factor = float(value_to_convert) / weight_in_grams if weight_in_grams != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food[property]) * update_factor
                actual_food[property] = f"{round(value, 2)}"
        else:
            calories = float(actual_food['calories'])
            update_factor = float(value_to_convert) / calories if calories != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food[property]) * update_factor
                actual_food[property] = f"{round(value, 2)}"

        maximum_allowed = float(actual_food[main_nutrient]) * multiplier_upper
        minimum_allowed = float(actual_food[main_nutrient]) * multiplier_lower

        for food in all_foods_of_group:
            if food['id'] == actual_food['id']:
                continue  # Skip the actual food itself

            food_calories = float(food['calories'])
            local_update_factor = float(actual_food['calories']) / food_calories if food_calories != 0 else 1.0
            update_multiplier = 1 + ((local_update_factor - 1) * 100) / 100

            for property in properties_to_update:
                new_value = float(food[property]) * update_multiplier
                food[property] = f"{round(new_value, 2)}"

            if minimum_allowed <= float(food[main_nutrient]) <= maximum_allowed:
                similar_foods.append(food)

        return similar_foods
    except Exception as e:
        print("erro na find daily")
        print(e)
        return []
    
def find_hangry_similar_foods(all_foods_of_group, actual_food, grams_or_calories, value_to_convert, main_nutrient):
    try:
        print(float(value_to_convert))
        similar_foods = []
        update_factor = 0.0
        print(f"base {actual_food['weight_in_grams']}")

        if grams_or_calories == "grams":
            weight_in_grams = float(actual_food['weight_in_grams'])
            update_factor = float(value_to_convert) / weight_in_grams if weight_in_grams != 0 else 1.0
            print(f"update_factor {update_factor}")
            for property in properties_to_update:
                value = float(actual_food[property]) * update_factor
                actual_food[property] = f"{round(value, 2)}"
        elif grams_or_calories == "calories":
            calories = float(actual_food['calories'])
            update_factor = float(value_to_convert) / calories if calories != 0 else 1.0
            print(f"update_factor {update_factor}")
            for property in properties_to_update:
                value = float(actual_food[property]) * update_factor
                actual_food[property] = f"{round(value, 2)}"
        else:
            return []

        print(f"main_nutrient {main_nutrient}")
        print(f"actual_food[main_nutrient] {actual_food[main_nutrient]}")
        maximum_allowed = float(actual_food[main_nutrient]) * multiplier_upper
        minimum_allowed = float(actual_food[main_nutrient]) * multiplier_lower

        for food in all_foods_of_group:
            if food['id'] == actual_food['id']:
                continue  # Skip the actual food itself
            print(food['food_name_pt'])

            food_calories = float(food['calories'])
            local_update_factor = float(actual_food['calories']) / food_calories if food_calories != 0 else 1.0
            update_multiplier = 1 + ((local_update_factor - 1) * 100) / 100

            for property in properties_to_update:
                new_value = float(food[property]) * update_multiplier
                food[property] = f"{round(new_value, 2)}"

            if minimum_allowed <= float(food[main_nutrient]) <= maximum_allowed:
                print(f"minimo {minimum_allowed}")
                print("atual")
                print(f"atual {food[main_nutrient]}")
                print(f"maximo {maximum_allowed}")
                if float(actual_food['weight_in_grams']) > float(food["weight_in_grams"]):
                    similar_foods.append(food)

        return similar_foods
    except Exception as e:
        print("erro na find hangry")
        print(e)
        return []
    
def find_not_hangry_similar_foods(all_foods_of_group, actual_food, grams_or_calories, value_to_convert, main_nutrient):
    try:
        similar_foods = []
        update_factor = 0.0

        if grams_or_calories == "grams":
            weight_in_grams = float(actual_food['weight_in_grams'])
            update_factor = float(value_to_convert) / weight_in_grams if weight_in_grams != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food[property]) * update_factor
                actual_food[property] = f"{round(value, 2)}"
        else:
            calories = float(actual_food['calories'])
            update_factor = float(value_to_convert) / calories if calories != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food[property]) * update_factor
                actual_food[property] = f"{round(value, 2)}"

        maximum_allowed = float(actual_food[main_nutrient]) * multiplier_upper
        minimum_allowed = float(actual_food[main_nutrient]) * multiplier_lower

        for food in all_foods_of_group:
            if food['id'] == actual_food['id']:
                continue  # Skip the actual food itself

            food_calories = float(food['calories'])
            local_update_factor = float(actual_food['calories']) / food_calories if food_calories != 0 else 1.0
            update_multiplier = 1 + ((local_update_factor - 1) * 100) / 100

            for property in properties_to_update:
                new_value = float(food[property]) * update_multiplier
                food[property] = f"{round(new_value, 2)}"

            if minimum_allowed <= float(food[main_nutrient]) <= maximum_allowed:
                if float(actual_food['weight_in_grams']) < float(food["weight_in_grams"]):
                    similar_foods.append(food)

        return similar_foods
    except Exception as e:
        print("erro na find not hangry")
        print(e)
        return []

def find_similar_foods(all_foods_of_group, actual_food, grams_or_calories, value_to_convert):
    similar_foods = []

    for food in all_foods_of_group:
        if food['id'] == actual_food['id']:
            continue  # Skip the actual food itself

        success_count = 0  # Contador para rastrear o número de nutrientes bem-sucedidos

        # Valor de calorias do alimento atual
        actual_food_calories = 1.0
        food_calories = 1.0

        if grams_or_calories == 'grams':
            actual_food_calories = float(actual_food['weight_in_grams'])
            food_calories = float(food['weight_in_grams'])
        elif grams_or_calories == 'calories':
            actual_food_calories = float(actual_food['calories'])
            food_calories = float(food['calories'])
        else:
            raise ValueError("Invalid value for grams_or_calories. Must be 'grams' or 'calories'.")

        for nutrient in nutrients:

            # Certifique-se de que o valor do nutriente seja um Decimal
            actual_food_value = float(actual_food[nutrient])
            food_value = float(food[nutrient])

            # Calcular a quantidade de nutrientes por caloria
            actual_food_nutrient_per_calorie = actual_food_value / actual_food_calories
            food_nutrient_per_calorie = food_value / food_calories

            lower_bound = actual_food_nutrient_per_calorie * multiplier_lower 
            upper_bound = actual_food_nutrient_per_calorie * multiplier_upper

            if lower_bound <= food_nutrient_per_calorie <= upper_bound:
                success_count += 1  # Incrementa o contador se o nutriente atender aos critérios
                            
            if grams_or_calories == 'grams':
                conversion_factor = float(value_to_convert) / float(food['weight_in_grams'])
            elif grams_or_calories == 'calories':
                conversion_factor = float(value_to_convert) / float(food['calories'])

            food[nutrient] = f"{float(food[nutrient]) * conversion_factor}"

            if grams_or_calories == 'grams':
                food['weight_in_grams'] = f"{float(value_to_convert)}"
                food['calories'] = f"{float(food['calories']) * conversion_factor}"
            elif grams_or_calories == 'calories':
                food['calories'] = f"{float(value_to_convert)}"
                food['weight_in_grams'] = f"{float(food['weight_in_grams']) * conversion_factor}"


        # Se todos os nutrientes atenderem aos critérios, adicione o alimento à lista de alimentos similares
        if success_count == len(nutrients):
            similar_foods.append(food)

    return similar_foods

def convert_food_values(food, nutrients, grams_or_calories, value_to_convert):
    converted_food = food.copy()
    food_calories = float(food['calories']) if grams_or_calories == 'calories' else float(food['weight_in_grams'])
    conversion_factor = value_to_convert / food_calories

    for nutrient in nutrients:
        converted_food[nutrient] = str(float(food[nutrient]) * conversion_factor)

    if grams_or_calories == 'grams':
        converted_food['weight_in_grams'] = str(value_to_convert)
        converted_food['calories'] = str(float(food['calories']) * conversion_factor)
    elif grams_or_calories == 'calories':
        converted_food['calories'] = str(value_to_convert)
        converted_food['weight_in_grams'] = str(float(food['weight_in_grams']) * conversion_factor)

    return converted_food


def send_email(subject, recipient_email, code):
    try:
        # Configurações da API SendPulse
        API_URL = "https://api.sendpulse.com/smtp/emails"
        API_USER = "77e99f2f600f6939ff6b3c5ad80b9a8d"
        API_PASSWORD = "583c52d97d01c1648a8828c2b8aa3fa5"

        # Autenticação
        auth_response = requests.post(
            "https://api.sendpulse.com/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": API_USER,
                "client_secret": API_PASSWORD
            }
        )
        
        auth_data = auth_response.json()
        access_token = auth_data['access_token']

        # Dados do email
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        email_data = {
            "email": {
                "html": f"<h1>Seu código de recuperação de senha é: {code}</h1>",
                "text": f"Seu código de recuperação de senha é: {code}",
                "subject": "Código de recuperação de senha",
                "from": {
                    "name": "Dr Troca",
                    "email": "desenvolvimento@drtroca.com"
                },
                "to": [
                    {"email": recipient_email}
                ]
            }
        }

        # Envio do email
        response = requests.post(API_URL, headers=headers, data=json.dumps(email_data))

        # Verifica resposta
        if response.status_code == 200:
            print("Email enviado com sucesso!")
        else:
            print(f"Erro ao enviar email: {response.status_code}, {response.text}")

    except Exception as e:
        print(f"Falha ao enviar email: {str(e)}")