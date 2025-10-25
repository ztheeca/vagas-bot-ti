# ===========================
# 📦 IMPORTAÇÕES
# ===========================
import os
import time
import random
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 🧠 Selenium para busca no Indeed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_chrome_github_actions():
    """Configuração específica para GitHub Actions"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")
    
    # User agent para Linux
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return options

# Carrega variáveis do arquivo .env
load_dotenv()

# ===========================
# 🔧 CONFIGURAÇÕES
# ===========================

# Webhook do Discord
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
# Local padrão
LOCAL = os.getenv("LOCAL", "Salvador, BA")
# ADICIONADO: Configurações Glassdoor
GLASSDOOR_EMAIL = os.getenv("GLASSDOOR_EMAIL")  # Opcional para login
GLASSDOOR_PASSWORD = os.getenv("GLASSDOOR_PASSWORD")  # Opcional para login

# Novas configurações do .env
MAX_VAGAS_POR_PLATAFORMA = int(os.getenv("MAX_VAGAS_POR_PLATAFORMA", "8"))
INTERVALO_BUSCA_MINUTOS = int(os.getenv("INTERVALO_BUSCA_MINUTOS", "60"))
TENTATIVAS_BUSCA = int(os.getenv("TENTATIVAS_BUSCA", "3"))
TIMEOUT_PAGINA = int(os.getenv("TIMEOUT_PAGINA", "30"))
GRUPO_MENSAGEM_DISCORD = int(os.getenv("GRUPO_MENSAGEM_DISCORD", "2"))

# Termos que queremos procurar
PALAVRAS_CHAVE = ["junior", "assistente", "auxiliar", "desenvolvedor", "programador", "TI", "tecnologia", "sistema", "software", "analista"]
# Termos para filtrar vagas de TI
TERMOS_TI = ["TI", "tecnologia", "desenvolvedor", "programador", "sistema", "software", "analista", "dados", "web", "mobile", "backend", "frontend", "dev", "engenharia", "computação"]

# ===========================
# ⚠️ CONFIGURAÇÕES DE SEGURANÇA
# ===========================
REQUESTS_POR_HORA = 4  # Máximo de buscas por hora
ULTIMA_EXECUCAO = 0

# ===========================
# 🛡️ FUNÇÕES ANTI-DETECÇÃO
# ===========================
def verificar_limite_requisicoes():
    """Controla rate limiting para evitar muitas requisições"""
    global ULTIMA_EXECUCAO
    agora = time.time()
    
    if agora - ULTIMA_EXECUCAO < (3600 / REQUESTS_POR_HORA):
        espera = (3600 / REQUESTS_POR_HORA) - (agora - ULTIMA_EXECUCAO)
        log_info(f"⏳ Rate limiting: aguardando {espera:.1f} segundos")
        time.sleep(espera)
    
    ULTIMA_EXECUCAO = time.time()

def configurar_proxy(options):
    """Configura proxy para rotacionar IPs (opcional)"""
    # Lista de proxies gratuitos (atualize regularmente)
    proxies = [
        # "ip:porta",  # Adicione proxies aqui
        # "192.168.1.1:8080",
    ]
    
    if proxies:
        proxy = random.choice(proxies)
        options.add_argument(f"--proxy-server={proxy}")
        log_info(f"🔒 Usando proxy: {proxy}")
    else:
        log_debug("ℹ️  Nenhum proxy configurado - usando IP real")

# ===========================
# 📝 CONFIGURAÇÃO DE LOGS
# ===========================
def setup_logging():
    """Configura o sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vagas_bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def log_info(message):
    """Log de informações"""
    logging.info(f"📝 {message}")

def log_error(message):
    """Log de erros"""
    logging.error(f"❌ {message}")

def log_success(message):
    """Log de sucesso"""
    logging.info(f"✅ {message}")

def log_debug(message):
    """Log para debug"""
    logging.debug(f"🔍 {message}")

# ===========================
# 🛠️ FUNÇÕES AUXILIARES
# ===========================
def espera_aleatoria():
    """Espera um tempo aleatório entre ações para parecer mais humano"""
    tempo = random.uniform(1, 3)
    time.sleep(tempo)

def scroll_suave(driver):
    """Faz scroll suave na página (usado como fallback)"""
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(0, total_height, 100):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.05)
    except Exception as e:
        log_debug(f"Erro no scroll suave: {e}")

