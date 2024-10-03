import json
import pika
import requests

def process_message(ch, method, properties, body):
    message = json.loads(body)
    odoo_url = 'http://localhost:8069'
    db = 'odoo_test'
    username = 'admin'
    password = 'admin'

    # Аутентификация в Odoo
    login_data = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'db': db,
            'login': username,
            'password': password,
        }
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(odoo_url + '/web/session/authenticate', json=login_data, headers=headers)
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
        response = requests.post(odoo_url + '/web/dataset/search_read', json=search_data, headers=headers)
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
            response = requests.post(odoo_url + '/web/dataset/call_kw', json=update_data, headers=headers)
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
            response = requests.post(odoo_url + '/web/dataset/call_kw', json=create_data, headers=headers)

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
        response = requests.post(odoo_url + '/web/dataset/search_read', json=search_data, headers=headers)
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
            response = requests.post(odoo_url + '/web/dataset/call_kw', json=unlink_data, headers=headers)

    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection_params = pika.ConnectionParameters('localhost')
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    channel.queue_declare(queue='product_updates')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='product_updates', on_message_callback=process_message)
    print('Ожидание сообщений. Для выхода нажмите CTRL+C')
    channel.start_consuming()

if __name__ == "__main__":
    main()
