# -*- coding: utf-8 -*-
# NBA Player Report Streamlit App - Final and Stable Version (with Team Name)

import pandas as pd
import streamlit as st
from nba_api.stats.static import players
# 最終修正：使用兼容性最高的標準多行匯入格式，解決 Import/SyntaxError
from nba_api.stats.endpoints import (
    playerawards, 
    commonplayerinfo, 
    playercareerstats, 
)

# ====================================================================
# I. 數據獲取與處理的核心邏輯
# ====================================================================

# Streamlit 緩存裝飾器，加速重複查詢時的數據獲取
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

def get_precise_positions(generic_position):
    """將 NBA API 返回的通用位置（Guard, F-C 等）轉換為所有精確位置（PG, SG, SF, PF, C）。"""
    
    position_map = {
        'Guard': ['PG', 'SG'],
        'Forward': ['SF', 'PF'],
        'Center': ['C'],
        'G-F': ['PG', 'SG', 'SF'],
        'F-G': ['SG', 'SF', 'PF'],
        'F-C': ['SF', 'PF', 'C'],
        'C-F': ['PF', 'C', 'SF'],
        'G': ['PG', 'SG'],
        'F': ['SF', 'PF'],
        'C': ['C'],
    }
    
    positions = position_map.get(generic_position)
    
    if positions:
        return ", ".join(positions)
    
    return generic_position

def get_player_report(player_name, season='2023-24'):
    """獲取並整理特定球員的狀態報告數據。"""
    player_id = get_player_id(player_name)
    if not player_id:
        return {'error': f"找不到球員：{player_name}。請檢查姓名是否正確。"}

    try:
        # 1. 獲取基本資訊
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        info_df = info.get_data_frames()[0]
        
        # 2. 獲取生涯數據（總計）
        stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        stats_data = stats.get_data_frames()[0]
        season_stats = stats_data[stats_data['SEASON_ID'] == season]
        
        # 3. 獲取獎項資訊
        awards = playerawards.PlayerAwards(player_id=player_id)
        awards_df = awards.get_data_frames()[0]
        
        report = {}
        # --- 基本資訊 ---
        generic_pos = info_df.loc[0, 'POSITION']
        
        report['name'] = info_df.loc[0, 'DISPLAY_FIRST_LAST']
        report['team_abbr'] = info_df.loc[0, 'TEAM_ABBREVIATION'] # 保持縮寫供標題使用
        report['team_full'] = info_df.loc[0, 'TEAM_NAME'] # <-- 新增：球隊全名
        report['status'] = 'Healthy (Active)' 
        report['position'] = generic_pos  
        report['precise_positions'] = get_precise_positions(generic_pos) 
        
        # --- 場均數據與 命中率 ---
        if not season_stats.empty and season_stats.iloc[-1]['GP'] > 0:
            avg_stats = season_stats.iloc[-1]
            total_gp = avg_stats['GP']
            
            # 五大數據
            report['pts'] = round(avg_stats['PTS'] / total_gp, 1) 
            report['reb'] = round(avg_stats['REB'] / total_gp, 1)
            report['ast'] = round(avg_stats['AST'] / total_gp, 1)
            report['stl'] = round(avg_stats['STL'] / total_gp, 1) 
            report['blk'] = round(avg_stats['BLK'] / total_gp, 1) 
            
            # 命中率與罰球
            report['fg_pct'] = round(avg_stats['FG_PCT'] * 100, 1) 
            report['ft_pct'] = round(avg_stats['FT_PCT'] * 100, 1)
            report['fta_per_game'] = round(avg_stats['FTA'] / total_gp, 1)
            
            # 場均上場時間
            report['min_per_game'] = round(avg_stats['MIN'] / total_gp, 1) 
            
            # 薪資相關資訊 (佔位符)
            report['contract_year'] = '數據源無法獲取'
            report['salary'] = '數據源無法獲取'
            
            report['season'] = season
        else:
            report.update({
                'pts': 'N/A', 'reb': 'N/A', 'ast': 'N/A', 'stl': 'N/A', 'blk': 'N/A',
                'fg_pct': 'N/A', 'ft_pct': 'N/A', 'fta_per_game': 'N/A',
                'min_per_game': 'N/A', 
                'contract_year': 'N/A', 
                'salary': 'N/A',         
                'season': f"無 {season} 賽季數據",
            })

        # --- 獎項列表 (含年份) ---
        if not awards_df.empty:
            award_pairs = awards_df[['DESCRIPTION', 'SEASON']].apply(
                lambda x: f"{x['DESCRIPTION']} ({x['SEASON'][:4]})", axis=1
            ).tolist()
            report['awards'] = award_pairs
        else:
            report['awards'] = []

        return report

    except Exception as e:
        return {'error': f"數據處理失敗，可能該球員在 {season} 賽季沒有數據。詳細錯誤: {e}"}

