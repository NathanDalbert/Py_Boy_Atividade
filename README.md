# Py_Boy_Atividade

# Equipe:
- Igor Emanuel Oliveira Rêgo
- Mickael de Albuquerque
- Nathan Dalbert 

## Controles de Áudio

O emulador inicia com `sound=True` e tenta acessar o volume do processo via **pycaw**.

Comandos suportados (enviados pelo `controller.py`):

- `MUTE`: Zera áudio do PyBoy (se API disponível) e volume do processo.
- `UNMUTE`: Restaura último volume real (padrão 50% se não conhecido).
- `VOL+` / `VOL-`: Ajustam volume em passos de 10% usando pycaw.
- `TURBO`, `NORMAL`, `LENTO`: Ajustam velocidade da emulação.

Se pycaw não estiver instalado ou falhar, os comandos de volume exibem mensagens, mas não alteram volume real.

### Instalação das Dependências

```powershell
pip install -r requirements.txt
```

### Teste Rápido

1. Inicie o game loop:
```powershell
python src/game_loop.py
```
2. Em outro terminal, abra o controlador:
```powershell
python src/controller.py
```
3. Envie comandos: `VOL+`, `VOL-`, `MUTE`, `UNMUTE`.

Observe o mixer de áudio do Windows para ver o volume do processo Python sendo ajustado.

## Execução via Docker

Você pode rodar o RabbitMQ em Docker enquanto executa a aplicação localmente:

### Iniciar RabbitMQ
```powershell
docker-compose up -d
```

O RabbitMQ estará disponível em:
- **AMQP**: `localhost:5672` (conexão da aplicação)
- **Management UI**: http://localhost:15672 (usuário: `guest`, senha: `guest`)

### Parar Docker
```powershell
docker-compose down
```

Para mais detalhes sobre Docker, consulte o arquivo [DOCKER.md](DOCKER.md).

## Orquestração (Rodar Tudo de Uma Vez)

Você pode iniciar os três componentes (game loop, controller e analytics) automaticamente:

### Opção 1: Script Python
```powershell
python run_all.py
```
Abre três consoles separados. Se uma venv existir em `.venv` (ou apontada por `VENV_PATH`), ela será ativada automaticamente em cada janela antes de rodar os scripts. Para parar, pressione CTRL+C na janela onde rodou `run_all.py`. Ele encerra todos os processos (game_loop, controller, analytics) de forma coordenada. Se qualquer um dos três terminar sozinho, os demais são encerrados automaticamente.

### Opção 2: Script PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File .\start_trio.ps1
```
Cria janelas independentes com cada processo. Detecta e ativa `.venv\Scripts\Activate.ps1` se existir (ou caminho definido em `VENV_PATH`). Este script NÃO encerra automaticamente os outros se um fechar; encerre manualmente.

### Variável `VENV_PATH`

Você pode apontar para outra venv:
```powershell
$env:VENV_PATH = 'C:\caminho\para\minha_venv'
python run_all.py
```
Ou:
```powershell
$env:VENV_PATH = 'C:\caminho\para\minha_venv'
powershell -ExecutionPolicy Bypass -File .\start_trio.ps1
```

Se usar ambiente virtual, ative-o antes de executar os scripts.

## Arquitetura / Módulos

### `app.config`
Carrega configuração via variáveis de ambiente (ex: `PYBOY_ROM`, `QUEUE_COMMANDS`, `QUEUE_EVENTS`).

### `app.constants`
Endereços de memória e nomes padrão de filas RabbitMQ.

### `app.volume`
Serviço para manipular volume do processo (pycaw opcional) com aquisição dinâmica e modo debug (`PYBOY_VOLUME_DEBUG=1`).

### `app.messaging`
Abstração fina sobre RabbitMQ: `connect`, `declare_queue`, `publish`, `consume`, encapsulando `pika` e removendo código duplicado.

### `app.logging_setup`
Inicializa logging padronizado (`PYBOY_LOG_LEVEL=DEBUG|INFO|WARNING`). Usa formato simples com hora, nível e nome do logger.

### Loggers
Cada script principal (`game_loop`, `controller`, `analytics`) obtém seu próprio logger e evita `print` para facilitar redirecionamento e filtros.

## Variáveis de Ambiente Principais
| Nome | Função | Default |
|------|---------|---------|
| `PYBOY_ROM` | Caminho da ROM | `roms/pokemon_red.gb` |
| `QUEUE_COMMANDS` | Nome fila comandos | `fila_comandos` |
| `QUEUE_EVENTS` | Nome fila eventos | `fila_eventos` |
| `PYBOY_LOG_LEVEL` | Nível de log | `INFO` |
| `PYBOY_VOLUME_DEBUG` | Ativa logs detalhados volume | `0` |
| `VENV_PATH` | Caminho de venv alternativa | `.venv` |

## Testes

### Executar (unittest legado)
```powershell
python -m unittest discover -s tests
```

### Executar (pytest)
```powershell
pytest -q
```

Com cobertura:
```powershell
pip install coverage
coverage run -m pytest
coverage report -m
```

Flag verbose e erros detalhados:
```powershell
pytest -vv
```

## Diagnóstico de Volume (pycaw)

Para ver tentativas de captura da interface de volume, defina a variável:
```powershell
$env:PYBOY_VOLUME_DEBUG = 1
python src/game_loop.py
```
Mensagens serão exibidas em stderr (ex: "Interface pycaw obtida" ou "Falha em obter interface").

Checklist rápido:
- `pip show pycaw comtypes` retornando versões → instalação OK.
- Executar jogo alguns segundos antes de `VOL+` para sessões de áudio aparecerem.
- Ambiente Windows nativo (não WSL) e Python 64 bits.
- Reinstalar se necessário: `pip install --force-reinstall pycaw comtypes`.


### Problemas Comuns

- Mensagem indicando ausência da interface: processo não listado nas sessões de áudio (tente gerar algum som primeiro).
- Sem alteração de volume: verifique se está fora de sandbox/remote e se pycaw/comtypes instalaram sem erro.
- Para redefinir: enviar `UNMUTE` ou ajustar manualmente pelo mixer.
