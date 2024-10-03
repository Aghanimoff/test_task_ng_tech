import pyodbc
import time
import pika
import json
from datetime import datetime, timedelta

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
    connection_params = pika.ConnectionParameters('localhost')
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    channel.queue_declare(queue='product_updates')
    channel.basic_publish(exchange='', routing_key='product_updates', body=json.dumps(message))
    connection.close()

def main():
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=TestDB;Trusted_Connection=yes;'
    connection = pyodbc.connect(conn_str)
    last_lsn = None  # Инициализация последнего LSN

    while True:
        products_changes, barcodes_changes, last_lsn = get_cdc_changes(connection, last_lsn)

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

        # Аналогично обрабатываем изменения в таблице ProductBarcodes

        time.sleep(10)  # Пауза между проверками

if __name__ == "__main__":
    main()
