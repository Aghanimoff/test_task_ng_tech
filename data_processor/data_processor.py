import json
import pika
import requests
import os
import time

def process_message(ch, method, properties, body):
    message = json.loads(body)
    ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
    ODOO_DB = os.getenv('ODOO_DB', 'odoo')
    ODOO_USER = os.getenv('ODOO_USER', 'odoo')
    ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'odoo')

    try:
        # Аутентификация в Odoo
        login_data = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'db': ODOO_DB,
                'login': ODOO_USER,
                'password': ODOO_PASSWORD,
            }
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(ODOO_URL + '/web/session/authenticate', json=login_data, headers=headers)
        result = response.json()
        if result.get('result'):
            session_id = response.cookies.get('session_id')
            headers['Cookie'] = f'session_id={session_id}'
        else:
            print('Ошибка аутентификации в Odoo')
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        if message['Operation'] == 'upsert':
            # Проверка существования продукта
            search_data = {
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'model': 'product.product',
                    'domain': [['default_code', '=', str(message['ProductID'])]],
                    'fields': ['id'],
                }
            }
            response = requests.post(ODOO_URL + '/web/dataset/search_read', json=search_data, headers=headers)
            result = response.json()

            product_data = {
                'name': message['ProductName'],
                'barcode': message['Barcodes'][0] if message['Barcodes'] else '',
                'default_code': str(message['ProductID']),
            }

            if result.get('result') and result['result']['records']:
                # Обновление продукта
                product_id = result['result']['records'][0]['id']
                update_data = {
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': {
                        'model': 'product.product',
                        'method': 'write',
                        'args': [[product_id], product_data],
                    }
                }
                response = requests.post(ODOO_URL + '/web/dataset/call_kw', json=update_data, headers=headers)
            else:
                # Создание продукта
                create_data = {
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': {
                        'model': 'product.product',
                        'method': 'create',
                        'args': [product_data],
                    }
                }
                response = requests.post(ODOO_URL + '/web/dataset/call_kw', json=create_data, headers=headers)

        elif message['Operation'] == 'delete':
            # Удаление продукта
            search_data = {
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'model': 'product.product',
                    'domain': [['default_code', '=', str(message['ProductID'])]],
                    'fields': ['id'],
                }
            }
            response = requests.post(ODOO_URL + '/web/dataset/search_read', json=search_data, headers=headers)
            result = response.json()
            if result.get('result') and result['result']['records']:
                product_id = result['result']['records'][0]['id']
                unlink_data = {
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': {
                        'model': 'product.product',
                        'method': 'unlink',
                        'args': [[product_id]],
                    }
                }
                response = requests.post(ODOO_URL + '/web/dataset/call_kw', json=unlink_data, headers=headers)

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Ошибка при обработке сообщения: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')

    # Добавляем повторные попытки подключения к RabbitMQ
    max_retries = 5
    retry_delay = 10  # секунд

    for attempt in range(max_retries):
        try:
            connection_params = pika.ConnectionParameters(host=RABBITMQ_HOST)
            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()
            channel.queue_declare(queue='product_updates', durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='product_updates', on_message_callback=process_message)
            print('Ожидание сообщений. Для выхода нажмите CTRL+C')
            channel.start_consuming()
            break
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Попытка подключения к RabbitMQ {attempt + 1} из {max_retries} не удалась: {e}")
            time.sleep(retry_delay)
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            time.sleep(retry_delay)
    else:
        print("Не удалось подключиться к RabbitMQ после нескольких попыток.")

if __name__ == "__main__":
    main()
