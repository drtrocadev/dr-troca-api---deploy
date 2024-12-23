from admPanel.auth import db_connection_pool
import base64
import re
from ftplib import FTP
import io
from PIL import Image
from datetime import datetime
import random
import string

def execute_query_without_params(sql_query, fetch_all=False, should_commit=True):
    connection = None
    cursor = None
    try:
        # Connection to the database
        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # Execute the SQL query
        cursor.execute(sql_query)

        # Fetch the results
        if fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()

        # Commit the transaction to apply the update to the database if necessary
        if should_commit:
            connection.commit()

        return result

    except Exception as e:
        # In case of an error, rollback the transaction to avoid incomplete updates
        if connection:
            connection.rollback()
        raise e

    finally:
        # Close the cursor and the connection to the database
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def execute_query_with_params(sql_query, params, fetch_all=False, should_commit=True, return_lastrowid=False):
    connection = None
    cursor = None
    try:
        # Conexão com o banco de dados
        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # Executa a query SQL com os parâmetros fornecidos
        cursor.execute(sql_query, params)

        # Fetch the results
        if fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()

        # Commit the transaction if necessary
        if should_commit:
            connection.commit()

        # Retorna o lastrowid se solicitado
        if return_lastrowid:
            return cursor.lastrowid

        return result

    except Exception as e:
        # Em caso de erro, faz rollback na transação
        if connection:
            connection.rollback()
        raise e

    finally:
        # Fecha o cursor e a conexão com o banco de dados
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def execute_insert_query_with_params(sql_query, params):
    connection = None
    cursor = None
    try:
        # Connection to the database
        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # Execute the SQL query with the provided parameters
        cursor.execute(sql_query, params)
        
        # Commit the transaction to apply the update to the database
        connection.commit()

        # Get the last inserted ID
        lastrowid = cursor.lastrowid

        return lastrowid

    except Exception as e:
        # In case of an error, rollback the transaction to avoid incomplete updates
        if connection:
            connection.rollback()
        raise e

    finally:
        # Close the cursor and the connection to the database
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

