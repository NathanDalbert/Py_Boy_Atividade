import os
from pyboy import PyBoy

# Caminho para a ROM (considerando que você roda o script da pasta raiz)
rom_path = "roms/pokemon_red.gb"

# Verifica se o arquivo existe antes de tentar abrir
if not os.path.exists(rom_path):
    print(f"ERRO: Não encontrei o arquivo em: {rom_path}")
    print("Certifique-se de que baixou a ROM e renomeou para 'pokemon_red.gb'")
    exit()

print("Iniciando PyBoy...")

# Inicializa o PyBoy
# window_type="SDL2" faz a janelinha do jogo aparecer
pyboy = PyBoy(rom_path, window_type="SDL2")

print("Emulador rodando! Segure a janela aberta por 5 segundos...")

# Loop simples para manter o jogo rodando por um tempo (300 frames = ~5 segundos)
for _ in range(300):
    pyboy.tick()

pyboy.stop()
print("Teste finalizado com sucesso!")