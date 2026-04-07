import discord
from discord import app_commands
from discord.ext import commands
import requests
import google.generativeai as genai

# --- ตั้งค่าส่วนตัว ---
TOKEN = ''
GOOGLE_API_KEY = ''  # ใส่ API Key ของ Google Generative AI ของคุณตรงนี้
genai.configure(api_key=GOOGLE_API_KEY)

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.message_content = True

# ปรับเป็น 1.2 หรือ 1.5 (ยิ่งสูง ยิ่งสุ่มได้เกมแปลกๆ แต่ระวังมันมั่วชื่อเกมนะ)
config = genai.types.GenerationConfig(
    temperature=1.2, 
)

bot = commands.Bot(command_prefix='!', intents=intents)
# เลือกใช้รุ่น Flash เพราะตอบสนองเร็วและฟรี
model = genai.GenerativeModel('gemini-2.5-flash', generation_config=config)

@bot.event
async def on_ready():
    print(f'ล็อกอินสำเร็จ: {bot.user}')
    print('พร้อมใช้งาน! (อย่าลืมพิมพ์ !sync ในช่องแชทเพื่ออัปเดตคำสั่ง / นะครับ)')

# --- แก้ไขคำสั่ง Sync ให้เป็นแบบ "ทันที" (Guild Sync) ---
@bot.command()
async def sync(ctx):
    await ctx.send("กำลังอัปเดตคำสั่ง... (เฉพาะเซิร์ฟเวอร์นี้) ⏳")
    
    # 1. ก๊อปปี้คำสั่งทั้งหมดมาลงที่เซิร์ฟเวอร์นี้
    bot.tree.copy_global_to(guild=ctx.guild)
    
    # 2. สั่ง Sync ไปที่เซิร์ฟเวอร์นี้โดยเฉพาะ (ขึ้นทันที)
    try:
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Sync เรียบร้อย! คำสั่ง Slash {len(synced)} ตัว พร้อมใช้งานในห้องนี้แล้วครับ")
    except Exception as e:
        await ctx.send(f"❌ Sync ไม่ผ่าน: {e}")

@bot.command()
async def clearlocal(ctx):
    await ctx.send("กำลังลบคำสั่ง Local (เฉพาะห้องนี้) ออก... 🧹")
    
    # ล้างคำสั่งที่ผูกติดกับ Server นี้ออกให้หมด
    bot.tree.clear_commands(guild=ctx.guild)
    
    # Sync ไปที่ Server นี้เพื่อบอกว่า "ไม่มีคำสั่งเฉพาะแล้วนะ" (ให้ไปใช้ Global แทน)
    await bot.tree.sync(guild=ctx.guild)
    
    await ctx.send("✅ ลบ Local เรียบร้อย! ตอนนี้จะเหลือแต่ Global ครับ (อย่าลืมกด Ctrl+R)")

# ---------------------------------------------------------
# 1. คำสั่ง /sale : ดูเกมลดราคาหน้าแรก
# ---------------------------------------------------------
@bot.tree.command(name="sale", description="ดูรายการเกมลดราคาแนะนำ (Steam Specials)")
async def sale(interaction: discord.Interaction):
    await interaction.response.defer()

    url = "https://store.steampowered.com/api/featuredcategories?cc=th"
    try:
        response = requests.get(url)
        data = response.json()
        items = data.get('specials', {}).get('items', [])
        
        # 1. สร้างลิสต์เปล่าเอาไว้เก็บการ์ด
        embeds = [] 
        
        for game in items[:5]: # ดึงมา 5 เกม
            name = game.get('name')
            app_id = game.get('id')
            discount = game.get('discount_percent')
            original_price = game.get('original_price', 0) / 100 
            final_price = game.get('final_price', 0) / 100
            link = f"https://store.steampowered.com/app/{app_id}"
            
            # รูปปกเกม (Steam ใช้ format นี้เสมอ)
            image_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"

            if discount > 0:
                # 2. สร้างการ์ด (Embed)
                embed = discord.Embed(
                    title=f"🔥 {name}", 
                    url=link, 
                    color=discord.Color.red() # สีแดงสื่อถึงของร้อน/ลดราคา
                )
                
                # ใส่รายละเอียดราคา
                embed.description = (
                    f"ลด **{discount}%** 🏷️\n"
                    f"เหลือ **{final_price:,.0f} บาท** (จาก ~~{original_price:,.0f}~~)"
                )
                
                # ใส่รูปปกเกม
                embed.set_image(url=image_url)
                
                # เพิ่มการ์ดลงในลิสต์
                embeds.append(embed)
        
        # 3. ส่งการ์ดทั้งหมดออกไปทีเดียว (Discord ให้ส่งได้สูงสุด 10 ใบต่อข้อความ)
        if embeds:
            await interaction.followup.send(content="🔥 **แนะนำเกมลดราคา (Steam Specials)**", embeds=embeds)
        else:
            await interaction.followup.send("ตอนนี้หน้าแรกยังไม่มีรายการลดราคาเด่นๆ ครับ")

    except Exception as e:
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