# ======================================
# 輔助函數：風格分析
# ======================================

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

    style_analysis = analyze_style(data, data.get('position', 'N/A'))
    
    awards_list_md = '\n'.join([f"* {award}" for award in data['awards'] if award])
    if not awards_list_md:
        awards_list_md = "* 暫無官方 NBA 獎項記錄"

    markdown_text = f"""
## ⚡ {data['name']} ({data['team_abbr']}) 狀態報告 
*當前球隊:* **{data['team_full']}** # <-- 顯示球隊全名

**✅ 目前狀態:** {data['status']}

**🗺️ 可打位置:** **{data['precise_positions']}**

**💰 合約資訊 (當前賽季 {data['season']}):**
* 年薪/平均年薪: **{data['salary']}**
* 合約第幾年: **{data['contract_year']}**

**📊 {data['season']} 賽季平均數據:**
* 場均上場時間 (MIN): **{data['min_per_game']}**
* 場均得分 (PTS): **{data['pts']}**
* 場均籃板 (REB): **{data['reb']}**
* 場均助攻 (AST): **{data['ast']}**
* 場均抄截 (STL): **{data['stl']}**
* 場均封阻 (BLK): **{data['blk']}**
* 投籃命中率 (FG%): **{data['fg_pct']}%**
* 罰球命中率 (FT%): **{data['ft_pct']}%**
* 場均罰球數 (FTA): **{data['fta_per_game']}**

---

**⭐ 球員風格分析 (對標資深球迷):**
* **核心風格:** {style_analysis['core_style']}
* **簡化評級:** {style_analysis['simple_rating']}
* **對標選手:** {style_analysis['comparsion']}

---

**🏆 曾經得過的官方獎項 (含年份):**
{awards_list_md}
"""
    return markdown_text

# ====================================================================
# II. Streamlit 界面邏輯
# ====================================================================

# 設定頁面
st.set_page_config(layout="centered")
st.title("🏀 NBA 球員狀態報告自動生成系統")

# 使用 Streamlit 的 sidebar 創建輸入表單
with st.sidebar:
    st.header("參數設置")
    player_name_input = st.text_input("輸入球員全名:", value="Jayson Tatum")
    season_input = st.text_input("輸入查詢賽季:", value="2023-24")
    
    # 創建一個按鈕
    if st.button("🔍 生成報告"):
        if player_name_input:
            with st.spinner(f'正在爬取 {player_name_input} 的 {season_input} 數據...'):
                report_data = get_player_report(player_name_input, season_input)
                markdown_output = format_report_markdown_streamlit(report_data)
                
                # 將結果儲存到 session_state
                st.session_state['report'] = markdown_output
                st.session_state['player_name'] = player_name_input
                st.session_state['season_input'] = season_input
        else:
            st.warning("請輸入一個球員姓名。")

# 顯示主要內容
st.header("生成結果")
if 'report' in st.session_state:
    st.markdown(st.session_state['report'])
