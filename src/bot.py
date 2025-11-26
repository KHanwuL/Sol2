import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import datetime
from typing import Optional

import db_manager as db
import solved_ac_api as api

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    db.init_db()
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync Error: {e}")

    daily_update.start()

# 봇 길드 참가 이벤트
@bot.event
async def on_guild_join(guild):
    if guild.system_channel:
        try:
            await guild.system_channel.send(
                f"초대해 주셔서 감사합니다! 당신의 PS 도우미 **Sol2**입니다!\n"
                f"'사용하기 전에, Sol2를 이용해보신 적이 없다면, '/등록' 명령어로 Sol2에 가입해 주세요!\n"
                f"도움이 필요하다면 '/도움' 명령어로 명령어 목록을 확인해 주세요!"
            )
        except discord.Forbidden:
            print(f"{guild.name} 서버 시스템 채널에 메세지를 보낼 권한이 없습니다.")

# 신규 서버 유저 참가 이벤트
@bot.event
async def on_member_join(member):
    guild = member.guild
    
    if guild.system_channel:
        try:
            await guild.system_channel.send(
                f"{guild.name}에 오신 것을 환영합니다!\n"
                f"이 서버는 PS 도우미 Sol2를 사용 중입니다.\n"
                f"Sol2를 이용하신 적이 없다면, '/등록' 명령어로 Sol2에 가입해 주세요!"
            )
        except discord.Forbidden:
            pass

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if interaction.response.is_done():
        send_func = interaction.followup.send
    else:
        send_func = interaction.response.send_message

    if isinstance(error, app_commands.MissingRole):
        await send_func(f"이 명령어를 사용하려면 **{error.missing_role}**이 필요합니다.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await send_func("이 명령어를 사용할 권한이 부족합니다.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        await send_func(
            f"봇에게 작업을 수행할 권한이 없습니다.\n"
            f"서버 설정에서 봇에게 다음 권한을 부여해주세요: **{missing_perms}**", 
            ephemeral=True
        )
    else:
        await interaction.followup.send(f"오류가 발생했습니다: {error}", ephemeral=True)

# ==================== 봇 명령어 ==================== #

def is_guild_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.guild is not None and interaction.user.id == interaction.guild.owner_id
    return app_commands.check(predicate)

# /그룹장 (부여/제거) {Member}
@bot.tree.command(name="그룹장", description="(서버장 전용)그룹장 역할을 부여합니다.")
@app_commands.choices(action=[
    app_commands.Choice(name="부여", value="add"),
    app_commands.Choice(name="제거", value="remove"),
])
@app_commands.describe(target="선택할 멤버를 지정해 주세요.")
@is_guild_owner()
async def set_group_manager(interaction: discord.Interaction, action: app_commands.Choice[str], target: discord.Member):
    await interaction.response.defer(ephemeral=True)

    if interaction.guild is None:
        await interaction.followup.send("이 명령어는 서버 내에서만 사용할 수 있습니다.", ephemeral=True)
        return

    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.followup.send("봇에게 **'역할 관리'** 권한이 없습니다.", ephemeral=True)
        return
    
    Sol2_Manager = discord.utils.get(interaction.guild.roles, name="Sol2_Manager")

    if not Sol2_Manager:
        try:
            Sol2_Manager = await interaction.guild.create_role(name="Sol2_Manager")
            await interaction.followup.send(f"Sol2_Manager 역할이 존재하지 않아 새로 생성하였습니다.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"역할 생성 실패: {e}", ephemeral=True)
            return

    if action.value == "add":
        try:
            await target.add_roles(Sol2_Manager)
            await interaction.followup.send(f"{target}에게 역할이 부여되었습니다.")
        except Exception as e:
            await interaction.followup.send(f"역할 부여에 실패하였습니다. {e}")
            return

    if action.value == "remove":
        try:
            await target.remove_roles(Sol2_Manager)
            await interaction.followup.send(f"{target}의 역할을 성공적으로 제거하였습니다.")
        except Exception as e:
            await interaction.followup.send(f"해당 멤버에게 역할이 없거나 오류가 발생하였습니다. {e}")

# /등록 {solvedac_id}
@bot.tree.command(name="등록", description="Sol2에 등록합니다.")
async def register_Sol2(interaction: discord.Interaction, solvedac_id: str):
    await interaction.response.defer(ephemeral=True)

    try:
        is_registered = db.is_registered_user(interaction.user.id)
        if is_registered:
            solvedac_handle = db.get_solvedac_handle(interaction.user.id)
            await interaction.followup.send(f"이미 가입되어 있습니다. id: {solvedac_handle}")
            return
        user_info = await api.get_user_info(solvedac_id)
        if not user_info:
            await interaction.followup.send(f"{solvedac_id} 계정을 찾을 수 없습니다.", ephemeral=True)
            return
        db.register_user(interaction.user.id, solvedac_id)

        top100_list = await get_user_top100_from_api(solvedac_id)
        if not top100_list:
            await interaction.followup.send("등록은 완료되었으나 문제 목록을 불러오지 못했습니다.", ephemeral=True)
            return
        db.insert_user_top100(solvedac_id, top100_list)
        await interaction.followup.send(f"{solvedac_id}로 성공적으로 등록되었습니다!")
    except Exception as e:
        await interaction.followup.send(f"등록에 실패하였습니다.", ephemeral=True)
        print(f"register_Sol2 error: {e}")


# ==================== 그룹 관련 봇 명령어 ==================== #

# /그룹 (생성/삭제) {group_name}
@bot.tree.command(name="그룹", description="(권한 필요)그룹 관련 명령어를 실행합니다.")
@app_commands.choices(action=[
    app_commands.Choice(name="생성", value="create"),
    app_commands.Choice(name="삭제", value="delete"),
])
@app_commands.checks.has_role("Sol2_Manager")
async def group_command(interaction: discord.Interaction, action: app_commands.Choice[str], group_name: str):
    await interaction.response.defer(ephemeral=True)

    # /그룹 생성 {group_name}
    if action.value == "create":
        if not interaction.guild:
            await interaction.followup.send("이 명령어는 서버 내에서만 사용할 수 있습니다.", ephemeral=True)
            return
        
        group_manager_id = interaction.user.id
        
        try:
            new_channel = await interaction.guild.create_text_channel(
                name=group_name, 
                topic=f"Sol2 {group_name} 그룹 채널입니다. 그룹장: <@{group_manager_id}>"
            )
            
            success = db.create_group(
                group_name=group_name,
                server_id=interaction.guild_id,
                channel_id=new_channel.id,
                manager_id=group_manager_id
            )

            if success:
                group_manager_solvedac_id = db.get_solvedac_handle(group_manager_id)
                if group_manager_solvedac_id is None:
                    return
                group_id = db.get_group_id(interaction.guild_id, new_channel.id)
                if group_id is None:
                    return
                db.add_group_member(group_manager_id,group_manager_solvedac_id,group_id)

                embed = discord.Embed(
                    title=f"{group_name} 채팅방에 오신 것을 환영합니다!",
                    description=f"이 채널은 {group_name} 그룹원들을 위한 채팅방입니다."
                )
                embed.add_field(name="그룹장:", value=f"<@{group_manager_id}>", inline=False)
                embed.add_field(name="명령어", value="/그룹 정보, /그룹원 참가, /문제집 목록", inline=False)

                await new_channel.send(embed=embed)
                
                await interaction.followup.send(f"**{group_name}** 그룹과 채널이 생성되었습니다.", ephemeral=True)
            else:
                await new_channel.delete()
                await interaction.followup.send(f"오류: **{group_name}** 그룹 이름은 이미 사용 중입니다.", ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(f"그룹 생성 중 오류 발생: {e}", ephemeral=True)

    # /그룹 삭제 {group_name}
    elif action.value == "delete":
        success = db.delete_group(group_name, interaction.user.id)

        if success:
            await interaction.followup.send(
                f"**{group_name}** 그룹이 삭제되었습니다. (채널은 수동으로 삭제해주세요)", ephemeral=True)
        else:
            await interaction.followup.send(
                f"삭제 실패: **{group_name}** 그룹이 없거나, 당신이 그룹장이 아닙니다.", ephemeral=True)

# /그룹정보
@bot.tree.command(name="그룹정보", description="그룹에 대한 정보를 출력합니다.")
async def group_info(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    channel_id = interaction.channel_id
    group_id = db.get_group_id(interaction.guild_id, channel_id)
    if group_id is None:
        await interaction.followup.send(f"그룹 채팅 채널에서 실행해 주세요.", ephemeral=True)
        return

    group_name = db.get_group_name(group_id)
    manager_id = db.get_group_manager(group_id)
    members = db.get_member(group_id) or []

    embed = discord.Embed(
        title=f"그룹 정보: {group_name}",
        description="그룹 상세 정보입니다."
    )
    embed.add_field(name="그룹장", value=f"<@{manager_id}>", inline=False)
        
    member_value = ", ".join(f"<@{m}>" for m in members) if members else "없음"
    embed.add_field(name="그룹원", value=member_value, inline=False)
        
    await interaction.followup.send(embed=embed, ephemeral=True)


# ==================== 그룹원 관련 봇 명령어 ==================== #

# /그룹원 (참가/탈퇴/정보)
@bot.tree.command(name="그룹원", description="그룹원 관련 명령어를 실행합니다.")
@app_commands.choices(action=[
    app_commands.Choice(name="참가", value="join"),
    app_commands.Choice(name="탈퇴", value="leave"),
    app_commands.Choice(name="정보", value="info")
])
async def member_command(interaction: discord.Interaction, action: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)

    channel_id = interaction.channel_id
    group_id = db.get_group_id(interaction.guild_id, channel_id)
    if group_id is None:
        await interaction.followup.send(f"그룹 채팅 채널에서 실행해 주세요.", ephemeral=True)
        return

    group_name = db.get_group_name(group_id)
    if not group_id:
        await interaction.followup.send(f"**{group_name}** 그룹이 존재하지 않습니다.", ephemeral=True)
        return

    solvedac_id = db.get_solvedac_handle(interaction.user.id)
    if not solvedac_id:
        await interaction.followup.send(f"db에 사용자님의 정보를 찾을 수가 없습니다. 등록을 안했다면 /등록 을 해주세요.")
        return
    
    # /그룹원 참가
    if action.value == "join":
        try:
            success = db.add_group_member(interaction.user.id, solvedac_id, group_id)
            if success:
                channel_id = db.get_channel_id(group_id)
                if channel_id:
                    channel = bot.get_channel(int(channel_id))
                    if isinstance(channel, discord.TextChannel):
                        await channel.send(f"**<@{interaction.user.id}>** 님이 그룹에 참가하셨습니다!")
                await interaction.followup.send(f"**{group_name}** 그룹에 참가했습니다.", ephemeral=True)
            else:
                await interaction.followup.send("참가 실패: 이미 그룹에 있거나 오류가 발생했습니다.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"에러 발생: {e}", ephemeral=True)
    
    # /그룹원 탈퇴
    elif action.value == "leave":
        success = db.delete_member(interaction.user.id, group_id)
        if success:
            await interaction.followup.send(f"**{group_name}** 그룹에서 탈퇴했습니다.", ephemeral=True)
        else:
            await interaction.followup.send(f"탈퇴 실패: 그룹에 속해있지 않거나 오류가 발생했습니다.", ephemeral=True)

    # /그룹원 정보
    elif action.value == "info":
        if db.is_member(solvedac_id, group_id):
            await interaction.followup.send(f"https://solved.ac/profile/{solvedac_id}", ephemeral=True)
        else:
            await interaction.followup.send(f"{solvedac_id}는 {group_name}의 그룹원이 아닙니다.", ephemeral=True)


# ==================== 문제집 관련 봇 명령어 ==================== #

# /문제집 (생성/삭제) {set_name}
@bot.tree.command(name="문제집", description="(권한 필요)문제집 관련 명령어를 실행합니다.")
@app_commands.choices(action=[
    app_commands.Choice(name="생성", value="create"),
    app_commands.Choice(name="삭제", value="delete"),
])
@app_commands.checks.has_role("Sol2_Manager")
async def problem_set_command(interaction: discord.Interaction, action: app_commands.Choice[str], set_name: str):
    await interaction.response.defer(ephemeral=True)
    
    channel_id = interaction.channel_id
    group_id = db.get_group_id(interaction.guild_id, channel_id)
    if group_id is None:
        await interaction.followup.send(f"그룹 채팅 채널에서 실행해 주세요.", ephemeral=True)
        return

    group_name = db.get_group_name(group_id)

    if not group_id:
        await interaction.followup.send(f"**{group_name}** 그룹이 존재하지 않습니다.", ephemeral=True)
        return
    
    # /문제집 생성 {set_name}
    if action.value == "create":
        group_manager_id = interaction.user.id

        try:
            success = db.create_problem_set(group_id, set_name)
            if success:
                await interaction.followup.send(f"**{set_name}** 문제집이 생성되었습니다.", ephemeral=True)
            else:
                await interaction.followup.send(f"문제집 생성 실패: 이미 존재하거나 오류가 발생했습니다.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"문제집 생성 중 오류 발생: {e}", ephemeral=True)

    # /문제집 삭제 {set_name}
    if action.value == "delete":
        success = db.delete_problem_set(group_id, set_name)
        if success:
            await interaction.followup.send(f"**{set_name}** 문제집이 삭제되었습니다.",ephemeral=True)
        else:
            await interaction.followup.send(f"삭제 실패: **{set_name}** 문제집이 존재하지 않습니다.", ephemeral=True)

# /문제집보기
@bot.tree.command(name="문제집보기", description="그룹장이 생성한 모든 문제집을 출력합니다.")
async def get_problem_sets(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    channel_id = interaction.channel_id
    group_id = db.get_group_id(interaction.guild_id, channel_id)
    if group_id is None:
        await interaction.followup.send(f"그룹 채팅 채널에서 실행해 주세요.", ephemeral=True)
        return
    group_name = db.get_group_name(group_id)
    if not group_id:
        await interaction.followup.send(f"**{group_name}** 그룹을 찾을 수 없습니다.", ephemeral=True)
        return
    
    manager_id = db.get_group_manager(group_id)
    problem_sets = db.get_problem_set(group_id)
    if not problem_sets:
        await interaction.followup.send(f"문제집이 없습니다. 문제집이 필요하다면 <@{manager_id}> 그룹장에게 요청하세요.", ephemeral=True)
        return


    embed = discord.Embed(
        title=f"그룹: {group_name}",
        description="문제집들"
    )
    
    for problem_set in problem_sets:
        embed.add_field(name="문제집",value=problem_set, inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


# ==================== 문제 관련 봇 명령어 ==================== #

# /문제집문제 (추가/삭제) {set_name} {problem_id}
@bot.tree.command(name="문제집문제", description="(권한 필요)문제집의 문제 관련 명령어를 실행합니다.")
@app_commands.choices(action=[
    app_commands.Choice(name="추가", value="insert"),
    app_commands.Choice(name="삭제", value="delete")
])
@app_commands.checks.has_role("Sol2_Manager")
async def problem_command(interaction: discord.Interaction, action: app_commands.Choice[str], set_name:str, problem_id: int):
    await interaction.response.defer(ephemeral=True)

    channel_id = interaction.channel_id
    group_id = db.get_group_id(interaction.guild_id, channel_id)
    if group_id is None:
        await interaction.followup.send(f"그룹 채팅 채널에서 실행해 주세요.", ephemeral=True)
        return
    
    set_id = db.get_set_id(group_id, set_name)
    if set_id is None:
        await interaction.followup.send(f"입력하신 문제집이 존재하지 않습니다.", ephemeral=True)
        return
    
    # /문제집문제 추가 {set_name} {problem_num}
    if action.value == "insert":
        db.add_problem(set_id, problem_id)
        await interaction.followup.send(f"{set_name}에 {problem_id} 문제를 추가했습니다.", ephemeral=True)

    # /문제집문제 삭제 {set_name} {problem_num}
    if action.value == "delete":
        db.delete_problem(set_id, problem_id)
        await interaction.followup.send(f"{set_name}의 {problem_id} 문제를 삭제하였습니다.", ephemeral=True)

# /문제집문제보기 {set_name}
@bot.tree.command(name="문제집문제보기", description="문제집의 문제들을 출력합니다.")
async def get_set_problems(interaction: discord.Interaction, set_name: str):
    await interaction.response.defer(ephemeral=True)

    channel_id = interaction.channel_id
    group_id = db.get_group_id(interaction.guild_id, channel_id)
    if group_id is None:
        await interaction.followup.send("그룹 채팅 채널에서 실행해 주세요.", ephemeral=True)
        return

    set_id = db.get_set_id(group_id, set_name)
    if not set_id:
        await interaction.followup.send(f"**{set_name}** 문제집을 찾을 수 없습니다.", ephemeral=True)
        return

    embed = discord.Embed(title=f"{set_name}", description="문제 목록")

    def get_problem_name(json_data: dict) -> str:
        try:
            return json_data['items']['titleKo']
        except Exception:
            return "제목읽기실패"
        
    problems = db.get_problem(set_id)
    if not problems:
        await interaction.followup.send(f"{set_name} 문제집에 문제가 없습니다.", ephemeral=True)
        return

    for problem_id in problems:
        try:
            problem_data = await api.get_problem_from_num(problem_id)
            problem_name = get_problem_name(problem_data)
            embed.add_field(name=f"{problem_name} ({problem_id})", value=f"https://www.acmicpc.net/problem/{problem_id}", inline=False)
        except Exception as e:
            embed.add_field(name=f"문제 {problem_id}", value=f"정보 불러오기 실패 ({e})", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# /문제 {problem_id}
@bot.tree.command(name="문제", description="백준 문제 정보를 출력합니다.")
async def get_baekjoon_problem_info(interaction: discord.Interaction, problem_id: int):
    await interaction.response.defer(ephemeral=True)

    try:
        baekjoon_problem_info = await api.get_problem_from_num(problem_id)
        titleKo = baekjoon_problem_info.get('titleKo') or baekjoon_problem_info.get('title') or "제목없음"
        await interaction.followup.send(f"{titleKo} ({problem_id})", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"문제 정보를 확인하는 데 실패했습니다. {e}", ephemeral=True)

# ==================== 사용자가 푼 문제 관련 봇 명령어 ==================== #

# /푼문제 {solvedac_id}
@bot.tree.command(name="푼문제", description="푼 문제를 출력합니다.")
async def get_solved_problems(interaction: discord.Interaction, solvedac_id: str):
    await interaction.response.defer(ephemeral=True)

    isUser = db.is_user(solvedac_id)
    if not isUser:
        await interaction.followup.send(f"{solvedac_id}는 Sol2 이용자가 아니므로, 불러올 수 없습니다.", ephemeral=True)
        return
    
    user_solved_problem_list = db.get_user_top100(solvedac_id)
    if not user_solved_problem_list:
        await interaction.followup.send(f"해당 사용자는 아직 문제를 풀지 않았습니다." , ephemeral=True)
        return
    
    embed = discord.Embed(
        title="푼 문제 목록:",
        description=f"{solvedac_id}님이 푼 문제들 목록입니다."
    )
    for solved_problem in user_solved_problem_list:
        problem_title = await get_baekjoon_problem_title(solved_problem)
        embed.add_field(name=f"{problem_title}", value=f"{solved_problem}", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# /오늘푼문제 {solvedac_id}
@bot.tree.command(name="오늘푼문제", description="오늘 사용자가 푼 문제를 출력합니다. (top 100 문제를 갱신해야 푼 것으로 처리됩니다.)")
async def solved_problem_today(interaction: discord.Interaction, solvedac_id: str):
    await interaction.response.defer(ephemeral=True)

    isUser = db.is_user(solvedac_id)
    if not isUser:
        await interaction.followup.send(f"{solvedac_id}는 Sol2 이용자가 아니므로, 불러올 수 없습니다.", ephemeral=True)
        return
    
    updated_top100_list = await get_user_top100_from_api(solvedac_id)
    if not updated_top100_list:
        return
    
    newly_added_problems = db.update_user_top100(solvedac_id, updated_top100_list)
    if not newly_added_problems:
        await interaction.followup.send(f"해당 사용자는 아직 문제를 풀지 않았습니다." , ephemeral=True)
        return
    
    embed = discord.Embed(
        title="푼 문제 목록:",
        description=f"{solvedac_id}님이 푼 문제들 목록입니다."
    )
    for solved_problem in newly_added_problems:
        problem_title = get_baekjoon_problem_title(solved_problem)
        embed.add_field(name=f"{problem_title} ({solved_problem})", value=f"https://www.acmicpc.net/problem/{solved_problem}", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)




# ==================== 라이벌 관련 봇 명령어 ==================== #

# /라이벌 (추가/삭제) {rival_id}
@bot.tree.command(name="라이벌", description="라이벌 관련 명령어를 실행합니다.")
@app_commands.choices(action=[
    app_commands.Choice(name="추가", value="add"),
    app_commands.Choice(name="삭제", value="delete"),
])
async def rival_command(interaction: discord.Interaction, action: app_commands.Choice[str], rival_id: str):
    await interaction.response.defer(ephemeral=True)

    solvedac_id = db.get_solvedac_handle(interaction.user.id)
    if not solvedac_id:
        await interaction.followup.send(f"db에 사용자님의 정보를 찾을 수가 없습니다. 등록을 안했다면 /등록 을 해주세요.", ephemeral=True)
        return
    
    # /라이벌 추가 {rival_id}
    if action.value == "add":
        try:
            isUser = db.is_user(rival_id)
            if not isUser:
                await interaction.followup.send(f"{rival_id}님은 아직 Sol2에 가입하지 않았습니다. 라이벌 신청을 하려면 라이벌이 Sol2에 가입되어 있어야 합니다.", ephemeral=True)
                return
            db.make_rival(solvedac_id, rival_id)
            await interaction.followup.send(f"라이벌 목록에 {rival_id}님이 추가되었습니다", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"라이벌 추가 중 오류가 발생했습니다. {e}", ephemeral=True)
            return
        
    # /라이벌 삭제 {rival_id}
    if action.value == "delete":
        try:
            db.erase_rival(solvedac_id, rival_id)
            await interaction.followup.send(f"라이벌을 성공적으로 삭제하였습니다. {rival_id}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"해당 라이벌이 없습니다. {e}", ephemeral=True)
            return
        
# /라이벌목록
@bot.tree.command(name="라이벌목록", description="라이벌 목록을 출력합니다.")
async def get_rival(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    my_id = db.get_solvedac_handle(interaction.user.id)
    if not my_id:
        await interaction.followup.send(f"db에 사용자님의 정보를 찾을 수가 없습니다. 등록을 안했다면 /등록 을 해주세요.", ephemeral=True)
        return
    rival_list = db.get_rival(my_id)
    
    if not rival_list:
        await interaction.followup.send("라이벌이 없습니다. /라이벌 추가 를 통해 라이벌을 만들어주세요.", ephemeral=True)
        return
    embed = discord.Embed(
        title="라이벌",
        description=f"{my_id}님의 라이벌 목록입니다."
    )
    for rival in rival_list:
        embed.add_field(name=f"{rival}", value="라이벌 설정 중", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# /역라이벌목록
@bot.tree.command(name="역라이벌목록", description="역라이벌 목록을 출력합니다.")
async def get_reverse_rival(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    my_id = db.get_solvedac_handle(interaction.user.id)
    if not my_id:
        await interaction.followup.send(f"db에 사용자님의 정보를 찾을 수가 없습니다. 등록을 안했다면 /등록 을 해주세요.", ephemeral=True)
        return
    reverse_list = db.get_reverse_rival(my_id)
    if not reverse_list:
        await interaction.followup.send("당신을 라이벌로 지정한 사람이 없습니다.", ephemeral=True)
        return
    embed = discord.Embed(
        title="역라이벌",
        description=f"{my_id}님의 역라이벌 목록입니다."
    )
    for reverse in reverse_list:
        embed.add_field(name=f"{reverse}", value="역라이벌 설정 중", inline=False)

    await interaction.followup.send(embed=embed, ephemeral= True)

# /라이벌도전장 {rival_id}
@bot.tree.command(name="라이벌도전장", description="라이벌이 푼 문제 중 내가 못 푼 문제를 출력합니다.")
async def rival_challenge(interaction: discord.Interaction, rival_id: str):
    await interaction.response.defer(ephemeral=True)

    isUser = db.is_user(rival_id)
    if not isUser:
        await interaction.followup.send(f"{rival_id}는 Sol2 이용자가 아니므로, 불러올 수 없습니다.", ephemeral=True)
        return
    
    solvedac_id = db.get_solvedac_handle(interaction.user.id)
    if not solvedac_id:
        await interaction.followup.send(f"db에 사용자님의 정보를 찾을 수가 없습니다. 등록을 안했다면 /등록 을 해주세요.")
        return
    
    my_solved_problem_list = db.get_user_top100(solvedac_id)
    if not my_solved_problem_list:
        return

    rival_solved_problem_list = db.get_user_top100(rival_id)
    if not rival_solved_problem_list:
        await interaction.followup.send(f"해당 사용자는 아직 문제를 풀지 않았습니다." , ephemeral=True)
        return
    
    rival_challenge_list = [pid for pid in rival_solved_problem_list if pid not in my_solved_problem_list]

    if not rival_challenge_list:
        await interaction.followup.send(f"{rival_id}님이 푼 문제 중 새로운 문제가 없습니다.", ephemeral=True)
        return

    embed = discord.Embed(
        title="라이벌 도전장",
        description=f"{rival_id}님이 풀었지만 아직 당신이 풀지 않은 문제들입니다."
    )
    for pid in rival_challenge_list:
        title = get_baekjoon_problem_title(pid)
        embed.add_field(name=f"{title} ({pid})", value=f"https://www.acmicpc.net/problem/{pid}", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# ==================== 기타 명령어들 ==================== #

async def get_baekjoon_problem_title(problem_id: int):
    try:
        baekjoon_problem_info = await api.get_problem_from_num(problem_id)
        titleKo = baekjoon_problem_info.get('titleKo') or baekjoon_problem_info.get('title') or f"문제 {problem_id}"
        return titleKo
    except Exception as e:
        print(f"문제 확인하는 데 오류 {e}")
        return f"문제 {problem_id}"
    
async def get_user_top100_from_api(solvedac_handle: str) -> Optional[list]:
    try:
        user_top100_list_json = await api.get_user_top100(solvedac_handle)
        items = user_top100_list_json.get('items', []) if isinstance(user_top100_list_json, dict) else []
        problem_ids = [item.get('problemId') for item in items if isinstance(item, dict)]
        return problem_ids
    except Exception as e:
        print(f"get_list_user_top100 Error: {e}")
        return None

async def did_user_solved_today(solvedac_id: str) -> Optional[bool]:
    isUser = db.is_user(solvedac_id)
    if not isUser:
        return
    
    updated_top100_list = await get_user_top100_from_api(solvedac_id)
    if not updated_top100_list:
        return
    
    newly_added_problems = db.update_user_top100(solvedac_id, updated_top100_list)
    if newly_added_problems:
        return True
    else:
        return False

async def check_user_new_solved():
    users = db.get_users_for_update()
    if not users:
        return
    
    for user in users:
        await did_user_solved_today(user)

@tasks.loop(hours=24)
async def daily_update():
    await check_user_new_solved()

@daily_update.before_loop
async def before_daily_loop():
    await bot.wait_until_ready()
    kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst)
    target_kst = now_kst.replace(hour=5, minute=0, second=0, microsecond=0)
    if now_kst >= target_kst:
        target_kst += datetime.timedelta(days=1)
    await discord.utils.sleep_until(target_kst)

if DISCORD_BOT_TOKEN:
    bot.run(DISCORD_BOT_TOKEN)
else:
    print("DISCORD_TOKEN이 .env 파일에 설정되지 않았습니다.")