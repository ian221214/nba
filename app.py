# -*- coding: utf-8 -*-
# NBA Player Report Streamlit App - Clean Deployment Version

import pandas as pd
import streamlit as st
from nba_api.stats.static import players
from nba_api.stats.endpoints import playerawards, commonplayerinfo, playercareerstats

# ====================================================================
# I. 數據獲取與處理的核心邏輯 (nba_stats.py 的內容)
# ====================================================================

@st.cache_data
def get_player_id(player_name):
    """根據球員姓名查找其唯一的 Player ID (使用 Streamlit 緩存)"""
    try:
        nba_players = players.get_players()
        player_info = [
            player for player in nba_players 
            if player['full_name'].lower() == player_name.lower()
        ]
        return player_info[0]['id'] if player_info else None
    except Exception:
        return None

def get_player_report(player_name, season='2023-24'):
    """獲取並整理特定球員的狀態報告數據。"""
    player_id = get_player_id(player_name)
    if not player_id:
        return {'error': f"找不到球員：{player_name}。請檢查姓名是否正確。"}

    try:
        # 1. 獲取基本資訊（位置、球隊）
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        info_df = info.get_data_frames()[0]
        
        # 2. 獲取生涯數據（總計和場均數據）
        stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        stats_data = stats.get_data_frames()[0]
        season_stats = stats_data[stats_data['SEASON_ID'] == season]
        
        # 3. 獲取獎項資訊
        awards = playerawards.PlayerAwards(player_id=player_id)
        awards_df = awards.get_data_frames()[0]
        
        report = {}
        # 基本資訊
        report['name'] = info_df.loc[0, 'DISPLAY_FIRST_LAST']
        report['team'] = info_df.loc[0, 'TEAM_ABBREVIATION']
        report['status'] = 'Healthy (Active)' 
        report['position'] = info_df.loc[0, 'POSITION']
        
        # 場均數據
        if not season_stats.empty and season_stats.iloc[-1]['GP'] > 0:
            avg_stats = season_stats.iloc[-1]
            report['pts'] = round(avg_stats['PTS'] / avg_stats['GP'], 1) 
            report['reb'] = round(avg_stats['REB'] / avg_stats['GP'], 1)
            report['ast'] = round(avg_stats['AST'] / avg_stats['GP'], 1)
            report['season'] = season
        else:
            report['pts'], report['reb'], report['ast'], report['season'] = 'N/A', 'N/A', 'N/A', f"無 {season} 賽季數據"

        # 獎項列表
        if not awards_df.empty:
            report['awards'] = awards_df['DESCRIPTION'].unique().tolist()
        else:
            report['awards'] = []

        return report

    except Exception as e:
        return {'error': f"數據處理失敗，可能該球員在 {season} 賽季沒有數據。詳細錯誤: {e}"}

def analyze_style(stats, position):
    """根據場均數據和位置，生成簡單的球員風格分析。"""
    try:
        pts = float(stats.get('pts', 0))
        ast = float(stats.get('ast', 0))
        reb = float(stats.get('reb', 0))
    except ValueError:
        return {'core_style': '數據不足，無法分析', 'simple_rating': '請嘗試查詢有數據的賽季。', 'comparsion': '無對標選手'}

    HIGH_PTS, HIGH_AST, HIGH_REB = 25, 8, 10
    core_style, simple_rating, comparsion = "角色球員", "可靠的輪換球員。", "無對標選手"
    
    # 風格判斷邏輯
    if pts >= HIGH_PTS and ast >= 6 and reb >= 6:
        core_style = "🌟 頂級全能巨星 (Elite All-Around Star)"
        simple_rating = "集得分、組織和籃板於一身的劃時代球員。"
        comparsion = "數據風格類似當年的 LeBron James 或 Nikola Jokic。"
    elif pts >= HIGH_PTS:
        core_style = "得分機器 (Volume Scorer)"
        simple_rating = "聯盟頂級的得分手，能夠在任何位置取分。"
        comparsion = "數據風格類似當年的 Kevin Durant 或 Michael Jordan。"
    elif ast >= HIGH_AST and pts >= 15:
        core_style = "🎯 組織大師 (Playmaking Maestro)"
        simple_rating = "以傳球優先的組織核心，同時具備可靠的得分能力。"
        comparsion = "數據風格類似當年的 Steve Nash 或 Chris Paul。"
    elif reb >= HIGH_REB and pts < 15:
        core_style = "🧱 籃板/防守支柱 (Rebounding/Defense Anchor)"
        simple_rating = "內線防守和籃板的專家，隊伍的堅實後盾。"
        comparsion = "數據風格類似當年的 Dennis Rodman 或 Ben Wallace。"

    return {'core_style': core_style, 'simple_rating': simple_rating, 'comparsion': comparsion}

def format_report_markdown_streamlit(data):
    """將整理後的數據格式化為 Markdown 報告 (Streamlit 直接渲染)"""
    if data.get('error'):
        return f"## ❌ 錯誤報告\n\n{data['error']}"

    # 注意：這裡使用 analyze_style 函數，確保它定義在 app.py 的前面部分
    style_analysis = analyze_style(data, data.get('position', 'N/A'))
    
    awards_list_md = '\n'.join([f"* {award}" for award in data['awards'] if award])
    if not awards_list_md:
        awards_list_md = "* 暫無官方 NBA 獎項記錄"

    markdown_text = f"""
## ⚡ {data['name']} ({data['team']}) 狀態報告

**✅ 目前狀態:** {data['status']}

**🗺️ 可打位置:** **{data['position']}**

**📊 {data['season']} 賽季平均數據:**
* 場均得分 (PTS): **{data['pts']}**
* 場均籃板 (REB): **{data['reb']}**
* 場均助攻 (AST): **{data['ast']}**

---

**⭐ 球員風格分析 (對標資深球迷):**
* **核心風格:** {style_analysis['core_style']}
* **簡化評級:** {style_analysis['simple_rating']}
* **對標選手:** {style_analysis['comparsion']}

---

**🏆 曾經得過的官方獎項:**
{awards_list_md}
"""
    # 最終的修正：直接返回 Markdown 字串，不調用任何外部模組
    return markdown_text
# ====================================================================
# II. Streamlit 界面邏輯
# ====================================================================

st.set_page_config(layout="centered")
st.title("🏀 NBA 球員狀態報告自動生成系統")

# 使用 Streamlit 的 sidebar 創建輸入表單
with st.sidebar:
    st.header("參數設置")
    player_name_input = st.text_input("輸入球員全名:", value="Jayson Tatum")
    season_input = st.text_input("輸入查詢賽季:", value="2023-24")
    
    # 創建一個按鈕
    if st.button("🔍 生成報告"):
        # 檢查輸入是否為空
        if player_name_input:
            # 顯示載入中的訊息
            with st.spinner(f'正在爬取 {player_name_input} 的 {season_input} 數據...'):
                # 獲取數據
                report_data = get_player_report(player_name_input, season_input)
                
                # 格式化為 Markdown
                markdown_output = format_report_markdown_streamlit(report_data)
                
                # 將結果儲存到 session_state，以便頁面刷新後仍能顯示
                st.session_state['report'] = markdown_output
        else:
            st.warning("請輸入一個球員姓名。")

# 顯示主要內容
st.header("生成結果")
if 'report' in st.session_state:
    # 使用 st.markdown 渲染結果
    st.markdown(st.session_state['report'])
