# Instalação do beam_calculator

O beam_calculator é distribuído pronto para usar: não é preciso instalar Python
nem nenhum outro programa.

## 1. Baixar

Na página **Releases** do repositório
(<https://github.com/arturkcorr3a/beam_calculator/releases>), abra a versão mais
recente e baixe, em **Assets**, o arquivo do seu sistema:

| Sistema | Arquivo |
|---|---|
| Windows 10 ou 11 (64 bits) | `beam_calculator-Setup-<versão>.exe` |
| Fedora | `beam_calculator-<versão>-1.fc43.x86_64.rpm` |
| Outras distribuições Linux | `beam_calculator-<versão>-linux-x86_64.tar.gz` |

## 2. Instalar

### Windows

1. Dê dois cliques em `beam_calculator-Setup-<versão>.exe`.
2. Se aparecer a tela azul **"O Windows protegeu o computador"**, clique em
   **Mais informações** e depois em **Executar assim mesmo**. O aviso aparece
   porque o instalador não tem assinatura digital paga; não indica problema
   no programa.
3. Siga o assistente: aceite a licença, escolha se quer um atalho na área de
   trabalho e clique em **Instalar**. Não é pedida senha de administrador.
4. Abra o programa pelo **Menu Iniciar → beam_calculator**.

**Atualizar:** instale a versão nova da mesma forma; ela substitui a anterior.

**Desinstalar:** **Configurações → Aplicativos → Aplicativos instalados →
beam_calculator → Desinstalar**.

### Fedora

No terminal, na pasta onde o arquivo foi baixado:

```bash
sudo dnf install ./beam_calculator-<versão>-1.fc43.x86_64.rpm
```

Abra o programa pelo menu de aplicativos (**beam_calculator**) ou pelo comando
`beam_calculator`.

**Atualizar:** o mesmo comando, com o arquivo da versão nova.

**Desinstalar:** `sudo dnf remove beam_calculator`

### Outras distribuições Linux

```bash
tar -xzf beam_calculator-<versão>-linux-x86_64.tar.gz
./beam_calculator/beam_calculator
```

Para incluir o programa no menu de aplicativos, com ícone, rode uma vez
`./beam_calculator/install.sh`. A pasta `beam_calculator` pode ficar onde
você quiser, mas o menu aponta para ela: se movê-la, rode o `install.sh` de novo.

**Desinstalar:** rode `./beam_calculator/install.sh --uninstall` e apague a
pasta `beam_calculator`.

## 3. Onde fica o memorial de cálculo

O memorial de cálculo é gravado automaticamente a cada execução, num arquivo
`beam_calculator_<data-hora>.log`, na pasta de registros do sistema. A pasta
também aparece no programa, em **Ferramentas → Configurações…**, seção
**Memorial de cálculo**; o caminho pode ser selecionado e copiado.

| Sistema | Pasta |
|---|---|
| Windows | `%LOCALAPPDATA%\beam_calculator\Logs` |
| Linux | `~/.local/state/beam_calculator/log` |

**Para abrir a pasta no Windows:** pressione **Win + R**, cole
`%LOCALAPPDATA%\beam_calculator\Logs` e pressione **Enter**. Também funciona
colando o caminho na barra de endereço do Explorador de Arquivos.

**Para abrir a pasta no Linux:** no gerenciador de arquivos, pressione
**Ctrl + L**, cole `~/.local/state/beam_calculator/log` e pressione **Enter**.
A pasta `.local` é oculta; por isso é mais fácil chegar a ela pelo caminho.

Os arquivos de projeto (`.yaml`), os PDFs e os DXFs são salvos onde você
escolher, nas janelas de salvar e exportar do programa.

## Licença

O beam_calculator é software livre, distribuído sob a licença GNU GPL versão 3
ou posterior, sem qualquer garantia (veja [LICENSE](LICENSE)). O código-fonte
está neste repositório.
