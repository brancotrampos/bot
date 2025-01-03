from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def health_check():
    return "Bot is running!", 200

def run_web_server():
    app.run(host="0.0.0.0", port=5000)

# Inicie o servidor em uma thread separada
if __name__ == "__main__":
    threading.Thread(target=run_web_server).start()

    # Aqui você inicia o bot
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import time
import threading

# Configurações iniciais
TOKEN = '8024871819:AAH4EQn26Ge_eqz7Ww2UQWnU-LIjbk29s6k'
ADMIN_ID = 6397013648

bot = telebot.TeleBot(TOKEN)

# Dados simulados para armazenamento
try:
    with open("dados.json", "r") as f:
        dados = json.load(f)
except FileNotFoundError:
    dados = {"grupos": {}, "mensagens": {}, "intervalo": 60, "mensagem_atual": None}

# Dicionário para rastrear estados do chat
estados = {}

# Funções auxiliares
def salvar_dados():
    """Salva os dados no arquivo JSON."""
    with open("dados.json", "w") as f:
        json.dump(dados, f, indent=4)

def eh_admin(user_id):
    """Verifica se o usuário é o administrador."""
    return user_id == ADMIN_ID

# Função para envio contínuo de mensagens
def enviar_mensagens_periodicamente():
    """Envia mensagens para os grupos cadastrados em intervalos configurados."""
    while True:
        try:
            if dados["mensagem_atual"]:
                grupos = [g_id for g_id, info in dados["grupos"].items() if info["ativo"]]
                if grupos:
                    for grupo_id in grupos:
                        try:
                            bot.copy_message(
                                chat_id=grupo_id,
                                from_chat_id=dados["mensagem_atual"]["chat_id"],
                                message_id=dados["mensagem_atual"]["message_id"]
                            )
                        except Exception as e:
                            print(f"Erro ao enviar mensagem para o grupo {grupo_id}: {e}")
                    time.sleep(dados.get("intervalo", 60))
                else:
                    print("Nenhum grupo ativo para envio.")
                    time.sleep(5)  # Aguarda antes de verificar novamente
            else:
                print("Nenhuma mensagem configurada para envio.")
                time.sleep(5)  # Aguarda antes de verificar novamente
        except Exception as e:
            print(f"Erro na execução do envio periódico: {e}")
            time.sleep(5)  # Evita travar o loop em caso de erro


# Inicia a thread para envio periódico de mensagens
threading.Thread(target=enviar_mensagens_periodicamente, daemon=True).start()

# Funções do painel
@bot.message_handler(commands=['menu'])
def start(message):
    """Inicia o painel de administração."""
    if not eh_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "\U0001F916 Bem-vindo ao painel de administração!\n\nEscolha uma opção:",
        reply_markup=menu_principal()
    )

def menu_principal():
    """Cria o menu principal do bot."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("\U0001F4DA Gerenciar Grupos", callback_data="gerenciar_grupos"))
    markup.add(InlineKeyboardButton("\U0001F4AC Configurar Mensagens", callback_data="configurar_mensagens"))
    markup.add(InlineKeyboardButton("\U0001F55C Configurar Intervalo", callback_data="configurar_intervalo"))
    markup.add(InlineKeyboardButton("🔙 Voltar", callback_data="voltar_menu"))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Lida com os botões do painel de administração."""
    if not eh_admin(call.from_user.id):
        return

    if call.data == "gerenciar_grupos":
        gerenciar_grupos(call.message.chat.id, call.message.message_id)
    elif call.data == "ativar_todos":
        toggle_todos_grupos(True, call.message.chat.id, call.message.message_id)
    elif call.data == "desativar_todos":
        toggle_todos_grupos(False, call.message.chat.id, call.message.message_id)
    elif call.data.startswith("grupo_"):
        grupo_id = call.data.split("_")[1]
        exibir_detalhes_grupo(call.message.chat.id, call.message.message_id, grupo_id)
    elif call.data.startswith("ativar_"):
        grupo_id = call.data.split("_")[1]
        toggle_ativo(grupo_id, True, call.message.chat.id, call.message.message_id)
    elif call.data.startswith("desativar_"):
        grupo_id = call.data.split("_")[1]
        toggle_ativo(grupo_id, False, call.message.chat.id, call.message.message_id)
    elif call.data.startswith("excluir_"):
        grupo_id = call.data.split("_")[1]
        excluir_grupo(grupo_id, call.message.chat.id, call.message.message_id)
    elif call.data == "configurar_mensagens":
        solicitar_mensagem(call.message.chat.id)
    elif call.data == "configurar_intervalo":
        solicitar_intervalo(call.message.chat.id)
    elif call.data == "voltar_menu":
        bot.edit_message_text(
            "\U0001F916 Bem-vindo ao painel de administração!\n\nEscolha uma opção:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=menu_principal()
        )

def gerenciar_grupos(chat_id, message_id):
    """Exibe a lista de grupos cadastrados."""
    grupos = dados["grupos"]
    if not grupos:
        texto = "\U0001F614 Nenhum grupo cadastrado."
        bot.edit_message_text(texto, chat_id, message_id, reply_markup=menu_principal())
        return

    texto = "\U0001F4DA Grupos cadastrados:\n\n"
    markup = InlineKeyboardMarkup()
    
    # Botões para ativar/desativar todos os grupos
    markup.add(InlineKeyboardButton("✅ Ativar Todos", callback_data="ativar_todos"))
    markup.add(InlineKeyboardButton("❌ Desativar Todos", callback_data="desativar_todos"))
    
    for grupo_id, grupo_info in grupos.items():
        texto += f"🔹 <b>{grupo_info['nome']}</b>\n🆔 ID: {grupo_id}\n\n"
        markup.add(InlineKeyboardButton(grupo_info['nome'], callback_data=f"grupo_{grupo_id}"))
    
    markup.add(InlineKeyboardButton("🔙 Voltar", callback_data="voltar_menu"))

    bot.edit_message_text(texto, chat_id, message_id, reply_markup=markup, parse_mode="HTML")

