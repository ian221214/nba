# -*- coding: utf-8 -*-
# NBA Player Report Streamlit App - Final and Stable Version (Corrected Model Output)

import pandas as pd
import streamlit as st
from nba_api.stats.static import players
# 引入相似度計算所需的庫
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
# 引入獲取所有球員數據的 API 端點
from nba_api.stats.endpoints import (
    playerawards, 
    commonplayerinfo, 
    playercareerstats, 
    LeagueDashPlayerStats, # 用於獲取所有球員的基準數據
)

# ====================================================================
# I. 數據獲取與處理的核心邏輯
# ====================================================================

# 7 個用於相似度分析的特徵
SIMILARITY_FEATURES = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT', 'FT_PCT']

@st.cache_data(ttl=3600 * 24)
def get_all_player_stats(season):
    """獲取所有活躍球員的基準統計數據，用於相似度計算。"""
    try:
        BASELINE_SEASON = '2023-24'
        all_stats = LeagueDashPlayerStats(
            season=BASELINE_SEASON, 
            season_type_all_star='Regular Season'
        )
        all_stats_df = all_stats.get_data_frames()[0]
        
        df = all_stats_df[['PLAYER_NAME', 'PLAYER_ID', 'PLAYER_POSITION'] + SIMILARITY_FEATURES].copy()
        df['FG_PCT'] = df['FG_PCT']
        df['FT_PCT'] = df['FT_PCT']
        df = df.fillna(0)
        
        return df
    except Exception as e:
        return None


@st.cache_data
def get_player_id(player_name):
    """根據球員姓名查找其唯一的 Player ID"""
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
    """將 NBA API 返回的通用位置轉換為所有精確位置。"""
    position_map = {
        'Guard': ['PG', 'SG'], 'Forward': ['SF', 'PF'], 'Center': ['C'],
        'G-F': ['PG', 'SG', 'SF'], 'F-G': ['SG', 'SF', 'PF'], 'F-C': ['SF', 'PF', 'C'],
        'C-F': ['PF', 'C', 'SF'], 'G': ['PG', 'SG'], 'F': ['SF', 'PF'], 'C': ['C'],
    }
    positions = position_map.get(generic_position)
    if positions:
        return ", ".join(positions)
    return generic_position

def get_player_report(player_name, season='2023-24'):
    # ... (此函數內容保持不變，因為數據獲取邏輯已經穩定)
    player_id = get_player_id(player_name)
    if not player_id:
        return {'error': f"找不到球員：{player_name}。請檢查姓名是否正確。"}

    try:
        # 數據獲取邏輯 (確保報告字段存在)
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        info_df = info.get_data_frames()[0]
        stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        stats_data = stats.get_data_frames()[0]
        season_stats = stats_data[stats_data['SEASON_ID'] == season]
        awards = playerawards.PlayerAwards(player_id=player_id)
        awards_df = awards.get_data_frames()[0]
        
        report = {}
        generic_pos = info_df.loc[0, 'POSITION']
        report['name'] = info_df.loc[0, 'DISPLAY_FIRST_LAST']
        
        # 處理球隊邏輯
        if not season_stats.empty:
            team_abbr_list = season_stats['TEAM_ABBREVIATION'].tolist()
            if 'TOT' in team_abbr_list:
                abbrs = [a for a in team_abbr_list if a != 'TOT']
                report['team_abbr'] = ", ".join(abbrs)
                report['team_full'] = f"效力多隊: {report['team_abbr']}"
            else:
                report['team_abbr'] = team_abbr_list[0]
                report['team_full'] = team_abbr_list[0]
        else:
            report['team_abbr'] = info_df.loc[0, 'TEAM_ABBREVIATION']
            report['team_full'] = info_df.loc[0, 'TEAM_NAME'] 
        
        report['status'] = 'Healthy (Active)' 
        report['position'] = generic_pos  
        report['precise_positions'] = get_precise_positions(generic_pos) 
        
        # --- 場均數據計算 ---
        if not season_stats.empty and season_stats.iloc[-1]['GP'] > 0:
            avg_stats = season_stats.iloc[-1]
            total_gp = avg_stats['GP']
            
            report['pts'] = round(avg_stats['PTS'] / total_gp, 1) 
            report['reb'] = round(avg_stats['REB'] / total_gp, 1)
            report['ast'] = round(avg_stats['AST'] / total_gp, 1)
            report['stl'] = round(avg_stats['STL'] / total_gp, 1) 
            report['blk'] = round(avg_stats['BLK'] / total_gp, 1) 
            
            # 相似度計算的原始數據
            report['fg_pct_raw'] = avg_stats['FG_PCT']
            report['ft_pct_raw'] = avg_stats['FT_PCT']
            
            report['fg_pct'] = round(avg_stats['FG_PCT'] * 100, 1) 
            report['ft_pct'] = round(avg_stats['FT_PCT'] * 100, 1)
            
            report['fta_per_game'] = round(avg_stats['FTA'] / total_gp, 1)
            report['min_per_game'] = round(avg_stats['MIN'] / total_gp, 1) 
            
            report['contract_year'] = '數據源無法獲取'
            report['salary'] = '數據源無法獲取'
            report['season'] = season
        else:
            report.update({
                'pts': 'N/A', 'reb': 'N/A', 'ast': 'N/A', 'stl': 'N/A', 'blk': 'N/A',
                'fg_pct': 'N/A', 'ft_pct': 'N/A', 'fta_per_game': 'N/A',
                'min_per_game': 'N/A', 'contract_year': 'N/A', 'salary': 'N/A',         
                'season': f"無 {season} 賽季數據",
                'fg_pct_raw': 0, 'ft_pct_raw': 0 
            })

        # --- 獎項列表 ---
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


