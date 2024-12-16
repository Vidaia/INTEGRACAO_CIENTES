import pandas as pd
import requests
from utils import arrumar_json_itens, ultima_compra, numero_telefone
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class TRIER():  
    def __init__(self, event):
        self.event = event
        self.user = event.get("user")
        self.password =event.get("password")
        self.host = event.get("host")
        self.database = event.get("database")
        self.port = event.get("port")
        self.api_token = event.get("API_TOKEN")
        self.data_inicial = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        self.data_final = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.usuarioId = self.event.get("usuario_id")
        self.URL_VENDA_API = f"https://api-sgf-gateway.triersistemas.com.br/sgfpod1/rest/integracao/venda/obter-v1?"
        self.URL_PRODUTO_API = f"https://api-sgf-gateway.triersistemas.com.br/sgfpod1/rest/integracao/produto/obter-todos-v1?"
        self.URL_CLIENTE_API = f"https://api-sgf-gateway.triersistemas.com.br/sgfpod1/rest/integracao/cliente/obter-todos-v1?"
        self.quantidade_registros = 999

        try:
            conn_str = f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'
            engine = create_engine(conn_str)
            self.headers = {
                "Authorization": f"Bearer {self.api_token}"
            }
            self.clientes_total_em_banco = pd.read_sql(f'SELECT COUNT(*) as total FROM clientes WHERE "usuarioId" = {self.usuarioId}', engine).apply(lambda row: max(row['total'] - 50, 0), axis=1).iloc[0]
            self.produtos_total_em_banco = pd.read_sql(f'SELECT COUNT(*) as total FROM produtos WHERE "usuarioId" = {self.usuarioId}', engine).apply(lambda row: max(row['total'] - 50, 0), axis=1).iloc[0]
            self.vendas_total_em_banco = pd.read_sql(f'SELECT COUNT(*) as total FROM vendas WHERE "usuarioId" = {self.usuarioId}', engine).apply(lambda row: max(row['total'] - 50, 0), axis=1).iloc[0]

        except Exception as e:
            logging.error(f"Houve um erro ao criar a engine do banco, o código não será executado! {str(e)}")

    def obter_dados(self, informacao):
        logger.info("Iniciando a obtenção de dados...")
        """
        PrimeiroRegistro = Ponto de partida da requisição, padrão = 0
        Informação = ["Cliente", "Produto", "Venda"]
        """
        if informacao not in ["CLIENTE", "PRODUTO", "VENDA", "CANCELAMENTO", "ALTERADO"]:
            raise ValueError("Informação inválida. Deve ser 'Cliente', 'Produto' ou 'Venda'.")
        df_final = pd.DataFrame()            
        if informacao=="VENDA":
            primeiro_registro = 0
        elif informacao=="PRODUTO":
            primeiro_registro = 0
        elif informacao=="CLIENTE":
            primeiro_registro = 0
           
        while True:
            if informacao=="VENDA":
                logger.info("Baixando novas vendas...")
                url = f"{self.URL_VENDA_API}primeiroRegistro={primeiro_registro}&quantidadeRegistros=999&dataEmissaoInicial={self.data_inicial}&dataEmissaoFinal={self.data_final}"
            elif informacao=="PRODUTO":
                logger.info("Baixando novos produtos...")
                url = f"{self.URL_PRODUTO_API}primeiroRegistro={primeiro_registro}&quantidadeRegistros=999&dataInicial={self.data_inicial}&dataFinal={self.data_final}"
            elif informacao=="CLIENTE":
                logger.info("Baixando novos clientes...")
                url = f"{self.URL_CLIENTE_API}primeiroRegistro={primeiro_registro}&quantidadeRegistros=999&dataInicial={self.data_inicial}&dataFinal={self.data_final}"
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"Erro ao acessar a API: {str(response.status_code)}")
                break
            data = response.json()
            df = pd.DataFrame(data)
            if df.empty:
                break
            df_final = pd.concat([df_final, df], ignore_index=True)
            primeiro_registro += int(self.quantidade_registros)
        return df_final
    
    def formatar_venda(self, venda):
        if venda.empty:
            logger.error(f"Não há novas vendas, nenhum dado novo será atualizado!")
            raise Exception("Nenhuma venda para processar.")  
        else:
            venda['itens'] = venda['itens'].apply(lambda x: arrumar_json_itens.corrigir_json(x) if isinstance(x, str) else x)
            df_expanded = venda.explode('itens').reset_index(drop=True)
            df_itens = pd.json_normalize(df_expanded['itens'])
            df_final = pd.concat([df_expanded.drop(columns=['itens', 'codigoVendedor']), df_itens], axis=1)
            dfVenda = pd.DataFrame({
                        "codigoVenda" : df_final['numeroNota'],
                        "usuarioId" : self.usuarioId,
                        "codigoProduto" : df_final['codigoProduto'],
                        "Vendedor" : df_final['codigoVendedor'],
                        "data" : df_final['dataEmissao'],
                        "quantidade" : df_final['quantidadeProdutos'],
                        "valorVenda" : df_final['valorTotalLiquido'],
                        "desconto" : "0",
                        "codigoCliente" : df_final['codigoCliente'].fillna(0).astype(int),
                        'updatedAt' : datetime.now()
                        })

            dfVenda = dfVenda.groupby(dfVenda.columns.difference(['quantidade', 'valorVenda']).tolist(), as_index=False).agg({
                'quantidade': 'sum',
                'valorVenda': 'sum'
            })
            dfVenda = dfVenda.drop_duplicates(subset=["usuarioId", "codigoVenda", "codigoProduto"])
            return dfVenda

    def formatar_produto(self, produto):
        if produto.empty:
            logger.error(f"Não há novos produtos, nenhum dado novo será atualizado!")
            raise Exception("Nenhum produto para processar.")  
        else:
            dfProdutos = pd.DataFrame({
                'nome': produto['nome'],
                'codigoDeBarras': produto['codigoBarras'].fillna("0"),
                'codigoDeBarras2': "0",
                'fabricante': produto['nomeLaboratorio'].fillna('NÃO TEM'),
                'grupo': produto['nomeGrupo'].fillna('NÃO TEM'),
                'classe': produto['nomeCategoria'].fillna('NÃO TEM'),
                'valor': produto['valorVenda'].fillna(0),
                'custo': produto['valorCusto'].fillna(0),
                'usuarioId': self.usuarioId,
                'codigoProduto': produto['codigo'],
                'updatedAt' : datetime.now()
                })
            return dfProdutos

    def formatar_cliente(self, cliente, vendas):
        if cliente.empty:
            logger.error(f"Não há novos produtos, nenhum dado novo será atualizado!")
            raise Exception("Nenhum cliente para processar.")  
        else:
            dfClientes = pd.DataFrame({
                "usuarioId" : self.usuarioId,
                "telefone" : cliente['fone'].fillna("0"),
                "telefone2" : "",
                "telefone3" : "",
                "nome" : cliente['nome'],
                "cpf" : cliente["numeroCpfCnpj"],
                "codigoCliente" : cliente['codigo'].fillna(0),
                "ultimaCompra" : cliente['codigo'].apply(lambda x: ultima_compra.ultimacompra(x, vendas)),
                "CEP": cliente['cep'],
                "endereco": cliente['logradouro'],
                "numero": cliente['numeroEndereco'],
                "dataNascimento" : pd.to_datetime('1900-01-01').date(),
                "clienteDesde" : pd.to_datetime('1900-01-01').date(),
                'updatedAt' : datetime.now()
                })
            dfClientes['telefone'] = dfClientes['telefone'].apply(numero_telefone.padronizar_telefone_brasileiro)
            dfClientes['telefone'] = dfClientes['telefone'].str.replace(r'\D', '', regex=True)
                    
            return dfClientes

    def novos_dados(self, clientes_novos, produtos_novos, vendas_novas):
        conn_str = f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'
        engine = create_engine(conn_str)

        clientes = pd.read_sql(f'select "codigoCliente" from clientes where "usuarioId" = {self.usuarioId}', engine)
        produtos = pd.read_sql(f'select "codigoProduto" from produtos where "usuarioId" = {self.usuarioId}', engine)
        vendas = pd.read_sql(f'select "codigoProduto", "codigoVenda" from vendas where "usuarioId" = {self.usuarioId}', engine)

        clientes['codigoCliente'] = clientes['codigoCliente'].astype(int)
        produtos['codigoProduto'] = produtos['codigoProduto'].astype(int)
        vendas['codigoVenda'] = vendas['codigoVenda'].astype(int)
        vendas['codigoProduto'] = vendas['codigoProduto'].astype(int)
        colunas_comparacao = ['codigoVenda', 'codigoProduto']
        novos_clientes = clientes_novos[~clientes_novos['codigoCliente'].isin(clientes['codigoCliente'])]
        novos_produtos = produtos_novos[~produtos_novos['codigoProduto'].isin(produtos['codigoProduto'])]
        vendas_novas_unicas = vendas_novas[~vendas_novas[colunas_comparacao].apply(tuple, 1).isin(vendas[colunas_comparacao].apply(tuple, 1))]
        return novos_clientes, novos_produtos, vendas_novas_unicas

    def inserir_dados(self, tabela, nome_tabel):
        conn_str = f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'
        engine = create_engine(conn_str)
        if nome_tabel not in ["clientes", "produtos", "vendas"]:
            raise ValueError("Informação inválida. Deve ser 'clientes', 'produtos' ou 'vendas'.")
        try:
            tabela.to_sql(f'{nome_tabel}', engine, index=False, if_exists='append', method='multi', chunksize=10000)
        except Exception as e:
            logging.error(f"Houve um erro ao criar a engine do banco, o código não será executado! {str(e)}")
            raise Exception("engine")