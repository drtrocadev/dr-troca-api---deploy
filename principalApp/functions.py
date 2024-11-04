import json
import requests


multiplier_lower = 0.75
multiplier_upper = 1.25

def process_foods_flat(result):
    foods = []
    for index, item in enumerate(result):
        try:
            # Transforma food_name e portion_size em dicionários
            food_name = {
                "en": str(item.get('food_name_en', "")),
                "pt": str(item.get('food_name_pt', "")),
                "es": str(item.get('food_name_es', ""))
            }
            portion_size = {
                "en": str(item.get('portion_size_en', "")),
                "es": str(item.get('portion_size_es', "")),
                "pt": str(item.get('portion_size_pt', ""))
            }

            # Garante que 'featured' seja um booleano
            featured = bool(item.get('featured', False))

            # Prepara o item com as informações do alimento, excluindo os campos não necessários para este contexto
            food_item = {key: item[key] for key in item if key not in [
                'group_name_en', 'group_name_pt', 'group_name_es',
                'group_description_en', 'group_description_pt', 'group_description_es',
                'group_image_url', 'food_name_en', 'food_name_pt', 'food_name_es',
                'portion_size_en', 'portion_size_es', 'portion_size_pt'
            ]}

            # Convertendo valores numéricos para string para corresponder ao modelo Swift
            for key in [
                'calories', 'carbohydrates', 'proteins', 'total_fats', 'saturated_fats', 'alcohol',
                'caffeine', 'taurine', 'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats',
                'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc', 'potassium', 'vitamin_a',
                'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_b1', 'vitamin_b2', 'vitamin_b3',
                'vitamin_b6', 'vitamin_b9', 'vitamin_b12', 'weight_in_grams'
            ]:
                # Garante que o valor é uma string, mantendo dois dígitos decimais para consistência
                food_item[key] = f"{float(item.get(key, 0.0)):.2f}"

            # Incluindo food_name e portion_size formatados
            food_item['food_name'] = food_name
            food_item['portion_size'] = portion_size

            # Dividindo allergens e categories em listas, tratando valores ausentes como listas vazias
            food_item['allergens'] = item.get('allergens', "").split('; ') if item.get('allergens') else []
            food_item['categories'] = item.get('categories', "").split('; ') if item.get('categories') else []

            # Garantindo que 'featured' esteja presente como booleano
            food_item['featured'] = featured

            # Garantindo que 'thumb_url' e 'image_url' estejam presentes como strings
            food_item['thumb_url'] = item.get('thumb_url', "")
            food_item['image_url'] = item.get('image_url', "")
            
            # Inclui o campo group_main_nutrient como string
            food_item['group_main_nutrient'] = str(item.get('group_main_nutrient', ""))

            # Inclui data de criação e atualização como strings
            food_item['created_at'] = str(item.get('created_at', ""))
            food_item['updated_at'] = str(item.get('updated_at', ""))

            foods.append(food_item)

        except Exception as e:
            print(f"Error processing item at index {index}: {e}")
            print("Item data:", item)

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

        foods_by_group[group_id]["foods"].append(food_item)

    return foods_by_group

def get_food_by_id(food_id, foods):
    try:
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
    except Exception as e:
        # Imprime a exceção exata que ocorreu
        print(f"Ocorreu um erro: {e}")
        return None


# Lista de todos os nutrientes a serem verificados
nutrients = [
    'carbohydrates', 'proteins', 'total_fats', 'saturated_fats',
    'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats',
    'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc',
    'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e',
    'vitamin_b1', 'vitamin_b2', 'vitamin_b3', 'vitamin_b6',
    'vitamin_b9', 'vitamin_b12', 'caffeine', 'taurine'
]

properties_to_update = [
    'carbohydrates', 'proteins', 'total_fats', 'saturated_fats',
    'monounsaturated_fats', 'polyunsaturated_fats', 'trans_fats',
    'fibers', 'calcium', 'sodium', 'magnesium', 'iron', 'zinc',
    'potassium', 'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e',
    'vitamin_b1', 'vitamin_b2', 'vitamin_b3', 'vitamin_b6',
    'vitamin_b9', 'vitamin_b12', 'calories', 'weight_in_grams',
    'caffeine', 'taurine'
]