# ====================================================================
# III. 相似度計算與風格分析 (升級對標)
# ====================================================================

def get_closest_match(target_stats_dict, current_season):
    """計算餘弦相似度並找出最貼切的對標選手。"""
    
    # 載入所有基準數據
    all_players_df = get_all_player_stats(current_season)
    
    # vvvvvvvvvvvvvv 【最終修正：處理基準庫載入失敗】 vvvvvvvvvvvvvv
    if all_players_df is None or all_players_df.empty:
        # 如果基準庫載入失敗，直接返回錯誤訊息字串
        return "MODEL_FAILED_DUE_TO_DATA_LIMIT" # <--- 返回特殊標籤，讓外層函數處理
    # ^^^^^^^^^^^^^^ 【最終修正：處理基準庫載入失敗】 ^^^^^^^^^^^^^^

    target_player_name = target_stats_dict['name']
    target_position = target_stats_dict['position']
    
    # 1. 執行位置篩選
    filtered_df = all_players_df[all_players_df['PLAYER_POSITION'].str.contains(target_position[:1], case=False, na=False)].copy()
    comparison_df = filtered_df[filtered_df['PLAYER_NAME'] != target_player_name].copy()
    comparison_df = comparison_df[comparison_df['PTS'] >= 5]
    
    if comparison_df.empty:
        return "數據庫太小，無同位置合格對標選手。"
    
    # 2. 準備目標數據向量
    target_data = {
        'PTS': [target_stats_dict['pts']], 'REB': [target_stats_dict['reb']], 
        'AST': [target_stats_dict['ast']], 'STL': [target_stats_dict['stl']], 
        'BLK': [target_stats_dict['blk']], 'FG_PCT': [target_stats_dict['fg_pct_raw']], 
        'FT_PCT': [target_stats_dict['ft_pct_raw']]
    }
    target_df = pd.DataFrame(target_data)

    # 3. 數據標準化 (StandardScaler)
    scaler = StandardScaler()
    comparison_scaled = scaler.fit_transform(comparison_df[SIMILARITY_FEATURES])
    target_scaled = scaler.transform(target_df[SIMILARITY_FEATURES])

    # 4. 計算餘弦相似度
    similarity_scores = cosine_similarity(target_scaled, comparison_scaled)[0]
    
    # 5. 找出最高相似度的球員
    comparison_df['Similarity'] = similarity_scores
    best_match = comparison_df.sort_values(by='Similarity', ascending=False).iloc[0]
    
    score = round(best_match['Similarity'] * 100, 2)
    return f"{best_match['PLAYER_NAME']} (相似度: {score}%)"