def validar_vaga(titulo, link):
    """Valida se os dados da vaga são consistentes"""
    if not titulo or not link:
        return False
    
    # Remove vagas com títulos muito curtos ou genéricos
    if len(titulo.strip()) < 5:
        return False
    
    # Verifica se o link é válido
    if not link.startswith(('http://', 'https://')):
        return False
    
    return True

def normalizar_titulo(titulo):
    """Remove espaços extras e normaliza o título"""
    return ' '.join(titulo.split())

def buscar_vagas_com_tentativas(funcao_busca, nome_plataforma, tentativas=TENTATIVAS_BUSCA):
    """Executa a busca com múltiplas tentativas em caso de falha"""
    for tentativa in range(tentativas):
        try:
            log_info(f"Tentativa {tentativa + 1} para {nome_plataforma}")
            vagas = funcao_busca()
            if vagas:
                log_success(f"{nome_plataforma}: {len(vagas)} vagas encontradas")
                return vagas
            else:
                log_info(f"{nome_plataforma}: Nenhuma vaga encontrada na tentativa {tentativa + 1}")
                
        except Exception as e:
            log_error(f"Erro na tentativa {tentativa + 1} para {nome_plataforma}: {str(e)}")
            if tentativa < tentativas - 1:
                log_info(f"Aguardando 5 segundos antes da próxima tentativa...")
                time.sleep(5)
    
    log_error(f"Todas as {tentativas} tentativas falharam para {nome_plataforma}")
    return []

def configurar_navegador_avancado():
    """Configuração mais avançada para evitar detecção"""
    options = Options()
    
    # Configurações básicas de stealth
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Remoção de automação
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Outras otimizações
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-popup-blocking")
    
    # User-Agent realista e atualizado (rotaciona entre vários)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    # Preferências para evitar detecção
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2,  # Reduz carregamento de imagens
    })
    
    # Configura proxy (opcional)
    configurar_proxy(options)
    
    return options

def remover_rastros_automacao(driver):
    """Remove todos os rastros de automação do navegador"""
    try:
        # Remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Remove automation traits
        driver.execute_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # Muda propriedades do Chrome via CDP
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        log_debug("✅ Rastros de automação removidos")
    except Exception as e:
        log_error(f"❌ Erro ao remover rastros: {e}")

def comportamento_humano_avancado(driver):
    """Simula comportamento humano mais realista"""
    try:
        # Movimentos de mouse e scroll aleatórios
        driver.execute_script("""
            const randomMove = () => {
                window.scrollTo({
                    top: Math.random() * 500,
                    left: 0,
                    behavior: 'smooth'
                });
            };
            setTimeout(randomMove, 1000);
            setTimeout(randomMove, 3000);
        """)
        
        # Tempo de espera mais humano
        time.sleep(random.uniform(2, 5))
        
        # Scroll mais natural e variado
        scroll_height = driver.execute_script("return document.body.scrollHeight")
        scroll_steps = random.randint(3, 8)
        
        for i in range(scroll_steps):
            scroll_pos = random.randint(0, scroll_height)
            driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
            time.sleep(random.uniform(0.5, 1.5))
            
        log_debug("✅ Comportamento humano simulado")
        
    except Exception as e:
        log_error(f"❌ Erro no comportamento humano: {e}")



