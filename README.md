# Árvore da Vida

Animação de partículas em Python: uma semente de luz cai, cria raízes, cresce
como árvore e passa pelas quatro estações até se dissolver em luz e renascer.
Cada ciclo (~1 min) gera uma árvore diferente.

![Prévia das estações](docs/previa.png)

## Como rodar

```
pip install -r requirements.txt
python arvore_da_vida.py
```

No Windows, se `python`/`pip` não forem encontrados, use `py -m pip install -r requirements.txt` e `py arvore_da_vida.py`.

Opcional: `python arvore_da_vida.py --seed 21` sempre gera a mesma árvore.

## Controles

| Tecla    | Ação                          |
|----------|-------------------------------|
| Espaço   | pausar / continuar            |
| ← / →    | voltar / avançar 4 segundos   |
| 1 … 8    | pular para uma fase           |
| R        | nova árvore                   |
| S        | salvar imagem (png)           |
| ESC      | sair                          |

## Ajustes rápidos (topo do arquivo)

- `W, H` — tamanho da janela (diminua se ficar lento)
- `TRAIL` — rastro das partículas (0 desliga)
- `EXPOSURE` — brilho geral
- Paletas: `BARK_A`, `BARK_B`, `SPRING_P`, `SUMMER_P`, `AUTUMN_P`, `SKY_KEYS`
