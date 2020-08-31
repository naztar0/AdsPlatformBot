import requests
import hmac
import time
import json
from constants import \
    way_for_pay_url, \
    way_for_pay_secret, \
    way_for_pay_service_url, \
    way_for_pay_merchant_id, \
    way_for_pay_merchant_domain_name


def way_for_pay_request_purchase(user_id, amount):
    date = int(time.time())
    order_reference = f'{date}_{user_id}'
    secret = way_for_pay_secret.encode('utf-8')
    str_signature = f'{way_for_pay_merchant_id};{way_for_pay_merchant_domain_name};{order_reference};{date};{amount};UAH;Пополнение баланса;1;{amount}'.encode('utf-8')
    hash_signature = hmac.new(secret, str_signature, 'MD5').hexdigest()
    res = requests.post(way_for_pay_url, json={
        'transactionType': 'CREATE_INVOICE',
        'merchantAccount': way_for_pay_merchant_id,
        'merchantAuthType': 'SimpleSignature',
        'apiVersion': 1,
        'merchantDomainName': way_for_pay_merchant_domain_name,
        'merchantTransactionSecureType': 'AUTO',
        'merchantSignature': hash_signature,
        'serviceUrl': way_for_pay_service_url,
        'orderReference': order_reference,
        'orderDate': date,
        'amount': amount,
        'currency': 'UAH',
        'productName': ['Пополнение баланса'],
        'productPrice': [amount],
        'productCount': [1],
    })
    response = json.loads(res.text)
    if response['reason'] == 'Ok':
        return response['invoiceUrl']
    else:
        return False, response['reason']