def exibir_detalhes_grupo(chat_id, message_id, grupo_id):
    """Exibe os detalhes de um grupo específico."""
    grupo = dados["grupos"].get(grupo_id)
    if not grupo:
        bot.send_message(chat_id, "❌ Erro: Grupo não encontrado.")
        return

    texto = (f"\U0001F4DA <b>Detalhes do Grupo:</b>\n\n"
             f"🆔 <b>ID:</b> {grupo_id}\n"
             f"📛 <b>Nome:</b> {grupo['nome']}\n"
             f"👥 <b>Quantidade de Membros:</b> {grupo.get('membros', 'N/A')}\n"
             f"🔵 <b>Status:</b> {'✅ Ativo' if grupo['ativo'] else '❌ Inativo'}")

    markup = InlineKeyboardMarkup()
    if grupo["ativo"]:
        markup.add(InlineKeyboardButton("❌ Desativar", callback_data=f"desativar_{grupo_id}"))
    else:
        markup.add(InlineKeyboardButton("✅ Ativar", callback_data=f"ativar_{grupo_id}"))
    markup.add(InlineKeyboardButton("🗑️ Excluir", callback_data=f"excluir_{grupo_id}"))
    markup.add(InlineKeyboardButton("🔙 Voltar", callback_data="gerenciar_grupos"))

    bot.edit_message_text(texto, chat_id, message_id, reply_markup=markup, parse_mode="HTML")

def toggle_ativo(grupo_id, ativo, chat_id, message_id):
    """Ativa ou desativa o grupo."""
    if grupo_id in dados["grupos"]:
        dados["grupos"][grupo_id]["ativo"] = ativo
        salvar_dados()
        exibir_detalhes_grupo(chat_id, message_id, grupo_id)
    else:
        bot.send_message(chat_id, "❌ Erro: Grupo não encontrado.")

def toggle_todos_grupos(ativo, chat_id, message_id):
    """Ativa ou desativa todos os grupos."""
    for grupo_id in dados["grupos"]:
        dados["grupos"][grupo_id]["ativo"] = ativo
    salvar_dados()
    gerenciar_grupos(chat_id, message_id)  # Atualiza a lista de grupos após a mudança

def excluir_grupo(grupo_id, chat_id, message_id):
    """Remove o bot do grupo e exclui seus dados."""
    if grupo_id in dados["grupos"]:
        try:
            bot.leave_chat(grupo_id)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Erro ao sair do grupo: {e}")

        del dados["grupos"][grupo_id]
        salvar_dados()
        bot.send_message(chat_id, "🗑️ Grupo excluído com sucesso!")
        gerenciar_grupos(chat_id, message_id)
    else:
        bot.send_message(chat_id, "❌ Erro: Grupo não encontrado.")



@bot.my_chat_member_handler()
def ao_ser_adicionado(membro):
    """Detecta quando o bot é adicionado a um grupo."""
    if membro.new_chat_member.status == "member":
        grupo_id = membro.chat.id
        nome_grupo = membro.chat.title
        dados["grupos"][str(grupo_id)] = {"nome": nome_grupo, "ativo": False, "membros": None}
        salvar_dados()
        bot.send_message(ADMIN_ID, f"➕ O bot foi adicionado ao grupo <b>{nome_grupo}</b> (ID: {grupo_id}).", parse_mode="HTML")

def solicitar_mensagem(chat_id):
    """Solicita que o administrador encaminhe uma mensagem para configurar."""
    bot.send_message(chat_id, "Encaminhe a mensagem que deseja configurar para envio contínuo:")
    estados[chat_id] = "configurando_mensagem"

def solicitar_intervalo(chat_id):
    """Solicita que o administrador envie o intervalo em segundos."""
    bot.send_message(chat_id, "Envie o intervalo desejado (em segundos) para as mensagens de divulgação:")
    estados[chat_id] = "configurando_intervalo"

@bot.message_handler(func=lambda message: True)
def definir_mensagem_ou_intervalo(message):
    """Lida com mensagens para configurar intervalo ou mensagem contínua."""
    if not eh_admin(message.from_user.id):
        return

    estado_atual = estados.get(message.chat.id)

    if estado_atual == "configurando_intervalo":
        # Verifica se a mensagem é um número
        if message.text.isdigit():
            intervalo = int(message.text)
            if intervalo < 10:
                bot.reply_to(message, "O intervalo deve ser de no mínimo 10 segundos.")
                return

            dados["intervalo"] = intervalo
            salvar_dados()
            bot.reply_to(message, f"Intervalo definido para {intervalo} segundos com sucesso! \u2705")
            estados.pop(message.chat.id, None)
        else:
            bot.reply_to(message, "Por favor, envie apenas números para configurar o intervalo.")
        return

    if estado_atual == "configurando_mensagem":
        # Configura a mensagem para envio contínuo
        dados["mensagem_atual"] = {"chat_id": message.chat.id, "message_id": message.message_id}
        salvar_dados()
        bot.reply_to(message, "Mensagem configurada com sucesso para envio contínuo! \u2705")
        estados.pop(message.chat.id, None)
        return

    # Mensagem fora de qualquer estado configurado
    bot.reply_to(message, "Não entendi sua mensagem. Por favor, escolha uma opção no menu.")

# Iniciar o bot
print("Bot iniciado...")
bot.polling(none_stop=True)