# ---------------------------------------------------------
# 2. คำสั่ง /check : เช็คราคาเกม (คำนวณส่วนลดเอง)
# ---------------------------------------------------------
@bot.tree.command(name="check", description="เช็คราคาเกมจากชื่อ (ระบุชื่อเกม)")
@app_commands.describe(game_name="ชื่อเกมที่ต้องการเช็ค")
async def check(interaction: discord.Interaction, game_name: str):
    await interaction.response.defer()

    url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&cc=th&l=thai"

    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('total') == 0:
            await interaction.followup.send(f"❌ หาเกมชื่อ **{game_name}** ไม่เจอครับ")
            return

        items = data.get('items', [])
        if items:
            best_match = items[0]
            name = best_match.get('name')
            app_id = best_match.get('id')
            price_data = best_match.get('price')
            link = f"https://store.steampowered.com/app/{app_id}"

            if not price_data:
                 await interaction.followup.send(f"🎮 **{name}**\nเกมนี้ไม่มีราคา (Free/Pre-order)\n{link}")
                 return

            initial_val = price_data.get('initial', 0) or 0
            final_val = price_data.get('final', 0) or 0
            
            original_price = initial_val / 100
            final_price = final_val / 100

            # Logic คำนวณส่วนลดเอง
            if initial_val > final_val:
                calc_discount = int(((initial_val - final_val) / initial_val) * 100)
                msg = (
                    f"เจอแล้วครับ! 🔥 **{name}**\n"
                    f"ลด **{calc_discount}%** 🏷️ เหลือ **{final_price:,.0f} บาท** (จาก {original_price:,.0f})\n"
                    f"👉 {link}"
                )
            else:
                msg = (
                    f"เจอแล้วครับ! 🎮 **{name}** (ราคาปกติ)\n"
                    f"ราคา **{final_price:,.0f} บาท**\n"
                    f"👉 {link}"
                )
            await interaction.followup.send(msg)

    except Exception as e:
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

# ---------------------------------------------------------
# 3. คำสั่ง /top : ดู 10 อันดับขายดี
# ---------------------------------------------------------
@bot.tree.command(name="top", description="ดู 10 อันดับเกมขายดีในไทย")
async def top(interaction: discord.Interaction):
    await interaction.response.defer()
    
    url = "https://store.steampowered.com/api/featuredcategories?cc=th"
    
    try:
        response = requests.get(url)
        data = response.json()
        top_games = data.get('top_sellers', {}).get('items', [])
        
        if not top_games:
            await interaction.followup.send("ไม่สามารถดึงข้อมูล Top Sellers ได้ในขณะนี้")
            return

        msg = "🏆 **Top 10 เกมขายดีใน Steam (TH)** 🇹🇭\n"
        msg += "--------------------------------------\n"

        for index, game in enumerate(top_games[:10]):
            name = game.get('name')
            final_price = game.get('final_price', 0) / 100
            discount = game.get('discount_percent')
            
            if discount > 0:
                price_text = f"🔥 {final_price:,.0f} บาท (ลด {discount}%)"
            else:
                price_text = f"{final_price:,.0f} บาท"

            msg += f"**{index+1}. {name}** | {price_text}\n"

        await interaction.followup.send(msg)

    except Exception as e:
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

