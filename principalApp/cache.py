from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params
from principalApp.functions import process_food_items

cache_foods = []

def update_cache():
    global cache_foods
    print("update")
    # Consulta SQL para buscar todos os alimentos com categorias, alergias e grupos
    sql_query = """
    SELECT 
        f.id, f.food_name_en, f.food_name_pt, f.food_name_es, f.portion_size_en, f.portion_size_es, f.portion_size_pt, f.group_id,
        g.name_en AS group_name_en, g.name_pt AS group_name_pt, g.name_es AS group_name_es,
        g.description_en AS group_description_en, g.description_pt AS group_description_pt, g.description_es AS group_description_es,
        g.image_url AS group_image_url,
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

    # Executa a consulta
    result = execute_query_without_params(sql_query, fetch_all=True)
    cache_foods = result