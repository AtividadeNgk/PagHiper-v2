import math, requests
import uuid, json

config = json.loads(open('./config.json', 'r').read())

#PAYMENT STATUS
#
# Idle     - pagamento gerado porem sem qrcode
# Waiting  - qrcode gerado aguardando pagamento
# Paid     - pagamento aprovado porem não processado 
# Finished - pagamento finalizado


def verificar_push(token):
    url = "https://api.pushinpay.com.br/api/pix/cashIn"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "value": 100,
        "webhook_url": f'',  # Altere para seu webhook real
        "split_rules": [
            {
                "value": math.floor(100*0.05),
                "account_id": "9D60FF2D-4298-4AEF-89AB-F27AE6A9D68D"
                }
            ]
        }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code in (200, 201):
            payment_info = response.json()
            pix_code = payment_info.get('qr_code', '')
            payment_id = payment_info.get('id', '')
            return True
        else: False
    except requests.exceptions.RequestException as e:
        print(f"Erro ao processar requisição para o PIX: {e}")
        return False, e

def criar_pix_pp(token, valor_cents):
    # Endpoint da API
    url = "https://api.pushinpay.com.br/api/pix/cashIn"

    valor_cents = float(valor_cents)
    comissao = math.floor(valor_cents * config['tax'])

    valor_cents = valor_cents * 100

    
    #comissao = 1 #Centavos
    print(f"""
    GERANDO PIX PUSHINPAY 
    TOTAL:{valor_cents}
    COMISSAO:{comissao}
    VALOR ENTREGUE:{valor_cents}
    """)
    # Cabeçalhos da requisição
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Corpo da requisição
    data = {
        "value": valor_cents,
        "webhook_url": f"{config['url']}/webhook/pp",  # Substitua por um domínio válido
        "split_rules": [
            {
                "value": comissao,  # 5% do valor total
                "account_id": "9D60FF2D-4298-4AEF-89AB-F27AE6A9D68D"  # Substitua pelo ID da conta correta
            }
        ]
    }

    try:
        # Realiza a requisição POST
        response = requests.post(url, json=data, headers=headers)
        # Verifica se a requisição foi bem-sucedida
        if response.status_code in (200, 201):
            try:
                payment_info = response.json()  # Parse da resposta JSON
                return {
                    "pix_code": payment_info.get("qr_code", False),
                    "payment_id": payment_info.get("id", False),
                    "message": "Pagamento PIX gerado com sucesso."
                }
            except ValueError:
                return {"error": "A resposta da API não está no formato esperado.", "details": response.text}
        else:
            return {
                "error": f"Erro ao criar pagamento. Status Code: {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        return {"error": "Erro ao realizar a requisição para a API.", "details": str(e)}


def criar_pix_mp(access_token: str, transaction_amount: float) -> dict:
    url = "https://api.mercadopago.com/v1/payments"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())  # Gera uma chave única para cada requisição
    }
    transaction_amount = round(float(transaction_amount), 2)
    application_fee = round((transaction_amount * config['tax'] / 100), 2)
    # Dados do pagamento
    payment_data = {
        "transaction_amount": transaction_amount,
        "description": "Pagamento via PIX - Marketplace",
        "payment_method_id": "pix",  # Método de pagamento PIX
        "payer": {
            "email": 'ngkacesspay@empresa.com'
        },
        "application_fee": application_fee,  # Taxa de 5% para o marketplace
        "statement_descriptor": "Marketplace"
    }
    print(application_fee)
    print(type(application_fee))
    print(transaction_amount)
    try:
        # Fazendo a requisição para criar o pagamento
        # Fazendo a requisição para criar o pagamento
        response = requests.post(url, headers=headers, json=payment_data)
        if response.status_code == 201:  # Verifica se a requisição foi bem-sucedida
            data = response.json()
            print(data)
            pix_code = data.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code", "")
            payment_id = data.get("id", "")
            return {
                'pix_code': pix_code,
                'payment_id': str(payment_id),
            }  # Retorna os dados do pagamento gerado
        else:
            return {"error": f"Erro ao criar pagamento: {response.status_code}", "details": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Erro ao processar requisição para o PIX: {e}")
        return {"error": "Erro ao processar requisição PIX", "details": str(e)}
    
def verificar_paghiper(api_key):
    """
    Verifica se a API Key do PagHiper é válida
    """
    url = "https://pix.paghiper.com/invoice/create/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Dados mínimos para teste
    data = {
        "apiKey": api_key,
        "order_id": "TEST_" + str(uuid.uuid4())[:8],
        "payer_email": "teste@teste.com",
        "payer_name": "Teste Validacao",
        "payer_cpf_cnpj": "00000000191",
        "days_due_date": 1,
        "items": [{
            "description": "Teste de API",
            "quantity": 1,
            "item_id": "1",
            "price_cents": 300  # R$ 3,00 (mínimo)
        }]
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            # Sucesso - API Key válida
            return True
        else:
            print(f"Erro PagHiper: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Erro ao verificar PagHiper: {e}")
        return False

def criar_pix_paghiper(api_key, valor):
    """
    Cria um PIX no PagHiper
    """
    url = "https://pix.paghiper.com/invoice/create/"
    
    # Converte valor para centavos
    valor_cents = int(float(valor) * 100)
    
    # Calcula a comissão (5%)
    comissao_cents = int(valor_cents * config['tax'] / 100)
    
    print(f"""
    GERANDO PIX PAGHIPER
    TOTAL: R$ {valor}
    VALOR EM CENTAVOS: {valor_cents}
    COMISSÃO: R$ {comissao_cents/100:.2f}
    """)
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # ID único para o pedido
    order_id = "NGK_" + str(uuid.uuid4())[:8]
    
    data = {
        "apiKey": api_key,
        "order_id": order_id,
        "payer_email": "cliente@ngkpay.com",
        "payer_name": "Cliente NGK Pay",
        "payer_cpf_cnpj": "00000000191",  # CPF genérico
        "days_due_date": 3,  # 3 dias para vencimento
        "notification_url": f"{config['url']}/webhook/paghiper",
        "items": [{
            "description": "Assinatura Grupo VIP",
            "quantity": 1,
            "item_id": "1",
            "price_cents": valor_cents
        }]
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 201:
            response_data = response.json()
            
            # Extrai os dados necessários
            transaction_id = response_data['create_request']['transaction_id']
            pix_code = response_data['create_request']['bank_slip']['digitable_line']
            
            return {
                "pix_code": pix_code,
                "payment_id": str(transaction_id),
                "message": "PIX PagHiper gerado com sucesso."
            }
        else:
            return {
                "error": f"Erro ao criar PIX. Status: {response.status_code}",
                "details": response.text
            }
            
    except Exception as e:
        print(f"Erro ao processar PIX PagHiper: {e}")
        return {
            "error": "Erro ao processar requisição PIX",
            "details": str(e)
        }