# ---------------------------------------------------------
# 4. คำสั่ง /online : เช็คคนเล่น
# ---------------------------------------------------------
@bot.tree.command(name="online", description="เช็คจำนวนคนเล่นปัจจุบัน (ระบุชื่อเกม)")
@app_commands.describe(game_name="ชื่อเกมที่ต้องการเช็ค")
async def online(interaction: discord.Interaction, game_name: str):
    await interaction.response.defer()

    search_url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&cc=th&l=thai"
    
    try:
        # Step 1: หา ID
        search_res = requests.get(search_url)
        search_data = search_res.json()
        
        if search_data.get('total') == 0:
            await interaction.followup.send(f"❌ หาเกมชื่อ **{game_name}** ไม่เจอครับ")
            return

        best_match = search_data.get('items')[0]
        app_id = best_match.get('id')
        real_name = best_match.get('name')

        # Step 2: เช็คคนเล่น
        stats_url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={app_id}"
        stats_res = requests.get(stats_url)
        stats_data = stats_res.json()
        
        player_count = stats_data.get('response', {}).get('player_count')

        if player_count is not None:
            msg = (
                f"🎮 **{real_name}**\n"
                f"👥 คนเล่นตอนนี้: **{player_count:,} คน**\n"
                f"👉 https://store.steampowered.com/app/{app_id}"
            )
            await interaction.followup.send(msg)
        else:
            await interaction.followup.send(f"เจอเกม **{real_name}** แต่ดึงข้อมูลคนเล่นไม่ได้ครับ")

    except Exception as e:
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

