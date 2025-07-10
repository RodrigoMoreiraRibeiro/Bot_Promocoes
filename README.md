# Bot Discord - Preços KaBuM 🛒

Bot para Discord que busca preços de produtos na KaBuM usando web scraping.

## 🚀 Funcionalidades

- **Busca geral**: `!kabum <produto>` - Busca qualquer produto
- **Busca de GPU**: `!gpu <modelo>` - Busca placas de vídeo específicas
- **Busca de Monitor**: `!monitor <especificação>` - Busca monitores
- **Preço específico**: `!preco <URL>` - Busca preço de produto por URL
- **Ajuda**: `!ajuda` - Mostra todos os comandos

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Token de bot do Discord

## 🔧 Instalação

### 💻 Execução Local
1. **Clone ou baixe os arquivos**

2. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure o token do Discord**:
   - Copie o arquivo `.env.example` para `.env`
   - Adicione seu token do Discord no arquivo `.env`

4. **Execute o bot**:
   ```bash
   python bot_kabum.py
   ```

### 🚀 Execução com GitHub Actions

1. **Configure o Secret**:
   - Vá para Settings > Secrets and variables > Actions
   - Adicione um novo secret chamado `DISCORD_TOKEN`
   - Cole o token do seu bot Discord

2. **Configure workflows**:
   - `.github/workflows/discord-bot.yml` - Bot com timeout
   - `.github/workflows/persistent-bot.yml` - Bot persistente (execução manual)
   - `.github/workflows/scheduled-prices.yml` - Verificação automática de preços

3. **Execute**:
   - Push para branch `main` ou execução manual via Actions tab

## 🤖 Como obter o token do Discord

1. Vá para [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique em "New Application"
3. Dê um nome ao seu bot
4. Vá para "Bot" no menu lateral
5. Clique em "Add Bot"
6. Copie o token e cole no arquivo `.env`

## 📱 Como adicionar o bot ao servidor

1. No Discord Developer Portal, vá para "OAuth2" > "URL Generator"
2. Selecione "bot" em Scopes
3. Selecione as permissões necessárias:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
4. Copie a URL gerada e acesse-a para adicionar o bot

## 💡 Exemplos de uso

```
!kabum RTX 4090
!gpu RTX 4080
!monitor 27 4K
!preco https://www.kabum.com.br/produto/123456
!ajuda
```

## 🔍 Como funciona

O bot utiliza:
- **aiohttp** para fazer requisições HTTP assíncronas
- **BeautifulSoup** para fazer parsing do HTML
- **discord.py** para interagir com o Discord
- **Embeds** para exibir resultados de forma organizada

## ⚠️ Limitações

- Resultados limitados a 10 produtos por busca
- Dependente da estrutura HTML da KaBuM
- Pode ser afetado por mudanças no site
- Rate limiting para evitar sobrecarga

## 🛠️ Melhorias futuras

- [ ] Sistema de alertas de preço
- [ ] Comparação de preços históricos
- [ ] Notificações de promoções
- [ ] Filtros avançados de busca
- [ ] Suporte a outros sites

## 🔐 Configuração de Secrets (GitHub Actions)

1. **Vá para o seu repositório no GitHub**
2. **Settings > Secrets and variables > Actions**
3. **Adicione os seguintes secrets**:
   - `DISCORD_TOKEN` - Token do seu bot Discord
   - `DEFAULT_CHANNEL_ID` - ID do canal padrão para relatórios (opcional)

## 📄 Licença

Este projeto é para fins educacionais. Respeite os termos de uso da KaBuM.

Este projeto é para fins educacionais. Respeite os termos de uso da KaBuM.

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir melhorias
- Enviar pull requests

## 📞 Suporte

Se você encontrar problemas:
1. Verifique se o token está correto
2. Confirme que todas as dependências estão instaladas
3. Verifique se o bot tem as permissões necessárias no servidor