# ===========================
# 🔍 FUNÇÃO: Buscar vagas no Indeed (Versão Corrigida)
# ===========================
def buscar_vagas_indeed():
    log_info("🌐 Iniciando busca no Indeed...")
    
    vagas_encontradas = []
    driver = None
    
    try:
        # Rate limiting
        verificar_limite_requisicoes()

        # Configuração avançada do navegador
        options = setup_chrome_github_actions()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Remove rastros de automação avançados
        remover_rastros_automacao(driver)
        
        # Monta URL
        termos = "+OR+".join(PALAVRAS_CHAVE)
        url = f"https://br.indeed.com/jobs?q={termos}&l={LOCAL.replace(' ', '+')}"
        log_info(f"🔗 Acessando: {url}")
        
        # Acessa a página
        driver.get(url)
        
        # Aguarda carregamento com timeout configurável
        WebDriverWait(driver, TIMEOUT_PAGINA).until(
            lambda d: "Indeed" in d.title and "Blocked" not in d.title
        )
        log_info(f"📄 Página carregada: {driver.title}")
        
        # Comportamento humano avançado
        comportamento_humano_avancado(driver)
        
        # Aguarda elementos das vagas
        WebDriverWait(driver, TIMEOUT_PAGINA).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.jcs-JobTitle"))
        )
        
        # Captura vagas
        vagas = driver.find_elements(By.CSS_SELECTOR, "a.jcs-JobTitle")
        log_info(f"🔍 {len(vagas)} elementos de vaga encontrados")
        
        # Processa vagas (com limite configurável)
        for job in vagas[:MAX_VAGAS_POR_PLATAFORMA]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                # Valida vaga
                if not validar_vaga(titulo, link):
                    log_debug(f"Vaga inválida descartada: {titulo}")
                    continue
                
                # Filtra por termos de TI
                titulo_lower = titulo.lower()
                if any(termo.lower() in titulo_lower for termo in TERMOS_TI):
                    vaga_formatada = f"**{titulo}**\n{link}"
                    vagas_encontradas.append(vaga_formatada)
                    log_success(f"Vaga filtrada (TI): {titulo}")
                else:
                    log_debug(f"Vaga descartada (não TI): {titulo}")
                    
            except Exception as e:
                log_error(f"Erro ao processar vaga individual: {e}")
                continue
        
        log_success(f"Indeed: {len(vagas_encontradas)} vagas de TI válidas encontradas")
        
    except Exception as e:
        log_error(f"Erro geral na busca Indeed: {e}")
        # Debug adicional
        if driver:
            try:
                page_title = driver.title
                page_url = driver.current_url
                log_debug(f"Title: {page_title}, URL: {page_url}")
            except:
                log_debug("Não foi possível obter informações da página")
        
    finally:
        # Fecha o navegador com segurança
        if driver:
            try:
                driver.quit()
                log_debug("Navegador Indeed fechado")
            except Exception as e:
                log_error(f"Erro ao fechar navegador Indeed: {e}")
    
    return vagas_encontradas

# ===========================
# 🔍 FUNÇÃO: Buscar vagas no Glassdoor (Versão Corrigida)
# ===========================
def buscar_vagas_glassdoor():
    log_info("🌐 Iniciando busca no Glassdoor...")
    
    vagas_encontradas = []
    driver = None
    
    try:
        # Rate limiting
        verificar_limite_requisicoes()

        # Configuração avançada do navegador
        options = setup_chrome_github_actions()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Remove rastros de automação avançados
        remover_rastros_automacao(driver)
        
        # Monta URL do Glassdoor - formato brasileiro
        termos = " ".join(PALAVRAS_CHAVE)
        local_formatado = LOCAL.replace(" ", "%20")
        url = f"https://www.glassdoor.com.br/Vaga/{termos.replace(' ', '-')}-vagas-{local_formatado}-SRCH_KO0,14.htm"
        log_info(f"🔗 Acessando: {url}")
        
        # Acessa a página
        driver.get(url)
        
        # Aguarda carregamento
        WebDriverWait(driver, TIMEOUT_PAGINA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='jobListing']"))
        )
        log_info(f"📄 Página carregada: {driver.title}")
        
        # Comportamento humano avançado
        comportamento_humano_avancado(driver)
        
        # Lida com popups/cookies se existirem
        try:
            popup_close = driver.find_elements(By.CSS_SELECTOR, ".modal_close, .close-button, [aria-label='Fechar']")
            if popup_close:
                popup_close[0].click()
                log_info("✅ Popup fechado")
                espera_aleatoria()
        except:
            log_debug("Nenhum popup encontrado ou erro ao fechar")
        
        # Captura vagas - seletores comuns do Glassdoor
        seletores_vagas = [
            "[data-test='jobListing']",
            ".jobListing",
            ".jl",
            ".react-job-listing"
        ]
        
        vagas = []
        for seletor in seletores_vagas:
            vagas = driver.find_elements(By.CSS_SELECTOR, seletor)
            if vagas:
                log_info(f"🔍 {len(vagas)} vagas encontradas com seletor: {seletor}")
                break
        
        if not vagas:
            log_info("🔍 Tentando seletor alternativo para links de vagas...")
            vagas = driver.find_elements(By.CSS_SELECTOR, "a.jobLink")
        
        # Processa vagas
        for job in vagas[:MAX_VAGAS_POR_PLATAFORMA]:
            try:
                # Tenta extrair título e link de diferentes formas
                titulo = ""
                link = ""
                
                # Método 1: Elemento de título dentro do listing
                try:
                    titulo_element = job.find_element(By.CSS_SELECTOR, "[data-test='job-title'], .jobTitle, a.jobLink")
                    titulo = titulo_element.text.strip()
                    if titulo_element.tag_name == "a":
                        link = titulo_element.get_attribute("href")
                    else:
                        link_element = job.find_element(By.CSS_SELECTOR, "a")
                        link = link_element.get_attribute("href")
                except:
                    # Método 2: Fallback - pega texto principal e link
                    titulo = job.text.strip().split('\n')[0]
                    link_elements = job.find_elements(By.CSS_SELECTOR, "a")
                    if link_elements:
                        link = link_elements[0].get_attribute("href")
                
                # Valida vaga
                if not validar_vaga(titulo, link):
                    log_debug(f"Vaga inválida descartada: {titulo}")
                    continue
                
                # Garante que o link é absoluto
                if link and link.startswith('/'):
                    link = f"https://www.glassdoor.com.br{link}"
                
                # Filtra por termos de TI
                titulo_lower = titulo.lower()
                if any(termo.lower() in titulo_lower for termo in TERMOS_TI):
                    vaga_formatada = f"**{titulo}**\n{link}"
                    vagas_encontradas.append(vaga_formatada)
                    log_success(f"Vaga filtrada (TI): {titulo}")
                else:
                    log_debug(f"Vaga descartada (não TI): {titulo}")
                    
            except Exception as e:
                log_error(f"Erro ao processar vaga individual do Glassdoor: {e}")
                continue
        
        log_success(f"Glassdoor: {len(vagas_encontradas)} vagas de TI válidas encontradas")
        
    except Exception as e:
        log_error(f"Erro geral na busca Glassdoor: {e}")
        
        # Debug adicional
        if driver:
            try:
                log_debug(f"URL atual: {driver.current_url}")
                log_debug(f"Título: {driver.title}")
                # Tira screenshot para debug (opcional)
                driver.save_screenshot("glassdoor_error.png")
                log_info("📸 Screenshot salvo como 'glassdoor_error.png'")
            except:
                pass
        
    finally:
        # Fecha o navegador com segurança
        if driver:
            try:
                driver.quit()
                log_debug("Navegador Glassdoor fechado")
            except Exception as e:
                log_error(f"Erro ao fechar navegador Glassdoor: {e}")
    
    return vagas_encontradas
    