def find_daily_similar_foods(all_foods_of_group, actual_food, grams_or_calories, value_to_convert, main_nutrient):
    print("entrou")
    try:
        similar_foods = []
        update_factor = 0.0

        # Tenta calcular o fator de atualização com base em gramas ou calorias
        if grams_or_calories == "grams":
            try:
                weight_in_grams = float(actual_food.get('weight_in_grams', 0) or 0.00)
                update_factor = float(value_to_convert) / weight_in_grams if weight_in_grams != 0 else 1.0
            except (ValueError, TypeError):
                print("Erro ao converter 'weight_in_grams' para float.")
                update_factor = 1.0
            
            for property in properties_to_update:
                try:
                    value = float(str(actual_food.get(property, 0) or 0.00).strip()) * update_factor
                    actual_food[property] = round(value, 2)  # Mantém como float
                    print(f"'{property}' convertido e atualizado para: {actual_food[property]}")
                except (ValueError, TypeError):
                    print(f"Erro ao converter o campo '{property}' em actual_food para float. Valor atual: {actual_food.get(property)}")
                    continue

        else:
            try:
                calories = float(str(actual_food.get('calories', 0) or 0.00).strip())
                update_factor = float(value_to_convert) / calories if calories != 0 else 1.0
            except (ValueError, TypeError):
                print("Erro ao converter 'calories' para float.")
                update_factor = 1.0
            
            for property in properties_to_update:
                try:
                    value = float(str(actual_food.get(property, 0) or 0.00).strip()) * update_factor
                    actual_food[property] = round(value, 2)  # Mantém como float
                    print(f"'{property}' convertido e atualizado para: {actual_food[property]}")
                except (ValueError, TypeError):
                    print(f"Erro ao converter o campo '{property}' em actual_food para float. Valor atual: {actual_food.get(property)}")
                    continue

        # Define os limites de nutrientes
        try:
            maximum_allowed = float(str(actual_food[main_nutrient] or 0.00).strip()) * multiplier_upper
            minimum_allowed = float(str(actual_food[main_nutrient] or 0.00).strip()) * multiplier_lower
            print(f"Limites de '{main_nutrient}': mínimo {minimum_allowed}, máximo {maximum_allowed}")
        except (ValueError, TypeError):
            print(f"Erro ao converter o campo '{main_nutrient}' para float. Valor atual: {actual_food.get(main_nutrient)}")
            maximum_allowed = minimum_allowed = 0

        # Processa os alimentos similares
        for food in all_foods_of_group:
            if food['id'] == actual_food['id']:
                continue

            try:
                food_calories = float(str(food.get('calories', 0) or 0.00).strip())
                local_update_factor = float(actual_food['calories']) / food_calories if food_calories != 0 else 1.0
                update_multiplier = 1 + ((local_update_factor - 1) * 100) / 100
            except (ValueError, TypeError):
                print("Erro ao converter 'calories' de food para float.")
                continue

            for property in properties_to_update:
                try:
                    current_value = str(food.get(property, 0) or 0.00).strip()
                    new_value = float(current_value) * update_multiplier
                    food[property] = round(new_value, 2)
                    print(f"'{property}' em food atualizado para: {food[property]}")
                except (ValueError, TypeError):
                    print(f"Erro ao converter o campo '{property}' em food para float. Valor atual: {food.get(property)}")
                    continue

            # Verifica se o alimento está dentro do limite permitido
            try:
                main_nutrient_value = str(food.get(main_nutrient, 0) or 0.00).strip()
                if minimum_allowed <= float(main_nutrient_value) <= maximum_allowed:
                    similar_foods.append(food)
            except (ValueError, TypeError):
                print(f"Erro ao converter o campo '{main_nutrient}' em food para float. Valor atual: {food.get(main_nutrient)}")
                continue

        return similar_foods
    except Exception as e:
        print("Erro na função find_daily_similar_foods")
        print(e)
        return []

    