# ---------------------------------------------------------
# คำสั่ง /askgame : ให้ AI แนะนำเกม
# ---------------------------------------------------------
@bot.tree.command(name="askgame", description="ให้ AI แนะนำเกมตามใจคุณ (เช่น: เกมยิงซอมบี้ ภาพสวยๆ)")
@app_commands.describe(prompt="อยากเล่นเกมแนวไหน พิมพ์บอกมาได้เลย!")
async def askgame(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()

    # 1. สร้าง Prompt บังคับให้ AI ตอบแค่ชื่อเกม
    system_prompt = f"""
    คุณคือผู้เชี่ยวชาญเกม Steam
    ผู้ใช้ต้องการหาเกมแนว: "{prompt}"
    จงนึกถึงรายชื่อเกมที่ดีและตรงสเปคมาอย่างน้อย 10 เกม จากนั้นให้ "สุ่มเลือกตอบมาแค่ 1 เกม" (ต้องเป็นเกมที่มีขายบน Steam เท่านั้น)
    สำคัญมาก: ให้ตอบกลับมาเป็น "ชื่อเกมภาษาอังกฤษ" เท่านั้น ห้ามมีสัญลักษณ์ ห้ามมีคำอธิบาย ห้ามมีเครื่องหมายคำพูด
    """

    try:
        # 2. ถาม AI
        ai_response = model.generate_content(system_prompt)
        recommended_game = ai_response.text.strip()
        
        # 3. เอาชื่อเกมที่ AI แนะนำ ไปค้นหาใน Steam API
        search_url = f"https://store.steampowered.com/api/storesearch/?term={recommended_game}&cc=th&l=thai"
        search_res = requests.get(search_url)
        search_data = search_res.json()

        # ถ้าหาใน Steam เจอ
        if search_data.get('total') > 0:
            best_match = search_data.get('items')[0]
            name = best_match.get('name')
            app_id = best_match.get('id')
            link = f"https://store.steampowered.com/app/{app_id}"
            image_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"

            # ตกแต่งการ์ด
            embed = discord.Embed(
                title=f"🤖 AI แนะนำ: {name}", 
                description=f"คุณอยากได้แนว: *{prompt}*\nนี่คือเกมที่ AI เลือกให้ครับ!",
                url=link, 
                color=discord.Color.blue()
            )
            embed.set_image(url=image_url)

            # ดึงราคา (ถ้ามี)
            price_data = best_match.get('price')
            if price_data:
                final_price = price_data.get('final', 0) / 100
                embed.add_field(name="ราคาปัจจุบัน", value=f"**{final_price:,.0f} บาท**", inline=False)
            else:
                embed.add_field(name="ราคา", value="ไม่มีข้อมูลราคา (อาจจะเล่นฟรี)", inline=False)

            await interaction.followup.send(embed=embed)

        else:
            # ถ้า AI แนะนำชื่อเกมแปลกๆ มาแล้วหาใน Steam ไม่เจอ
            await interaction.followup.send(f"🤖 AI แนะนำเกม: **{recommended_game}** แต่บอทหาใน Steam ไม่เจอครับ ลองเปลี่ยนคำค้นหาดูนะ")

    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ AI: {e}")

# ---------------------------------------------------------
# คำสั่ง /review : ให้ AI สรุปรีวิวเกม
# ---------------------------------------------------------
@bot.tree.command(name="review", description="📝 ให้ AI สรุปรีวิว จุดเด่น-จุดด้อย ของเกม")
@app_commands.describe(game_name="ชื่อเกมที่อยากให้ AI รีวิว")
async def review(interaction: discord.Interaction, game_name: str):
    # บรรทัดนี้บอก Discord ว่า "รอแป๊บนึงนะ บอทกำลังคิด" (ป้องกัน error time out)
    await interaction.response.defer()

    try:
        # 1. ค้นหาเกมใน Steam ก่อน เพื่อเอาชื่อที่ถูกต้องเป๊ะๆ และดึงรูปปกมาใช้
        search_url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&cc=th&l=thai"
        search_res = requests.get(search_url)
        search_data = search_res.json()

        if search_data.get('total') > 0:
            # ดึงข้อมูลเกมอันดับแรกที่ค้นเจอ
            best_match = search_data.get('items')[0]
            real_game_name = best_match.get('name')
            app_id = best_match.get('id')
            image_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"
            steam_link = f"https://store.steampowered.com/app/{app_id}"

            # 2. สร้าง Prompt สั่งงาน AI ให้เป็นนักรีวิว
            review_prompt = f"""
            คุณคือนักวิจารณ์เกมที่เชี่ยวชาญและอธิบายเข้าใจง่าย
            ช่วยเขียนสรุปรีวิวสำหรับเกม "{real_game_name}" สั้นๆ ให้อ่านง่าย
            โดยบังคับให้ตอบตามโครงสร้าง 3 หัวข้อนี้เท่านั้น (ห้ามเกริ่นนำ ห้ามมีข้อความอื่น):
            ✅ **จุดเด่น:** (อธิบายสั้นๆ 1-2 บรรทัด)
            ❌ **จุดสังเกต:** (อธิบายสั้นๆ 1-2 บรรทัด)
            🎯 **เหมาะกับใคร:** (เช่น เหมาะกับคนชอบเกมแนวไหน มีเวลาเล่นเยอะไหม)
            """

            # 3. ส่งคำสั่งให้ AI (ใช้ model เดิมที่ประกาศไว้ด้านบนได้เลย)
            ai_response = model.generate_content(review_prompt)
            review_text = ai_response.text.strip()

            # 4. นำข้อความที่ AI สรุป มาใส่ลงในการ์ดสวยๆ
            embed = discord.Embed(
                title=f"📝 AI สรุปรีวิว: {real_game_name}",
                description=review_text,
                url=steam_link,
                color=discord.Color.purple() # ใช้สีม่วงหรือสีอะไรก็ได้ที่ชอบ
            )
            embed.set_image(url=image_url)
            embed.set_footer(text="รีวิวถูกสร้างขึ้นโดย Gemini AI")

            # ส่งกลับไปที่ Discord
            await interaction.followup.send(embed=embed)

        else:
            await interaction.followup.send(f"❌ บอทหาเกมชื่อ **{game_name}** ใน Steam ไม่เจอครับ ลองพิมพ์ชื่อให้เป๊ะขึ้นอีกนิดนะ")

    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลรีวิว: {e}")

# รันบอท
bot.run(TOKEN)