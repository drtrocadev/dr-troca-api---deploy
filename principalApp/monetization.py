from flask import Blueprint, request, jsonify
from admPanel.functions import execute_query_without_params
from admPanel.functions import execute_query_with_params
from admPanel.auth import db_connection_pool
from flask_jwt_extended import JWTManager, jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
import bcrypt
from principalApp.auth_clients import verify_password_change_timestamp
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

monetization_blueprint = Blueprint('monetization_blueprint', __name__)

@monetization_blueprint.route('/v1/request_redeem', methods=['POST'])
@jwt_required()
def request_withdraw():
    try:
        current_user_email = get_jwt_identity()
        jwt_claims = get_jwt()
        
        valid, error_message = verify_password_change_timestamp(current_user_email, jwt_claims)
        if not valid:
            return jsonify({"statusCode": "401", "message": error_message}), 401
    
        user_id = jwt_claims.get("user_id")
        
        data = request.get_json()
        password = data.get('password')

        query = "SELECT * FROM users WHERE userID = %s"
        user = execute_query_with_params(query, (user_id,))

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            
            amount = data.get('amount')
            if not amount:
                return jsonify({"msg": "Amount is required"}), 400

            current_balance = user['actual_money']
            
            if amount > current_balance:
                return jsonify({"msg": "Insufficient funds"}), 403

            # Start a transaction
            connection = db_connection_pool.get_connection()
            cursor = connection.cursor(dictionary=True)

            try:
                # Subtract the requested amount from actual_money
                new_balance = current_balance - amount
                update_balance_query = """
                UPDATE users
                SET actual_money = %s
                WHERE userID = %s
                """
                cursor.execute(update_balance_query, (new_balance, user_id))

                # Insert the withdraw request
                insert_withdraw_query = """
                INSERT INTO withdraw_requests (userID, amount, status)
                VALUES (%s, %s, 'PENDING')
                """
                cursor.execute(insert_withdraw_query, (user_id, amount))

                # Commit the transaction
                connection.commit()

                return jsonify({"msg": "Withdraw request created successfully", "actual_money": new_balance}), 201

            except Exception as e:
                # Rollback in case of an error
                connection.rollback()
                return jsonify({"msg": str(e)}), 500

            finally:
                # Close the cursor and the connection
                cursor.close()
                connection.close()

        else:
            return jsonify({"msg": "Invalid password"}), 401
    
    except Exception as e:
        return jsonify({"msg": str(e)}), 500
    
@monetization_blueprint.route('/v1/sign_up_with_referral', methods=['POST'])
@jwt_required()
def sign_up_with_referral():
    try:
        current_user_email = get_jwt_identity()
        jwt_claims = get_jwt()
        
        valid, error_message = verify_password_change_timestamp(current_user_email, jwt_claims)
        if not valid:
            return jsonify({"statusCode": "401", "message": error_message}), 401
    
        data = request.get_json()
        referral_code = data.get('referral_code')

        if not referral_code:
            return jsonify({"msg": "Referral code is required"}), 400

        user_id = jwt_claims.get("user_id")

        connection = db_connection_pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # Step 1: Get the userID of the user who owns the referral code
        get_referral_user_query = """
        SELECT userID
        FROM users
        WHERE referral_code = %s
        """
        cursor.execute(get_referral_user_query, (referral_code,))
        referral_user = cursor.fetchone()

        if not referral_user:
            return jsonify({"msg": "Invalid referral code"}), 404

        referral_user_id = referral_user['userID']

        # Step 2: Insert a new transaction
        insert_transaction_query = """
        INSERT INTO transactions (user_id, type, amount, status, transaction_date, secondary_user_id)
        VALUES (%s, 'CREDIT', 0, 1, %s, %s)
        """
        cursor.execute(insert_transaction_query, (referral_user_id, datetime.now(), user_id))

        # Commit the transaction
        connection.commit()
        return jsonify({"msg": "Transaction added successfully"}), 201

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

@monetization_blueprint.route('/v1/get_history', methods=['GET'])
@jwt_required()
def get_history():
    try:
        jwt_claims = get_jwt()
        user_id = jwt_claims.get("user_id")

        def fetch_pending_withdraws():
            pending_withdraws_query = """
            SELECT *
            FROM withdraw_requests
            WHERE userID = %s AND status = 'PENDING'
            """
            return execute_query(pending_withdraws_query, (user_id,))

        def fetch_transactions():
            transactions_query = """
            SELECT *
            FROM transactions
            WHERE user_id = %s
            """
            return execute_query(transactions_query, (user_id,))

        def fetch_user_info():
            user_info_query = """
            SELECT * FROM users WHERE userID = %s
            """
            return execute_query(user_info_query, (user_id,), fetch_all=False)

        with ThreadPoolExecutor() as executor:
            pending_withdraws_future = executor.submit(fetch_pending_withdraws)
            transactions_future = executor.submit(fetch_transactions)
            user_info_future = executor.submit(fetch_user_info)
            
            pending_withdraws = pending_withdraws_future.result()
            transactions = transactions_future.result()
            user_info = user_info_future.result()

        # Calculate actual monthly revenue
        current_month = datetime.now().month
        current_year = datetime.now().year
        actual_monthly_revenue = sum(
            transaction['amount'] for transaction in transactions
            if transaction['type'] == 'CREDIT' and 
               transaction['transaction_date'].month == current_month and
               transaction['transaction_date'].year == current_year
        )

        # Omita a senha ao preparar a resposta
        if user_info and 'password' in user_info:
            del user_info['password']

        # Return the results in a dictionary
        return jsonify({
            "pending_redeem": pending_withdraws,
            "transactions": transactions,
            "actual_monthly_revenue": actual_monthly_revenue,
            "user_info": user_info
        }), 200

    except Exception as e:
        return jsonify({"msg": str(e)}), 500