# beam_calculator — arquivos de logo

Monograma "b": a letra é formada por uma seção de viga, e os pontos representam as barras da armadura positiva.
Nos SVGs, os textos foram convertidos em contornos. Por isso abrem iguais em qualquer computador, sem precisar instalar fontes.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `svg/simbolo`, `png/simbolo` | Só o monograma (PNG em 256, 512 e 1024 px) |
| `svg/horizontal`, `png/horizontal` | Símbolo + nome, com e sem a assinatura "Dimensionamento de vigas em concreto armado" (PNG @2x e @4x) |
| `svg/vertical`, `png/vertical` | Versão empilhada, para capas e páginas de rosto |
| `svg/icone`, `png/icone` | Ícone de aplicativo, favicons (16/32/48 px e `.ico`), `apple-touch-icon` e ícones Android |

Cada logo vem em quatro versões:
- `cor`: para fundo claro
- `negativo`: para fundo escuro
- `mono-preto`: impressão em preto e branco
- `mono-branco`: aplicação sobre foto ou cor escura

Todos os PNGs têm fundo transparente, exceto os ícones de app.

## Cores

| Uso | Hex |
|---|---|
| Grafite (letra e texto) | `#1F2428` |
| Azul de destaque (fundo claro) | `#2F6FDB` |
| Azul de destaque (fundo escuro) | `#5B9BFF` |
| Texto claro sobre fundo escuro | `#F1F3F5` |
| Assinatura (fundo claro / escuro) | `#5B636B` / `#AEB5BC` |

## Fontes
- Nome: **JetBrains Mono Bold**
- Assinatura: **Inter Regular**

As duas são gratuitas (SIL Open Font License) e estão no Google Fonts.

## Uso
- Mantenha ao redor do logo uma área livre de pelo menos metade da largura do "b".
- Abaixo de 24 px de altura, use só o símbolo. Abaixo de 48 px, use o favicon simplificado (`favicon-claro.svg`).
- Não distorça, não gire e não troque as cores fora das versões acima.

## Favicon em uma página web

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon-180.png">
```

O `favicon.svg` muda sozinho para a versão clara quando o navegador está no modo escuro.