# ===========================
# 🚀 FUNÇÃO: Enviar mensagem para o Discord (Melhorada)
# ===========================
def enviar_discord(vagas):
    """Envia vagas para o Discord com tratamento robusto de erros"""
    
    # Validações iniciais
    if not DISCORD_WEBHOOK_URL:
        log_error("DISCORD_WEBHOOK_URL não está definida no arquivo .env")
        return
    
    if not DISCORD_WEBHOOK_URL.startswith("https://discord.com/api/webhooks/"):
        log_error("DISCORD_WEBHOOK_URL parece inválida")
        return
    
    if not vagas:
        log_info("Nenhuma vaga para enviar ao Discord")
        # Opcional: enviar mensagem informando que não há vagas
        mensagem_vazia = {
            "content": f"📭 Nenhuma vaga nova encontrada em {LOCAL} na última busca ({datetime.now().strftime('%d/%m/%Y %H:%M')})"
        }
        try:
            requests.post(DISCORD_WEBHOOK_URL, json=mensagem_vazia, timeout=10)
        except:
            pass
        return
    
    log_info(f"Preparando para enviar {len(vagas)} vagas para o Discord")
    
    # Divide as vagas em grupos
    grupo_tamanho = GRUPO_MENSAGEM_DISCORD
    total_grupos = (len(vagas) + grupo_tamanho - 1) // grupo_tamanho
    
    for i in range(0, len(vagas), grupo_tamanho):
        grupo_numero = (i // grupo_tamanho) + 1
        grupo = vagas[i:i + grupo_tamanho]
        
        # Prepara mensagem
        conteudo = "\n\n".join(grupo)
        mensagem = {
            "content": f"🎯 **Vagas de TI em {LOCAL}** ({datetime.now().strftime('%d/%m/%Y')})\n"
                      f"📦 Parte {grupo_numero}/{total_grupos}\n\n"
                      f"{conteudo}\n\n"
                      f"🔍 *Encontrado via Bot de Vagas*"
        }
        
        # Valida tamanho da mensagem
        comprimento = len(mensagem["content"])
        log_debug(f"Tamanho da mensagem parte {grupo_numero}: {comprimento} caracteres")
        
        if comprimento > 2000:
            log_info(f"Mensagem parte {grupo_numero} muito longa, truncando...")
            excesso = comprimento - 1997
            mensagem["content"] = mensagem["content"][:1997] + "..."
        
        # Envia para Discord
        try:
            resposta = requests.post(
                DISCORD_WEBHOOK_URL, 
                json=mensagem, 
                timeout=15,
                headers={'Content-Type': 'application/json'}
            )
            
            if resposta.status_code == 204:
                log_success(f"Parte {grupo_numero}/{total_grupos} enviada com sucesso!")
            else:
                log_error(f"Erro ao enviar parte {grupo_numero}: {resposta.status_code} - {resposta.text}")
                
            # Pequena pausa entre mensagens
            time.sleep(1)
            
        except requests.exceptions.Timeout:
            log_error(f"Timeout ao enviar parte {grupo_numero} para Discord")
        except requests.exceptions.ConnectionError:
            log_error(f"Erro de conexão ao enviar parte {grupo_numero} para Discord")
        except Exception as e:
            log_error(f"Erro inesperado ao enviar parte {grupo_numero}: {e}")
    
    log_success(f"Processo de envio concluído! {len(vagas)} vagas enviadas em {total_grupos} mensagens")

# ===========================
# 🧠 FUNÇÃO PRINCIPAL
# ===========================
def main():
    """Função principal que orquestra toda a busca de vagas"""
    log_info("🚀 Iniciando busca de vagas automatizada...")
    log_info("=" * 50)
    
    # Valida configurações essenciais
    if not DISCORD_WEBHOOK_URL:
        log_error("DISCORD_WEBHOOK_URL não configurada no arquivo .env!")
        return False
    
    # Registra início da execução
    inicio_execucao = datetime.now()
    log_info(f"📍 Local da busca: {LOCAL}")
    log_info(f"⏰ Início: {inicio_execucao.strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Busca vagas com tratamento de erro
    log_info("🔍 Iniciando buscas nas plataformas...")
    
    vagas_indeed = buscar_vagas_com_tentativas(buscar_vagas_indeed, "Indeed")
    vagas_glassdoor = buscar_vagas_com_tentativas(buscar_vagas_glassdoor, "Glassdoor")  # SUBSTITUÍDO
    
    # Combina resultados
    todas_vagas = vagas_indeed + vagas_glassdoor  # ATUALIZADO
    
    if not todas_vagas:
        log_info("📭 Nenhuma vaga encontrada em nenhuma plataforma")
        enviar_discord([])  # Envia mensagem de "nenhuma vaga"
        return True
    
    # Remove duplicatas
    log_info("🔄 Removendo vagas duplicadas...")
    vagas_unicas = []
    titulos_vistos = set()
    
    for vaga in todas_vagas:
        try:
            # Extrai e normaliza o título
            titulo = vaga.split('\n')[0]
            titulo_normalizado = normalizar_titulo(titulo)
            
            if titulo_normalizado not in titulos_vistos:
                vagas_unicas.append(vaga)
                titulos_vistos.add(titulo_normalizado)
                log_debug(f"Vaga única adicionada: {titulo_normalizado}")
            else:
                log_debug(f"Vaga duplicada removida: {titulo_normalizado}")
                
        except Exception as e:
            log_error(f"Erro ao processar vaga para remoção de duplicatas: {e}")
            continue
    
    # Estatísticas finais
    fim_execucao = datetime.now()
    tempo_execucao = (fim_execucao - inicio_execucao).total_seconds()
    
    log_info("=" * 50)
    log_info("📊 ESTATÍSTICAS DA BUSCA:")
    log_info(f"   • Indeed: {len(vagas_indeed)} vagas")
    log_info(f"   • Glassdoor: {len(vagas_glassdoor)} vagas")  # ATUALIZADO
    log_info(f"   • Total bruto: {len(todas_vagas)} vagas")
    log_info(f"   • Total único: {len(vagas_unicas)} vagas")
    log_info(f"   • Tempo de execução: {tempo_execucao:.2f} segundos")
    log_info("=" * 50)
    
    # Envia para Discord
    log_info("📤 Enviando vagas para o Discord...")
    enviar_discord(vagas_unicas)
    
    log_success("🏁 Busca concluída com sucesso!")
    return True

# ===========================
# 🚀 MAIN AUTOMATIZADA
# ===========================

def main_automatizada(historico_vagas=None):
    """Versão da main para execução automatizada que retorna vagas novas"""
    if historico_vagas is None:
        historico_vagas = set()
    
    log_info("🤖 Execução automatizada iniciada...")
    
    # Valida configurações essenciais
    if not DISCORD_WEBHOOK_URL:
        log_error("DISCORD_WEBHOOK_URL não configurada!")
        return set()
    
    # Busca vagas
    vagas_indeed = buscar_vagas_com_tentativas(buscar_vagas_indeed, "Indeed")
    vagas_glassdoor = buscar_vagas_com_tentativas(buscar_vagas_glassdoor, "Glassdoor")
    
    # Combina resultados
    todas_vagas = vagas_indeed + vagas_glassdoor
    
    if not todas_vagas:
        log_info("📭 Nenhuma vaga encontrada")
        enviar_discord([])
        return set()
    
    # Filtra vagas novas
    vagas_novas = []
    for vaga in todas_vagas:
        # Cria um hash simples da vaga para comparação
        vaga_hash = hash(vaga.split('\n')[0])  # Hash do título
        
        if vaga_hash not in historico_vagas:
            vagas_novas.append(vaga)
            historico_vagas.add(vaga_hash)
    
    # Envia apenas vagas novas para o Discord
    if vagas_novas:
        log_info(f"🎯 {len(vagas_novas)} vagas NOVAS encontradas!")
        enviar_discord(vagas_novas)
    else:
        log_info("🔄 Nenhuma vaga nova encontrada")
        # Opcional: enviar mensagem de "sem novidades" a cada 12 execuções
        if len(historico_vagas) > 0 and random.random() < 0.08:  # ~8% de chance
            enviar_discord(["🔍 Nenhuma vaga nova encontrada na última verificação. O bot continua monitorando..."])
    
    return set([hash(vaga.split('\n')[0]) for vaga in vagas_novas])

def obter_proximo_horario_otimizado():
    """Retorna horários otimizados para busca baseado em padrões"""
    agora = datetime.now()
    hora = agora.hour
    
    # Horários preferenciais (maior chance de vagas frescas)
    horarios_otimizados = [
        9, 10, 11,    # Manhã - início do expediente
        14, 15, 16,   # Tarde - após almoço
        17, 18        # Final da tarde - fechamento
    ]
    
    # Encontra o próximo horário ideal
    for horario in horarios_otimizados:
        if hora < horario:
            return horario
    
    # Se passou todos, usa o primeiro do próximo dia
    return horarios_otimizados[0]

# ===========================
#  AGENDAMENTO INTELIGENTE
# ===========================

def executar_com_agendamento_inteligente():
    """Executa com agendamento baseado em horários otimizados"""
    log_info("🧠 Modo agendamento inteligente ativado")
    
    historico_vagas = set()
    contador_execucoes = 0
    
    while True:
        try:
            contador_execucoes += 1
            proximo_horario = obter_proximo_horario_otimizado()
            agora = datetime.now()
            
            # Calcula segundos até o próximo horário
            if agora.hour < proximo_horario:
                # Executa hoje
                proxima_execucao = agora.replace(hour=proximo_horario, minute=0, second=0, microsecond=0)
            else:
                # Executa amanhã
                amanha = agora + timedelta(days=1)
                proxima_execucao = amanha.replace(hour=proximo_horario, minute=0, second=0, microsecond=0)
            
            segundos_espera = (proxima_execucao - agora).total_seconds()
            
            log_info(f"🔄 Execução #{contador_execucoes} agendada para: {proxima_execucao.strftime('%d/%m/%Y %H:%M')}")
            log_info(f"⏰ Aguardando {segundos_espera/3600:.1f} horas...")
            
            # Aguarda até o horário agendado (com verificações periódicas)
            while segundos_espera > 0:
                # Verifica a cada 30min se não foi interrompido
                tempo_espera = min(1800, segundos_espera)  # Máximo 30min
                time.sleep(tempo_espera)
                segundos_espera -= tempo_espera
                
                if segundos_espera > 0:
                    log_debug(f"⏳ Faltam {segundos_espera/60:.0f} minutos...")
            
            # Executa a busca
            log_info("🎯 Iniciando busca agendada...")
            novas_vagas = main_automatizada(historico_vagas)
            historico_vagas.update(novas_vagas)
            
        except KeyboardInterrupt:
            log_info("🛑 Execução interrompida pelo usuário")
            break
        except Exception as e:
            log_error(f"💥 Erro no agendamento: {e}")
            time.sleep(300)  # 5min em caso de erro
            
# ===========================
# 🔄 EXECUÇÃO CONTÍNUA
# ===========================
def executar_continuamente():
    """Executa o bot em intervalos regulares de forma inteligente"""
    log_info("🔄 Modo de execução contínua ativado")
    log_info(f"⏰ Intervalo entre buscas: {INTERVALO_BUSCA_MINUTOS} minutos")
    
    contador_execucoes = 0
    historico_vagas = set()  # Para evitar duplicatas entre execuções
    
    while True:
        try:
            contador_execucoes += 1
            log_info(f"🔄 Execução #{contador_execucoes}")
            log_info("-" * 50)
            
            # Horário inteligente - evita horários de pico
            agora = datetime.now()
            hora_atual = agora.hour
            
            # Não executa entre 2h e 6h (menor tráfego)
            if 2 <= hora_atual <= 6:
                espera_ate = 7 - hora_atual
                log_info(f"🌙 Modo noturno: aguardando até 7h ({espera_ate}h)")
                time.sleep(espera_ate * 3600)
                continue
            
            # Executa a busca principal
            vagas_novas = main_automatizada(historico_vagas)
            
            # Atualiza histórico
            historico_vagas.update(vagas_novas)
            
            # Calcula próximo horário de execução com variação aleatória
            variacao = random.randint(-10, 10)  # ±10 minutos
            intervalo_com_variacao = max(30, INTERVALO_BUSCA_MINUTOS + variacao)  # Mínimo 30min
            
            proxima_execucao = datetime.now().timestamp() + (intervalo_com_variacao * 60)
            proxima_str = datetime.fromtimestamp(proxima_execucao).strftime('%d/%m/%Y %H:%M:%S')
            
            log_info(f"✅ Execução #{contador_execucoes} concluída")
            log_info(f"📊 Vagas novas encontradas: {len(vagas_novas)}")
            log_info(f"⏰ Próxima execução: {proxima_str} ({intervalo_com_variacao}min)")
            log_info("=" * 50)
            
            # Aguarda intervalo
            time.sleep(intervalo_com_variacao * 60)
            
        except KeyboardInterrupt:
            log_info("🛑 Execução interrompida pelo usuário")
            break
            
        except Exception as e:
            log_error(f"💥 Erro crítico na execução: {e}")
            log_info("💤 Aguardando 10 minutos antes de tentar novamente...")
            time.sleep(600)  # 10 minutos em caso de erro crítico

# ===========================
# 🚀 PONTO DE INÍCIO
# ===========================
if __name__ == "__main__":
    """
    Modos de execução:
    - python bot_vagas.py                      (execução única)
    - python bot_vagas.py --continuous         (execução contínua) ← AGORA FUNCIONA
    - python bot_vagas.py --scheduled          (agendamento inteligente)
    - python bot_vagas.py --test               (modo teste)
    """
    
    # Configura logging
    setup_logging()
    
    # Verifica argumentos
    import sys
    args = sys.argv[1:]
    
    try:
        if "--test" in args or "-t" in args:
            log_info("🧪 Modo teste ativado")
            # Testa apenas uma plataforma rapidamente
            test_vagas = buscar_vagas_com_tentativas(buscar_vagas_indeed, "Indeed TESTE")
            log_info(f"🧪 Resultado teste: {len(test_vagas)} vagas")
            
        elif "--scheduled" in args or "-s" in args:
            log_info("🧠 Iniciando Bot com Agendamento Inteligente")
            executar_com_agendamento_inteligente()
            
        elif "--continuous" in args or "-c" in args:
            log_info("🔄 Iniciando Bot em Modo Contínuo")
            executar_continuamente()  # ← CHAMA A FUNÇÃO DE EXECUÇÃO CONTÍNUA
            
        else:
            log_info("🎯 Iniciando Busca Única")
            main()
            
    except KeyboardInterrupt:
        log_info("👋 Execução interrompida pelo usuário")
        
    except Exception as e:
        log_error(f"💥 Erro fatal: {e}")
        
    finally:
        log_info("🏁 Script finalizado")