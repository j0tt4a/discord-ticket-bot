import discord
from discord.ext import commands
from discord import app_commands
import io
import datetime
import random

# ================== CONFIG ==================
TOKEN = "TU_TOKEN"  # ← Railway lo pone aquí
GUILD_ID = 1465457571245719749         # ID del servidor
VERIFY_CHANNEL_ID = 1466008444937965742  # Canal donde va el mensaje de verificación
REPORTS_CHANNEL_ID = 1466011823538176090 # Canal "Reportes o Dudas"
VERIFY_TRANSCRIPTS_CHANNEL_ID = 1468763263423484019  # CAMBIA ESTE ID: Canal para transcripts de verificación
REPORT_TRANSCRIPTS_CHANNEL_ID = 1466056850930794784 # CAMBIA ESTE ID: Canal para transcripts de reportes/dudas

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)


# ================ VISTAS / BOTONES =================

class VerifyTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📷 FOTOGRAFÍA", style=discord.ButtonStyle.blurple, custom_id="verify_photo")
    async def verify_photo(self, interaction: discord.Interaction, button: discord.ui.Button):
        codigo = str(random.randint(100000, 999999))
        await create_ticket(
            interaction,
            tipo="verificacion-foto",
            titulo="Ticket de verificación (Foto)",
            descripcion=f"""# 📷 | HAS ESCOGIDO VERIFICARTE POR FOTO:
✅ | Para verificarte, tienes que pasar una **FOTO TUYA** donde **SE TE VEA** lo mejor posible, **CON EL SIGUIENTE CODIGO ESCRITO EN UN PAPEL:**
**`{codigo}`**
- Y dime como quieres el dm (abierto, q te pregunten, o cerrado); abierto significa que pueden abrirte directamente, que te pregunten significa que antes de abrirte pues te pregunten, y cerrado es q no quieres q te abran. Y tu color fav? ⭐""",
            categoria="verificacion",
            codigo_verificacion=codigo
        )

    @discord.ui.button(label="📱 VIDEO", style=discord.ButtonStyle.blurple, custom_id="verify_video")
    async def verify_video(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(
            interaction,
            tipo="verificacion-video",
            titulo="Ticket de verificación (Video)",
            descripcion="""# 📱| HAS ESCOGIDO VERIFICARTE POR VIDEO:
✅ | Para verificarte, tienes que pasar un **VIDEO TUYO** donde **SE TE VEA** lo mejor posible, **Y SALGAS DICIENDO:**
**"Hola Quesito's, soy (tu nombre), y esta es mi verificacion."**
- Y dime como quieres el dm (abierto, q te pregunten, o cerrado); abierto significa que pueden abrirte directamente, que te pregunten significa que antes de abrirte pues te pregunten, y cerrado es q no quieres q te abran. Y tu color fav? ⭐""",
            categoria="verificacion"
        )


class ReportTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reportes", style=discord.ButtonStyle.danger, custom_id="report_button")
    async def report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(
            interaction,
            tipo="reporte",
            titulo="Ticket de reporte",
            descripcion="Describe tu **reporte** con el máximo detalle posible.",
            categoria="reportes"
        )

    @discord.ui.button(label="Dudas", style=discord.ButtonStyle.success, custom_id="duda_button")
    async def duda_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(
            interaction,
            tipo="duda",
            titulo="Ticket de dudas",
            descripcion="Explica tu **duda** para que el staff pueda ayudarte.",
            categoria="reportes"
        )


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar y transcript", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not hasattr(interaction.channel, "topic") or interaction.channel.topic is None:
            await interaction.response.send_message("Este canal no parece ser un ticket válido.", ephemeral=True)
            return

        opener_id = None
        categoria = None
        if interaction.channel.topic.startswith("ticket_owner:"):
            parts = interaction.channel.topic.split("|")
            try:
                opener_id = int(parts[0].split(":")[1])
                if len(parts) > 1:
                    categoria = parts[1].strip()
            except:
                pass

        if interaction.user.id != opener_id and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("No tienes permiso para cerrar este ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await send_transcript_and_delete(interaction.channel, interaction.user, categoria)


# ================= FUNCIONES AUXILIARES =================

async def get_ticket_category(guild: discord.Guild, categoria: str = "verificacion") -> discord.CategoryChannel:
    if categoria == "verificacion":
        cat_name = "🎫 - 𝗭𝗼𝗻𝗮 𝗧𝗶𝗰𝗸𝗲𝘁𝘀 (𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝗰𝗶𝗼𝗻)"
    else:  # reportes
        cat_name = "🎟️ - 𝗭𝗼𝗻𝗮 𝗧𝗶𝗰𝗸𝗲𝘁𝘀 (𝗦𝗼𝗽𝗼𝗿𝘁𝗲)"
    
    category = discord.utils.get(guild.categories, name=cat_name)
    if category is None:
        category = await guild.create_category(cat_name)
    return category


async def create_ticket(interaction: discord.Interaction, tipo: str, titulo: str, descripcion: str, categoria: str = "verificacion", codigo_verificacion: str = None):
    guild = interaction.guild
    category = await get_ticket_category(guild, categoria)

    existing = [c for c in category.text_channels if c.name.startswith(tipo)]
    num = len(existing) + 1
    channel_name = f"{tipo}-{num}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    topic = f"ticket_owner:{interaction.user.id}"
    if categoria:
        topic += f"|{categoria}"
    if codigo_verificacion:
        topic += f"|codigo:{codigo_verificacion}"

    channel = await guild.create_text_channel(
        channel_name,
        category=category,
        overwrites=overwrites,
        topic=topic
    )

    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Información",
        value=f"{interaction.user.mention}, el staff te atenderá en breve.\n"
              f"Cuando termine la atención, pulsa el botón para **cerrar el ticket** y generar la **transcripción**."
    )

    view = TicketControlView()
    await channel.send(content=interaction.user.mention, embed=embed, view=view)
    await interaction.response.send_message(f"Tu ticket ha sido creado: {channel.mention}", ephemeral=True)


async def send_transcript_and_delete(channel: discord.TextChannel, closed_by: discord.User, categoria: str = None):
    # Obtenemos mensajes del canal
    messages = [message async for message in channel.history(oldest_first=True, limit=2000)]

    # Creamos contenido de transcript
    lines = []
    lines.append(f"═══════════════════════════════════════")
    lines.append(f"Servidor: {channel.guild.name} (ID: {channel.guild.id})")
    lines.append(f"Canal: {channel.name} (ID: {channel.id})")
    lines.append(f"Tipo: {categoria or 'desconocido'}")
    lines.append(f"Cerrado por: {closed_by} (ID: {closed_by.id})")
    lines.append(f"Fecha cierre: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append(f"═══════════════════════════════════════")
    lines.append("")

    for msg in messages:
        time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        content = msg.content.replace("\n", "\\n") if msg.content else "(sin texto)"
        lines.append(f"[{time_str}] {msg.author} (ID:{msg.author.id}): {content}")
        if msg.attachments:
            for attachment in msg.attachments:
                lines.append(f"    📎 {attachment.filename}: {attachment.url}")

    transcript_text = "\n".join(lines)
    
    # Crear archivo
    file = discord.File(io.BytesIO(transcript_text.encode("utf-8")), filename=f"transcript-{channel.name}.txt")

    # Enviar a canal correspondiente
    transcript_channel = None
    if categoria == "verificacion":
        transcript_channel = bot.get_channel(VERIFY_TRANSCRIPTS_CHANNEL_ID)
    elif categoria in ["reportes", "duda"]:
        transcript_channel = bot.get_channel(REPORT_TRANSCRIPTS_CHANNEL_ID)

    if transcript_channel:
        embed = discord.Embed(
            title=f"📋 Transcripción - {channel.name}",
            description=f"Ticket cerrado por {closed_by.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Categoría", value=categoria, inline=True)
        await transcript_channel.send(embed=embed, file=file)
    
    # También enviar DM al que cerró (opcional)
    try:
        await closed_by.send(f"✅ Transcripción del ticket `{channel.name}` guardada correctamente.", file=file)
    except:
        pass

    await channel.delete(reason=f"Ticket cerrado por {closed_by}")


# ================== EVENTOS ==================

@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    except Exception as e:
        print(f"Error al sync commands: {e}")

    bot.add_view(VerifyTicketView())
    bot.add_view(ReportTicketView())
    bot.add_view(TicketControlView())


# ================ COMANDOS DE CONFIGURACIÓN =================

@bot.tree.command(name="setup_verificacion", description="Enviar mensaje de verificación con tickets.")
@app_commands.checks.has_permissions(manage_channels=True)
async def setup_verificacion(interaction: discord.Interaction):
    if interaction.channel_id != VERIFY_CHANNEL_ID:
        await interaction.response.send_message(
            "Este comando solo se puede usar en el canal de verificación configurado.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="✅ - 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝗰𝗶𝗼𝗻",
        description=(
            "Para poder verificarte y tener acceso a todos los canales del servidor, "
            "**DEBES CREAR TICKET** y escoger **UNA** de las opciones que te da al abrir el ticket.\n\n"
            "Dentro del ticket verás estas opciones:\n\n"
            "📷 | **FOTOGRAFIA**\n"
            "Si deseas verificarte con esta opción, selecciona el botón de fotografía.\n\n"
            "📱 | **VIDEO**\n"
            "Si deseas verificarte con esta opción, selecciona el botón de video."
        ),
        color=discord.Color.green()
    )

    view = VerifyTicketView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Mensaje de verificación enviado.", ephemeral=True)


@bot.tree.command(name="setup_reportes", description="Enviar mensaje de Reportes y Dudas con botones.")
@app_commands.checks.has_permissions(manage_channels=True)
async def setup_reportes(interaction: discord.Interaction):
    if interaction.channel_id != REPORTS_CHANNEL_ID:
        await interaction.response.send_message(
            "Este comando solo se puede usar en el canal de Reportes o Dudas configurado.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Soporte - Reportes y Dudas",
        description=(
            "Utiliza los botones de abajo para abrir un ticket.\n\n"
            "🔴 **Reportes**: Abre un ticket para reportar usuarios, situaciones, etc.\n"
            "🟢 **Dudas**: Abre un ticket para cualquier pregunta o ayuda que necesites."
        ),
        color=discord.Color.orange()
    )

    view = ReportTicketView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Mensaje de Reportes/Dudas enviado.", ephemeral=True)


# ================== ERRORES DE PERMISO ==================

@setup_verificacion.error
async def setup_verificacion_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("No tienes permiso para usar este comando.", ephemeral=True)


@setup_reportes.error
async def setup_reportes_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("No tienes permiso para usar este comando.", ephemeral=True)


# ================== ARRANCAR BOT ==================

bot.run(TOKEN)