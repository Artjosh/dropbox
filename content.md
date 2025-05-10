# PDF Processing API

API para processamento de PDFs do Dropbox com suporte a monitoramento de logs em tempo real

## Autenticação

Todas as requisições à API requerem autenticação via cabeçalho `X-API-Key`.

- **Cabeçalho**: `X-API-Key`
- **Valor**: `josh_box` (substitua pelo seu API secret)

## Endpoints

### 1. Processamento de PDFs

- **URL**: `/process-pdfs`
- **Método**: POST
- **Descrição**: Processa arquivos PDF com o mesmo CPF, unindo-os em um único arquivo

#### Exemplo de Requisição

```bash
curl -X POST http://localhost:5000/process-pdfs -H "X-API-Key: josh_box"
```

#### Resposta

```json
{
  "message": "Processamento concluído: 2 arquivos processados",
  "processed_cpfs": {
    "00013550071": 2
  },
  "skipped_cpfs": 694,
  "success": true,
  "total_files": 696,
  "total_processed": 2
}
```

### 2. Consulta de Logs

- **URL**: `/status`
- **Método**: GET
- **Descrição**: Fornece acesso ao conteúdo do arquivo de log (`workspace.log`)

#### Parâmetros de Query

- `tail` (opcional): Retorna apenas as últimas N linhas. Exemplo: `?tail=100`
- `start` (opcional): Linha inicial para paginação. Exemplo: `?start=200`
- `length` (opcional): Número de linhas a retornar. Exemplo: `?length=500`

#### Exemplos de Uso

**Obter as últimas 10 linhas:**
```bash
curl "http://localhost:5000/status?tail=10" -H "X-API-Key: josh_box"
```

**Obter linhas específicas (paginação):**
```bash
curl "http://localhost:5000/status?start=100&length=50" -H "X-API-Key: josh_box"
```

#### Resposta (com tail)

```json
{
  "count": 5,
  "log_lines": [
    "10/05/2025 12:34:31 [INFO] Pasta de origem encontrada em: /aaaa/COMPROVANTE DE PAGAMENTO\n",
    "10/05/2025 12:34:32 [INFO] Pasta de saída encontrada em: /aaaa/USO_DO_ROBO\n",
    "10/05/2025 12:34:33 [INFO] Pasta de processados encontrada em: /aaaa/COMPROVANTES_DE_PAGAMENTO_PROCESSADOS\n",
    "10/05/2025 12:34:33 [INFO] Dropbox inicializado com sucesso\n",
    "10/05/2025 12:34:33 [INFO] Processador de PDF inicializado com sucesso\n"
  ],
  "tail": true
}
```

#### Resposta (com paginação)

```json
{
  "log_lines": [...],
  "total_lines": 155,
  "start": 100,
  "end": 150,
  "has_more": true
}
```

### 3. Streaming de Logs em Tempo Real

- **URL**: `/stream-logs`
- **Método**: GET
- **Descrição**: Fornece um streaming de logs em tempo real usando Server-Sent Events (SSE)

#### Como Funciona

Este endpoint estabelece uma conexão persistente com o cliente e envia novas linhas de log em tempo real à medida que são adicionadas ao arquivo `workspace.log`. É ideal para monitoramento contínuo.

O cliente recebe os eventos no formato Server-Sent Events (SSE), que pode ser implementado em navegadores usando a API EventSource. Cada nova linha de log é enviada como um evento separado.

#### Exemplo de Uso

Não é possível demonstrar completamente via curl, mas você pode iniciar a conexão:

```bash
curl -N "http://localhost:5000/stream-logs" -H "X-API-Key: josh_box"
```

#### Formato dos Eventos

```
data: {"log":"10/05/2025 12:34:33 [INFO] Dropbox inicializado com sucesso"}

data: {"log":"10/05/2025 12:34:33 [INFO] Processador de PDF inicializado com sucesso"}

data: {"event":"connected","message":"Conexão estabelecida"}
```

### 4. Download de Logs

- **URL**: `/download-logs`
- **Método**: GET
- **Descrição**: Permite baixar o arquivo de log completo

#### Exemplo de Uso

Para baixar o arquivo diretamente no navegador:

```bash
curl -O -J "http://localhost:5000/download-logs" -H "X-API-Key: josh_box"
```

O arquivo será baixado com o nome `logs-YYYYMMDD-HHMMSS.log` contendo a data e hora atual.

## Operação do Sistema

O sistema realiza as seguintes operações:

1. Procura a pasta `COMPROVANTE DE PAGAMENTO` no Dropbox
2. Procura a pasta `USO_DO_ROBO` (preferencialmente no mesmo local)
3. Cria a pasta `COMPROVANTES_DE_PAGAMENTO_PROCESSADOS` se não existir
4. Identifica arquivos PDF com o mesmo CPF no nome
5. Une PDFs com mesmo CPF e salva na pasta `USO_DO_ROBO`
6. Move os PDFs originais para a pasta `COMPROVANTES_DE_PAGAMENTO_PROCESSADOS`
7. Registra todas as operações no arquivo `workspace.log`