def find_hangry_similar_foods(all_foods_of_group, actual_food, grams_or_calories, value_to_convert, main_nutrient):
    try:
        print(float(value_to_convert))
        similar_foods = []
        update_factor = 0.0

        if grams_or_calories == "grams":
            weight_in_grams = float(actual_food.get('weight_in_grams', 0) or 0.00)
            update_factor = float(value_to_convert) / weight_in_grams if weight_in_grams != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food.get(property, 0) or 0.00) * update_factor
                actual_food[property] = round(value, 2)
        elif grams_or_calories == "calories":
            calories = float(actual_food.get('calories', 0) or 0.00)
            update_factor = float(value_to_convert) / calories if calories != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food.get(property, 0) or 0.00) * update_factor
                actual_food[property] = round(value, 2)
        else:
            return []

        maximum_allowed = float(actual_food.get(main_nutrient, 0) or 0.00) * multiplier_upper
        minimum_allowed = float(actual_food.get(main_nutrient, 0) or 0.00) * multiplier_lower

        for food in all_foods_of_group:
            if food['id'] == actual_food['id']:
                continue

            food_calories = float(food.get('calories', 0) or 0.00)
            local_update_factor = float(actual_food['calories']) / food_calories if food_calories != 0 else 1.0
            update_multiplier = 1 + ((local_update_factor - 1) * 100) / 100

            for property in properties_to_update:
                new_value = float(food.get(property, 0) or 0.00) * update_multiplier
                food[property] = round(new_value, 2)

            if minimum_allowed <= float(food.get(main_nutrient, 0) or 0.00) <= maximum_allowed:
                if float(actual_food['weight_in_grams']) > float(food.get("weight_in_grams", 0) or 0.00):
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
            weight_in_grams = float(actual_food.get('weight_in_grams', 0) or 0.00)
            update_factor = float(value_to_convert) / weight_in_grams if weight_in_grams != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food.get(property, 0) or 0.00) * update_factor
                actual_food[property] = round(value, 2)
        else:
            calories = float(actual_food.get('calories', 0) or 0.00)
            update_factor = float(value_to_convert) / calories if calories != 0 else 1.0
            for property in properties_to_update:
                value = float(actual_food.get(property, 0) or 0.00) * update_factor
                actual_food[property] = round(value, 2)

        maximum_allowed = float(actual_food.get(main_nutrient, 0) or 0.00) * multiplier_upper
        minimum_allowed = float(actual_food.get(main_nutrient, 0) or 0.00) * multiplier_lower

        for food in all_foods_of_group:
            if food['id'] == actual_food['id']:
                continue

            food_calories = float(food.get('calories', 0) or 0.00)
            local_update_factor = float(actual_food['calories']) / food_calories if food_calories != 0 else 1.0
            update_multiplier = 1 + ((local_update_factor - 1) * 100) / 100

            for property in properties_to_update:
                new_value = float(food.get(property, 0) or 0.00) * update_multiplier
                food[property] = round(new_value, 2)

            if minimum_allowed <= float(food.get(main_nutrient, 0) or 0.00) <= maximum_allowed:
                if float(actual_food['weight_in_grams']) < float(food.get("weight_in_grams", 0) or 0.00):
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
            continue

        success_count = 0
        actual_food_calories = float(actual_food.get('calories', 0) or 0.00)
        food_calories = float(food.get('calories', 0) or 0.00)

        if grams_or_calories == 'grams':
            actual_food_calories = float(actual_food.get('weight_in_grams', 0) or 0.00)
            food_calories = float(food.get('weight_in_grams', 0) or 0.00)
        elif grams_or_calories == 'calories':
            actual_food_calories = float(actual_food.get('calories', 0) or 0.00)
            food_calories = float(food.get('calories', 0) or 0.00)
        else:
            raise ValueError("Invalid value for grams_or_calories. Must be 'grams' or 'calories'.")

        for nutrient in nutrients:
            actual_food_value = float(actual_food.get(nutrient, 0) or 0.00)
            food_value = float(food.get(nutrient, 0) or 0.00)

            actual_food_nutrient_per_calorie = actual_food_value / actual_food_calories if actual_food_calories else 0.00
            food_nutrient_per_calorie = food_value / food_calories if food_calories else 0.00

            lower_bound = actual_food_nutrient_per_calorie * multiplier_lower
            upper_bound = actual_food_nutrient_per_calorie * multiplier_upper

            if lower_bound <= food_nutrient_per_calorie <= upper_bound:
                success_count += 1

            conversion_factor = (float(value_to_convert) / food_calories) if grams_or_calories == 'calories' else (float(value_to_convert) / float(food.get('weight_in_grams', 0) or 0.00))
            food[nutrient] = round(float(food.get(nutrient, 0) or 0.00) * conversion_factor, 2)

            if grams_or_calories == 'grams':
                food['weight_in_grams'] = round(float(value_to_convert), 2)
                food['calories'] = round(food_calories * conversion_factor, 2)
            elif grams_or_calories == 'calories':
                food['calories'] = round(float(value_to_convert), 2)
                food['weight_in_grams'] = round(float(food.get('weight_in_grams', 0) or 0.00) * conversion_factor, 2)

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