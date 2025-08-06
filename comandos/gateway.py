import modules.manager as manager
import modules.payment as payment
import json, re, requests
import modules.payment as payment

config = json.loads(open('./config.json', 'r').read())

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater, CallbackContext, ChatJoinRequestHandler
from telegram.error import BadRequest, Conflict

from modules.utils import process_command, is_admin, error_callback, error_message, cancel, escape_markdown_v2

GATEWAY_RECEBER, GATEWAY_ESCOLHA = range(2)

#comando adeus
async def gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    planos = manager.get_bot_plans(context.bot_data['id'])
    if not command_check:
        return ConversationHandler.END
    if not await is_admin(context, update.message.from_user.id):
        
        return ConversationHandler.END
    context.user_data['conv_state'] = "gateway"

    keyboard = [
            [InlineKeyboardButton("Mercado Pago", callback_data="mp"), InlineKeyboardButton("Pushinpay", callback_data="push")],
            [InlineKeyboardButton("PagHiper", callback_data="paghiper")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔐 Qual gateway deseja adicionar?\n\n"
        ">𝗖𝗼𝗺𝗼 𝗳𝘂𝗻𝗰𝗶𝗼𝗻𝗮\\? Conecte seu bot com Mercado Pago, PushinPay ou PagHiper para processar pagamentos\\.",
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )
    return GATEWAY_ESCOLHA

async def gateway_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    elif query.data == 'mp':
        # Constrói a URL
        mp_url = f"https://auth.mercadopago.com/authorization?client_id={config['client_id']}&response_type=code&platform_id=mp&state={context.bot_data['id']}&redirect_url={config['url']}/callback"
        
        # Cria o botão com o link
        keyboard = [[InlineKeyboardButton("🔗 Conectar Mercado Pago", url=mp_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "🔒 Clique no botão abaixo para vincular seu Mercado Pago.", 
            reply_markup=reply_markup
        )
        
        context.user_data['conv_state'] = False
        return ConversationHandler.END
    elif query.data == 'push':
        keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)        
        await query.message.edit_text("🔒 Envie o token da PushinPay.", reply_markup=reply_markup)
        context.user_data['gateway_type'] = 'pp'  # Marca o tipo
        return GATEWAY_RECEBER
    elif query.data == 'paghiper':
        keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)        
        await query.message.edit_text("🔒 Envie a API Key do PagHiper.", reply_markup=reply_markup)
        context.user_data['gateway_type'] = 'paghiper'  # Marca o tipo
        return GATEWAY_RECEBER
    
async def recebe_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token_recebido = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not update.message.text:
        await update.message.reply_text(text=f"⛔ Token/API Key inválido, por favor envie um válido")
        return GATEWAY_RECEBER
    
    # Verifica qual gateway está sendo configurado
    gateway_type = context.user_data.get('gateway_type', 'pp')
    
    if gateway_type == 'paghiper':
        # Validação para PagHiper
        if not token_recebido.startswith('apk_'):
            await update.message.reply_text(
                "❌ API Key inválida\\! A API Key do PagHiper deve começar com 'apk\\_'\n\n"
                ">Exemplo\\: apk\\_12345678\\-OqCWOKczcjutZaFRSfTlVBDpHFXpkdzz",
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
            return GATEWAY_RECEBER
        
        if not payment.verificar_paghiper(token_recebido):
            await update.message.reply_text(
                "❌ API Key inválida ou sem permissões\\!\n\n"
                "Verifique se a API Key está correta e ativa no PagHiper\\.",
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
            return GATEWAY_RECEBER
        
        manager.update_bot_gateway(context.bot_data['id'], {'type':'paghiper', 'token':token_recebido})
        await update.message.reply_text(text=f"✅ Gateway PagHiper configurado com sucesso!")
    else:
        # Código original para PushinPay
        if not payment.verificar_push(token_recebido):
            await update.message.reply_text(
                "❌ Token inválido\\! O Token deve ser nesse formato ⬋\n\n"
                ">36498\\|kMLGkibg5Z2D1Ap8hyvabkYsf5emCcREMpRMkTPa2c802374",
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
            return GATEWAY_RECEBER
        
        manager.update_bot_gateway(context.bot_data['id'], {'type':'pp', 'token':token_recebido})
        await update.message.reply_text(text=f"✅ Gateway PushinPay configurado com sucesso!")
    
    context.user_data['conv_state'] = False
    context.user_data.pop('gateway_type', None)  # Limpa o tipo de gateway
    return ConversationHandler.END
