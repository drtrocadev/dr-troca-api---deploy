from flask import Blueprint, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt, get_jwt_identity
from admPanel.auth import db_connection_pool
from admPanel.functions import upload_recipe
from admPanel.functions import upload_invoice
from datetime import datetime
from admPanel.functions import execute_query_without_params

adm_monetization_blueprint = Blueprint('adm_monetization_blueprint', __name__)

@adm_monetization_blueprint.route('/adm/v1/approve_redeem', methods=['POST'])
def approve_withdraw():
    connection = None
    cursor = None
    try:
        data = request.get_json()
        withdraw_request_id = data.get('withdraw_request_id')
        recipe_base64 = data.get('recipe_base64')
        invoice_base64 = data.get('invoice_base64')

        if not withdraw_request_id:
            return jsonify({"msg": "Withdraw request ID is required"}), 400
        
        if not recipe_base64 and not invoice_base64:
            return jsonify({"msg": "At least one of recipe or invoice base64 is required"}), 400

        # Define empty strings if one of the fields is missing
        if not recipe_base64:
            recipe_base64 = ""
        if not invoice_base64:
            invoice_base64 = ""

        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # First, update the withdraw request status
        update_query = """
        UPDATE withdraw_requests
        SET status = 'APPROVED'
        WHERE id = %s
        """
        cursor.execute(update_query, (withdraw_request_id,))

        # Then, fetch the userID and amount
        select_query = """
        SELECT userID, amount
        FROM withdraw_requests
        WHERE id = %s
        """
        cursor.execute(select_query, (withdraw_request_id,))
        withdraw_details = cursor.fetchone()

        if not withdraw_details:
            connection.rollback()
            return jsonify({"msg": "Withdraw request not found"}), 404

        user_id = withdraw_details['userID']
        amount = withdraw_details['amount']

        # Generate a unique filename
        current_time = datetime.now().strftime("%Y%m%d%H%M")
        recipe_filename = f"{user_id}_{withdraw_request_id}_{current_time}_recipe.png" if recipe_base64 else ""
        invoice_filename = f"{user_id}_{withdraw_request_id}_{current_time}_invoice.png" if invoice_base64 else ""

        # Step 3: Upload the recipe image and get the URL
        recipe_url = ""
        if recipe_base64 != "":
            recipe_url = upload_recipe(recipe_base64, recipe_filename)

        # Step 4: Upload the invoice image and get the URL
        invoice_url = ""
        if invoice_base64 != "":
            invoice_url = upload_invoice(invoice_base64, invoice_filename)

        # Step 5: Insert a new transaction of type "DEBIT"
        insert_transaction_query = """
        INSERT INTO transactions (user_id, type, amount, status, transaction_date, recipe_url, invoice_url)
        VALUES (%s, 'DEBIT', %s, 1, %s, %s, %s)
        """
        cursor.execute(insert_transaction_query, (user_id, amount, datetime.now(), recipe_url, invoice_url))

        # Commit the transaction
        connection.commit()
        return jsonify({"msg": "Withdraw request approved and transaction created successfully"}), 201

    except Exception as e:
        # In case of an error, rollback the transaction
        if connection:
            connection.rollback()
        return jsonify({"msg": str(e)}), 500

    finally:
        # Close the cursor and the connection to the database
        if cursor:
            cursor.close()
        if connection:
            connection.close()





def execute_query(query, params, fetch_all=True):
    connection = db_connection_pool.get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, params)
    result = cursor.fetchall() if fetch_all else cursor.fetchone()
    cursor.close()
    connection.close()
    return result

@adm_monetization_blueprint.route('/adm/v1/withdraw_requests', methods=['GET'])
def fetch_all_withdraw_requests():
    withdraws_query = """
    SELECT 
        w.id AS withdraw_id,
        w.amount,
        w.status,
        w.created_at,
        u.userID,
        u.name,
        u.email,
        u.cpf,
        u.paypall_email,
        u.phone,
        u.is_subscriber,
        u.created_at AS user_created_at
    FROM 
        withdraw_requests w
    JOIN 
        users u ON w.userID = u.userID

    """

    withdraws = execute_query_without_params(withdraws_query, fetch_all=True)

    # Transform the flat structure into the desired nested structure
    for withdraw in withdraws:
        withdraw['user'] = {
            'userID': withdraw.pop('userID'),
            'name': withdraw.pop('name'),
            'email': withdraw.pop('email'),
            'cpf': withdraw.pop('cpf'),
            'paypall_email': withdraw.pop('paypall_email'),
            'phone': withdraw.pop('phone'),
            'is_subscriber': withdraw.pop('is_subscriber'),
            'created_at': withdraw.pop('user_created_at')  # Trazendo de volta o created_at do usuário
        }

    pending_redeems = [withdraw for withdraw in withdraws if withdraw['status'] == 'PENDING']
    approved_redeems = [withdraw for withdraw in withdraws if withdraw['status'] == 'APPROVED']

    return jsonify({
        'pending_redeems': pending_redeems,
        'approved_redeems': approved_redeems
    })
