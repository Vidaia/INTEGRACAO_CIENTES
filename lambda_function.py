from utils.TRIER import TRIER

def lambda_handler(event, context):
    t = TRIER(event)
    cliente = t.obter_dados(informacao='CLIENTE')
    produto = t.obter_dados(informacao='PRODUTO')
    venda = t.obter_dados(informacao='VENDA')
    venda = t.formatar_venda(venda)
    clientes = t.formatar_cliente(cliente, venda)
    produtos = t.formatar_produto(produto)
    clientes, produtos, venda = t.novos_dados(clientes, produtos, venda)
    t.inserir_dados(clientes, 'clientes')
    t.inserir_dados(produtos, 'produtos')
    t.inserir_dados(venda, 'vendas')
