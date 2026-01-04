import hashlib
import secrets
import mysql.connector
from mysql.connector import Error


class DatabaseManager:

    def __init__(self, host='localhost', user='root', password='password', db_name='banking_db'):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': db_name
        }

    def __get_connection(self):
        """Creates and returns a new database connection."""
        try:
            connection = mysql.connector.connect(**self.config)
            if connection.is_connected():
                return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None

    def validate_user(self, identity, password):
        """
        Validates user credentials against the DB.
        Returns: True if valid, False if invalid.
        """
        conn = self.__get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor(dictionary=True)
            # Fetch user details including account_number
            query = """
                        SELECT account_number, password, salt, userId FROM users 
                        WHERE userId = %s OR email_id = %s OR account_number = %s
                    """
            cursor.execute(query, (identity, identity, identity))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                stored_hash = user['password']
                stored_salt = user['salt']

                # Check Hash
                combined = password + stored_salt
                calculated_hash = hashlib.sha256(combined.encode()).hexdigest()

                if calculated_hash == stored_hash:
                    return user

            return None  # (Failure)

        except Error as e:
            print(f"Validation Error: {e}")
            return None

    def update_password(self, account_number, new_plain_password):
        conn = self.__get_connection()
        if not conn:
            return False

        try:
            new_salt = secrets.token_urlsafe(8)

            # Hash: SHA256(password + salt)
            combined = new_plain_password + new_salt
            new_hash = hashlib.sha256(combined.encode()).hexdigest()

            # Update Database
            cursor = conn.cursor()
            query = "UPDATE users SET password = %s, salt = %s WHERE account_number = %s"
            cursor.execute(query, (new_hash, new_salt, account_number))
            conn.commit()
            is_updated = cursor.rowcount > 0
            cursor.close()
            conn.close()

            return is_updated  # Returns True if a row was updated

        except Error as e:
            print(f"Update Password Error: {e}")
            return False

    def get_account_details(self, account_number):
        conn = self.__get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    u.userId, u.email_id,
                    a.account_number, a.ifsc_code, a.upi_id, 
                    a.bank_branch, a.account_holder_name, a.account_balance
                FROM users u
                JOIN account_details a ON u.account_number = a.account_number
                WHERE u.account_number = %s
            """
            cursor.execute(query, (account_number,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()
            return result

        except Error as e:
            print(f"Fetch Account Info Error: {e}")
            return None

    def lookup_beneficiary(self, look_for, value):
        """
        Look up beneficiary details.
        look_for: 'ACCOUNT' or 'UPI'
        value: The account number or UPI ID
        """
        conn = self.__get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor(dictionary=True)

            if look_for == 'ACCOUNT':
                query = "SELECT account_number, bank_branch, account_holder_name FROM account_details WHERE account_number = %s"
            else:
                query = "SELECT account_number, bank_branch, account_holder_name FROM account_details WHERE upi_id = %s"

            cursor.execute(query, (value,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()
            return result
        except Error as e:
            print(f"Lookup Error: {e}")
            return None

    def perform_transfer(self, sender_acc, receiver_acc, amount, mode, note):
        """
        ATOMIC TRANSACTION: Deduct, Add, and Log Transaction.
        """
        conn = self.__get_connection()
        if not conn: return False

        try:
            conn.start_transaction()
            cursor = conn.cursor()

            # 1. Fetch Sender Details (Locking row for update is best practice, but simple select for now)
            cursor.execute("SELECT account_balance, account_holder_name FROM account_details WHERE account_number = %s",
                           (sender_acc,))
            sender_data = cursor.fetchone()

            # 2. Fetch Receiver Details
            cursor.execute("SELECT account_holder_name FROM account_details WHERE account_number = %s", (receiver_acc,))
            receiver_data = cursor.fetchone()

            # Validation
            if not sender_data or not receiver_data:
                conn.rollback()
                return False

            sender_balance = sender_data[0]
            sender_name = sender_data[1]
            receiver_name = receiver_data[0]

            if sender_balance < amount:
                conn.rollback()
                return False  # Insufficient funds

            # 3. Deduct from Sender
            cursor.execute(
                "UPDATE account_details SET account_balance = account_balance - %s WHERE account_number = %s",
                (amount, sender_acc))

            # 4. Add to Receiver
            cursor.execute(
                "UPDATE account_details SET account_balance = account_balance + %s WHERE account_number = %s",
                (amount, receiver_acc))

            # 5. LOG TRANSACTION
            # Generate ID and Time
            trans_id = secrets.token_hex(8).upper()  # Generates 16 char random ID
            # Python datetime for insertion
            from datetime import datetime
            now = datetime.now()

            log_query = """
                INSERT INTO transaction_history 
                (transaction_id, transaction_date, sender_name, receiver_name, sender_account_number, receiver_account_number, mode, amount, note, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'SUCCESS')
            """
            cursor.execute(log_query,
                           (trans_id, now, sender_name, receiver_name, sender_acc, receiver_acc, mode, amount, note))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Error as e:
            print(f"Transfer Error: {e}")
            conn.rollback()
            return False

    def get_transaction_history(self, account_number):
        conn = self.__get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(dictionary=True)
            # Fetch transactions where user is sender OR receiver, sorted by latest first
            query = """
                SELECT * FROM transaction_history
                WHERE sender_account_number = %s OR receiver_account_number = %s
                ORDER BY transaction_date DESC
            """
            cursor.execute(query, (account_number, account_number))
            result = cursor.fetchall()

            cursor.close()
            conn.close()
            return result
        except Error as e:
            print(f"History Error: {e}")
            return []
