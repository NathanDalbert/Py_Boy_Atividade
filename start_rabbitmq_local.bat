@echo off
echo ============================================
echo   Iniciando RabbitMQ Local
echo ============================================
echo.

REM Verificar se Docker está disponível
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Docker detectado
    echo.
    echo Iniciando RabbitMQ via Docker (modo leve)...
    echo.

    REM Parar container antigo se existir
    docker stop pyboy_rabbitmq_local >nul 2>&1
    docker rm pyboy_rabbitmq_local >nul 2>&1

    REM Iniciar RabbitMQ em container
    docker run -d ^
        --name pyboy_rabbitmq_local ^
        -p 5672:5672 ^
        -p 15672:15672 ^
        rabbitmq:3-management

    if %errorlevel% equ 0 (
        echo.
        echo ✅ RabbitMQ iniciado com sucesso!
        echo.
        echo 📊 Management UI: http://localhost:15672
        echo    Usuario: guest
        echo    Senha: guest
        echo.
        echo ℹ️  Para parar: docker stop pyboy_rabbitmq_local
        echo.
    ) else (
        echo.
        echo ❌ Erro ao iniciar RabbitMQ via Docker
        echo.
    )
) else (
    echo [X] Docker não encontrado
    echo.
    echo Tentando iniciar RabbitMQ instalado localmente...
    echo.

    REM Tentar iniciar serviço do Windows
    net start RabbitMQ >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ RabbitMQ (serviço Windows) iniciado!
        echo.
    ) else (
        REM Tentar executar rabbitmq-server diretamente
        where rabbitmq-server >nul 2>&1
        if %errorlevel% equ 0 (
            echo Iniciando rabbitmq-server...
            start "RabbitMQ Server" rabbitmq-server
            echo.
            echo ✅ RabbitMQ iniciado em nova janela
            echo.
        ) else (
            echo.
            echo ❌ RabbitMQ não foi encontrado!
            echo.
            echo 📥 Opções para instalar:
            echo.
            echo 1. Docker Desktop: https://www.docker.com/products/docker-desktop
            echo    Depois execute este script novamente
            echo.
            echo 2. RabbitMQ nativo: https://www.rabbitmq.com/download.html
            echo    Instale com Erlang incluído
            echo.
            echo 3. Chocolatey: choco install rabbitmq
            echo.
            echo ℹ️  A aplicação funcionará em MODO DEGRADADO sem RabbitMQ
            echo    (funcionalidades limitadas mas o jogo rodará)
            echo.
        )
    )
)

echo ============================================
echo.
pause