def execute_query(sql, params, many=False):
    conn = None
    cursor = None
    last_ids = None
    try:
        conn = db_connection_pool.get_connection()  # Substitua pela sua função real de conexão ao banco
        cursor = conn.cursor()

        if many:
            cursor.executemany(sql, params)
            last_ids = cursor.lastrowid  # Isso pode não funcionar conforme esperado para 'executemany' em alguns DBs
        else:
            cursor.execute(sql, params)
            last_ids = cursor.lastrowid

        conn.commit()

    except Exception as e:
        conn.rollback()  # É importante fazer rollback se houver um erro
        print(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return last_ids

# Configurações de FTP
ftp_host = '89.116.115.91'
ftp_username = 'u994546528.painelAdm'
ftp_password = '1hdej#@Jasu'
ftp_port = 21
ftp_folder = 'domains/drtroca.com.br/public_html/drtroca/foods/'
ftp_categories_folder = 'domains/drtroca.com.br/public_html/drtroca/categories/'
ftp_folder_recipes = 'domains/drtroca.com.br/public_html/drtroca/recipes/'
ftp_folder_invoices = 'domains/drtroca.com.br/public_html/drtroca/invoices/'

def generate_filename():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_letters = ''.join(random.choices(string.ascii_letters, k=4))
    return f"{timestamp}_{random_letters}"

def upload_image_and_get_url(image_base64):
    if not image_base64:
        raise ValueError("Image base64 data not found")

    # Remove espaços em branco e quebras de linha da string base64
    image_base64 = re.sub(r'\s+', '', image_base64)

    # Verifica se o comprimento da string é um múltiplo de 4 e adiciona o padding "=", se necessário
    padding_needed = len(image_base64) % 4
    if padding_needed > 0:
        image_base64 += '=' * (4 - padding_needed)

    # Decodifica a string base64 corrigida para obter os dados binários da imagem
    image_data = base64.b64decode(image_base64)

    # Converte os dados binários para um objeto de imagem
    image = Image.open(io.BytesIO(image_data))

    # Prepara o stream para salvar a imagem convertida em PNG
    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_stream.seek(0)  # Volta ao início do stream para o upload

    filename = generate_filename()
    filename_with_suffix = filename + ".png"

    # Fazendo o upload para o servidor FTP
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.cwd(ftp_folder)
    ftp.storbinary('STOR ' + filename_with_suffix, image_stream)
    ftp.quit()

    # Retorna a URL da imagem após o upload bem-sucedido
    return f"https://www.drtroca.com.br/domains/drtroca.com.br/public_html/drtroca/foods/{filename_with_suffix}"

def upload_category_cover_and_get_url(image_base64):
    if not image_base64:
        raise ValueError("Image base64 data not found")

    # Remove espaços em branco e quebras de linha da string base64
    image_base64 = re.sub(r'\s+', '', image_base64)

    # Verifica se o comprimento da string é um múltiplo de 4 e adiciona o padding "=", se necessário
    padding_needed = len(image_base64) % 4
    if padding_needed > 0:
        image_base64 += '=' * (4 - padding_needed)

    # Decodifica a string base64 corrigida para obter os dados binários da imagem
    image_data = base64.b64decode(image_base64)

    # Converte os dados binários para um objeto de imagem
    image = Image.open(io.BytesIO(image_data))

    # Prepara o stream para salvar a imagem convertida em PNG
    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_stream.seek(0)  # Volta ao início do stream para o upload

    filename = generate_filename()
    filename_with_suffix = filename + ".png"

    # Fazendo o upload para o servidor FTP
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.cwd(ftp_categories_folder)
    ftp.storbinary('STOR ' + filename_with_suffix, image_stream)
    ftp.quit()

    # Retorna a URL da imagem após o upload bem-sucedido
    return f"https://www.drtroca.com.br/domains/drtroca.com.br/public_html/drtroca/categories/{filename_with_suffix}"
   
def upload_recipe(image_base64, filename):
    if not image_base64:
        raise ValueError("Image base64 data not found")
    if not filename:
        raise ValueError("fileName not found")

    # Remove espaços em branco e quebras de linha da string base64
    image_base64 = re.sub(r'\s+', '', image_base64)

    # Verifica se o comprimento da string é um múltiplo de 4 e adiciona o padding "=", se necessário
    padding_needed = len(image_base64) % 4
    if padding_needed > 0:
        image_base64 += '=' * (4 - padding_needed)

    # Decodifica a string base64 corrigida para obter os dados binários da imagem
    image_data = base64.b64decode(image_base64)

    # Converte os dados binários para um objeto de imagem
    image = Image.open(io.BytesIO(image_data))

    # Prepara o stream para salvar a imagem convertida em PNG
    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_stream.seek(0)  # Volta ao início do stream para o upload

    filename_with_suffix = filename + ".png"

    # Fazendo o upload para o servidor FTP
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.cwd(ftp_folder_recipes)
    ftp.storbinary('STOR ' + filename_with_suffix, image_stream)
    ftp.quit()

    # Retorna a URL da imagem após o upload bem-sucedido
    return f"https://www.drtroca.com.br/domains/drtroca.com.br/public_html/drtroca/recipes/{filename_with_suffix}"

def upload_invoice(invoice_base64, filename):
    if not invoice_base64:
        raise ValueError("Image base64 data not found")
    if not filename:
        raise ValueError("fileName not found")

    # Remove espaços em branco e quebras de linha da string base64
    invoice_base64 = re.sub(r'\s+', '', invoice_base64)

    # Verifica se o comprimento da string é um múltiplo de 4 e adiciona o padding "=", se necessário
    padding_needed = len(invoice_base64) % 4
    if padding_needed > 0:
        invoice_base64 += '=' * (4 - padding_needed)

    # Decodifica a string base64 corrigida para obter os dados binários da imagem
    image_data = base64.b64decode(invoice_base64)

    # Converte os dados binários para um objeto de imagem
    image = Image.open(io.BytesIO(image_data))

    # Prepara o stream para salvar a imagem convertida em PNG
    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_stream.seek(0)  # Volta ao início do stream para o upload

    filename_with_suffix = filename + ".png"

    # Fazendo o upload para o servidor FTP
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.cwd(ftp_folder_invoices)
    ftp.storbinary('STOR ' + filename_with_suffix, image_stream)
    ftp.quit()

    # Retorna a URL da imagem após o upload bem-sucedido
    return f"https://www.drtroca.com.br/domains/drtroca.com.br/public_html/drtroca/invoices/{filename_with_suffix}"


ftp_folder_thumbs = 'domains/drtroca.com.br/public_html/drtroca/thumbs/'

def generate_and_upload_thumbnail(image_input):
    """
    Generates a thumbnail from the given image input (base64 string or URL),
    uploads it to the FTP server, and returns the thumbnail URL.
    """
    try:
        if image_input.startswith("http"):
            # If the image_input is a URL, download the image first
            import requests
            response = requests.get(image_input)
            response.raise_for_status()
            image_data = response.content
        else:
            # If the image_input is a base64 string, decode it
            image_base64 = re.sub(r'\s+', '', image_input)
            padding_needed = len(image_base64) % 4
            if padding_needed > 0:
                image_base64 += '=' * (4 - padding_needed)
            image_data = base64.b64decode(image_base64)

        # Open the image using PIL
        image = Image.open(io.BytesIO(image_data))

        # Create a thumbnail (e.g., 128x128 pixels)
        thumbnail_size = (128, 128)
        image.thumbnail(thumbnail_size)

        # Save the thumbnail to a bytes buffer in PNG format
        thumbnail_stream = io.BytesIO()
        image.save(thumbnail_stream, format='PNG')
        thumbnail_stream.seek(0)

        # Generate a unique filename for the thumbnail
        thumbnail_filename = generate_filename() + "_thumb.png"

        # Upload the thumbnail to FTP server
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_username, passwd=ftp_password)
        ftp.cwd(ftp_folder_thumbs)
        ftp.storbinary('STOR ' + thumbnail_filename, thumbnail_stream)
        ftp.quit()

        # Return the URL of the uploaded thumbnail
        return f"https://www.drtroca.com.br/domains/drtroca.com.br/public_html/drtroca/thumbs/{thumbnail_filename}"

    except Exception as e:
        # Handle exceptions (you might want to log this instead)
        print(f"Error generating/uploading thumbnail: {e}")
        raise e