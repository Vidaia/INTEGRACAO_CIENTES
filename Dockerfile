# Define o diretório onde a função estará localizada
ARG FUNCTION_DIR="/function"

# Etapa de construção da imagem
FROM python:3.12 AS build-image

# Inclui o argumento global nesta etapa da construção
ARG FUNCTION_DIR

# Cria o diretório para a função
RUN mkdir -p ${FUNCTION_DIR}

# Copia o código da função para o diretório especificado
COPY . ${FUNCTION_DIR}

# Instala as dependências da função (neste caso, 'awslambdaric' para a execução em Lambda)
RUN pip install --target ${FUNCTION_DIR} awslambdaric

RUN pip install --target ${FUNCTION_DIR} -r ${FUNCTION_DIR}/requirements.txt

# Usa uma versão slim da imagem base do Python para reduzir o tamanho final da imagem
FROM python:3.12-slim

# Inclui o argumento global nesta etapa da construção
ARG FUNCTION_DIR

# Define o diretório de trabalho como o diretório da função
WORKDIR ${FUNCTION_DIR}

# Copia as dependências instaladas da etapa de construção para a imagem final
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

# Define o cliente de interface de tempo de execução como o comando padrão para o runtime do container
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]

# Passa o nome do handler da função como argumento para o runtime
CMD [ "lambda_function.lambda_handler" ]