def analyze_style(stats, position):
    """此函數保留風格判斷邏輯，不執行對標。"""
    try:
        pts = float(stats.get('pts', 0))
        ast = float(stats.get('ast', 0))
        reb = float(stats.get('reb', 0))
    except ValueError:
        return {'core_style': '數據不足，無法分析', 'simple_rating': '請嘗試查詢有數據的賽季。'}

    HIGH_PTS, HIGH_AST, HIGH_REB = 25, 8, 10
    core_style, simple_rating = "角色球員", "可靠的輪換球員。"
    
    if pts >= HIGH_PTS and ast >= 6 and reb >= 6:
        core_style = "🌟 頂級全能巨星 (Elite All-Around Star)"
        simple_rating = "集得分、組織和籃板於一身的劃時代球員。"
    elif pts >= HIGH_PTS:
        core_style = "得分機器 (Volume Scorer)"
        simple_rating = "聯盟頂級的得分手，能夠在任何位置取分。"
    elif ast >= HIGH_AST and pts >= 15:
        core_style = "🎯 組織大師 (Playmaking Maestro)"
        simple_rating = "以傳球優先的組織核心，同時具備可靠的得分能力。"
    elif reb >= HIGH_REB and pts < 15:
        core_style = "🧱 籃板/防守支柱 (Rebounding/Defense Anchor)"
        simple_rating = "內線防守和籃板的專家，隊伍的堅實後盾。"
    else:
        core_style = "角色球員 (Role Player)"
        simple_rating = "一名可靠的輪換球員。"

    return {'core_style': core_style, 'simple_rating': simple_rating}


def format_report_markdown_streamlit(data):
    """將整理後的數據格式化為 Markdown 報告 (Streamlit 直接渲染)"""
    if data.get('error'):
        return f"## ❌ 錯誤報告\n\n{data['error']}"

    style_analysis = analyze_style(data, data.get('position', 'N/A'))
    
    # 獲取動態對標結果
    if data['pts'] != 'N/A':
        comparison_result = get_closest_match(data, data['season'])
        
        # vvvvvvvvvvvvvv 【最終修正：優雅處理失敗】 vvvvvvvvvvvvvv
        if comparison_result == "MODEL_FAILED_DUE_TO_DATA_LIMIT":
            # 如果模型失敗，則使用風格分析的結果作為備用
            comparison_result = f"數據庫暫時無法連接，風格相似：{style_analysis['core_style']}"
        elif comparison_result == "數據庫太小，無同位置合格對標選手。":
            # 如果是數據太少，也使用風格分析結果
            comparison_result = f"數據庫太小，風格相似：{style_analysis['core_style']}"
        # ^^^^^^^^^^^^^^ 【最終修正：優雅處理失敗】 ^^^^^^^^^^^^^^

    else:
        comparison_result = "數據不足，無法進行對標。"
        
    awards_list_md = '\n'.join([f"* {award}" for award in data['awards'] if award])
    if not awards_list_md:
        awards_list_md = "* 暫無官方 NBA 獎項記錄"

    markdown_text = f"""
## ⚡ {data['name']} ({data['team_abbr']}) 狀態報告 
**當賽季效力球隊:** **{data['team_full']}**

**✅ 目前狀態:** {data['status']}

**🗺️ 可打位置:** **{data['precise_positions']}**

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

**⭐ 球員風格分析 (機器學習對標):**
* **核心風格:** {style_analysis['core_style']}
* **簡化評級:** {style_analysis['simple_rating']}
* **球員模板:** **{comparison_result}**

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
    player_name_input = st.text_input("輸入球員全名:", value="James Harden")
    season_input = st.text_input("輸入查詢賽季:", value="2018-19")
    
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
