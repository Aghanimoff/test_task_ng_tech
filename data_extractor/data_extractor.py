import pyodbc
import time
import pika
import json
import os

def get_cdc_changes(connection, last_lsn):
    cursor = connection.cursor()
    # Получение максимального LSN
    cursor.execute("SELECT sys.fn_cdc_get_max_lsn()")
    max_lsn = cursor.fetchone()[0]

    if last_lsn is None:
        last_lsn = max_lsn

    # Получение изменений в таблице Products
    cursor.execute("""
        SELECT * FROM cdc.fn_cdc_get_all_changes_dbo_Products(?, ?, N'all')
    """, last_lsn, max_lsn)
    products_changes = cursor.fetchall()

    # Получение изменений в таблице ProductBarcodes
    cursor.execute("""
        SELECT * FROM cdc.fn_cdc_get_all_changes_logistics_ProductBarcodes(?, ?, N'all')
    """, last_lsn, max_lsn)
    barcodes_changes = cursor.fetchall()

    return products_changes, barcodes_changes, max_lsn

def send_to_queue(message):
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    connection_params = pika.ConnectionParameters(host=RABBITMQ_HOST)
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    channel.queue_declare(queue='product_updates', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='product_updates',
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()

def main():
    # Получение параметров подключения из переменных окружения
    MSSQL_HOST = os.getenv('MSSQL_HOST', 'localhost')
    MSSQL_USER = os.getenv('MSSQL_USER', 'SA')
    MSSQL_PASSWORD = os.getenv('MSSQL_PASSWORD', 'Admin@123')
    MSSQL_DATABASE = os.getenv('MSSQL_DATABASE', 'TestDB')

    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={MSSQL_HOST};DATABASE={MSSQL_DATABASE};UID={MSSQL_USER};PWD={MSSQL_PASSWORD};'

    max_retries = 5
    retry_delay = 10  # секунд

    for attempt in range(max_retries):
        try:
            connection = pyodbc.connect(conn_str)
            print("Подключение к SQL Server успешно установлено.")
            break
        except pyodbc.OperationalError as e:
            print(f"Попытка подключения {attempt + 1} из {max_retries} не удалась: {e}")
            time.sleep(retry_delay)
    else:
        print("Не удалось подключиться к SQL Server после нескольких попыток.")
        return

    # Инициализация последнего LSN
    last_lsn = None
    while True:
        try:
            products_changes, barcodes_changes, last_lsn = get_cdc_changes(connection, last_lsn)
            print(f"Получено {len(products_changes)} изменений в таблице Products.")
            print(f"Получено {len(barcodes_changes)} изменений в таблице ProductBarcodes.")
            # ... остальной код ...
            time.sleep(10)  # Пауза между проверками

            for change in products_changes:
                # Обработка изменений в таблице Products
                operation = change.__getattribute__('__$operation')
                if operation in (2, 4):  # Insert or Update
                    product_id = change.ProductID
                    product_name = change.ProductName

                    # Получаем связанные штрихкоды
                    cursor = connection.cursor()
                    cursor.execute("""
                        SELECT Barcode FROM logistics.ProductBarcodes WHERE ProductID = ?
                    """, product_id)
                    barcodes = [row.Barcode for row in cursor.fetchall()]

                    message = {
                        'ProductID': product_id,
                        'ProductName': product_name,
                        'Barcodes': barcodes,
                        'Operation': 'upsert'
                    }
                    send_to_queue(message)

                elif operation == 1:  # Delete
                    product_id = change.ProductID
                    message = {
                        'ProductID': product_id,
                        'Operation': 'delete'
                    }
                    send_to_queue(message)

        except Exception as e:
            print(f"Ошибка при обработке данных: {e}")

        time.sleep(10)

if __name__ == "__main__":
    main()
