import streamlit as st
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. 初始化全局狀態 (跨使用者共享)
# ==========================================
@st.cache_resource
def get_auction_state():
    return {
        "round": 1,               # 紀錄目前是第幾次拍賣
        "image": None,            # 拍賣的圖片物件 (PIL Image)
        "highest_bid": 0,         # 目前最高出價
        "highest_bidder": None,   # 目前最高出價者
        "last_bid_time": None,    # 最後一次出價的時間戳
        "auction_ended": False    # 拍賣是否已結束
    }

state = get_auction_state()

# ==========================================
# 2. 圖片處理函數 (產生得標結果圖)
# ==========================================
def generate_winner_image():
    original = state["image"]
    width, height = original.size
    
    new_height = height + 100
    new_img = Image.new("RGB", (width, new_height), "white")
    new_img.paste(original, (0, 0))
    
    draw = ImageDraw.Draw(new_img)
    
    try:
        font = ImageFont.truetype("msjh.ttc", max(24, int(width/25))) 
    except:
        try:
            font = ImageFont.truetype("PingFang.ttc", max(24, int(width/25)))
        except:
            font = ImageFont.load_default()
            
    winner_text = f"第 {state['round']} 場得標者: {state['highest_bidder']} | 金額: ${state['highest_bid']}"
    
    text_bbox = draw.textbbox((0, 0), winner_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) / 2
    y = height + (100 - text_height) / 2 - 10
    
    draw.text((x, y), winner_text, fill="black", font=font)
    
    buf = BytesIO()
    new_img.save(buf, format="PNG")
    return buf.getvalue()

# ==========================================
# 3. 主程式 UI 與 邏輯
# ==========================================
st.set_page_config(page_title="即時圖片拍賣系統", page_icon="🔨")

# 使用者本地狀態 (登入名稱)
if "username" not in st.session_state:
    st.session_state.username = ""

# --- 側邊欄：自由登入區塊 ---
with st.sidebar:
    st.header("👤 參與者登入")
    st.info("觀看拍賣不需登入，欲參與喊價請先設定名稱。")
    name_input = st.text_input("請輸入您的名稱", value=st.session_state.username)
    if st.button("設定名稱"):
        if name_input.strip():
            st.session_state.username = name_input.strip()
            st.success(f"登入成功！身分：{st.session_state.username}")
        else:
            st.error("名稱不能為空！")

# 標題加入「第幾場拍賣」的變數
st.title(f"🔨 即時圖片拍賣系統 - 第 {state['round']} 場")

# --- 階段 A：上傳圖片 (無圖片時顯示，任何人皆可上傳) ---
if state["image"] is None:
    st.info("目前尚未有拍賣進行中，您可以直接上傳圖片來發起本回合的拍賣。")
    uploaded_file = st.file_uploader("上傳一張欲拍賣的圖片", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        if st.button("開始拍賣！", type="primary"):
            # 初始化本回合拍賣狀態
            state["image"] = Image.open(uploaded_file)
            state["highest_bid"] = 0
            state["highest_bidder"] = None
            state["last_bid_time"] = None
            state["auction_ended"] = False
            st.rerun()

# --- 階段 B：拍賣進行中 ---
else:
    # 顯示拍賣圖片
    st.image(state["image"], use_container_width=True, caption=f"第 {state['round']} 場競標拍賣品")
    st.divider()

    # 每秒自動更新的計時與狀態看板
    @st.fragment(run_every=1)
    def auction_timer_board():
        if state["last_bid_time"] is not None and not state["auction_ended"]:
            elapsed = time.time() - state["last_bid_time"]
            time_left = 10.0 - elapsed
            
            if time_left <= 0:
                state["auction_ended"] = True
                st.rerun()
            else:
                st.metric("🏆 當前最高出價", f"${state['highest_bid']}", f"出價者: {state['highest_bidder']}")
                st.error(f"⏳ 結標倒數： **{time_left:.1f} 秒** (若無人加價即結標)")
                
        elif not state["auction_ended"]:
            st.success("✨ 拍賣已開始！目前尚未有人出價，快來搶下第一標！")
            
        elif state["auction_ended"]:
            st.metric("🏆 最終得標金額", f"${state['highest_bid']}", f"得標者: {state['highest_bidder']}")

    auction_timer_board()

    # --- 互動區塊 (依據是否登入呈現不同介面) ---
    if not state["auction_ended"]:
        # 檢查是否已設定名稱 (登入)
        if not st.session_state.username:
            st.warning("👈 您目前正在觀看拍賣。若要參與喊價，請先在左側欄位設定您的名稱！")
        else:
            st.subheader(f"💰 {st.session_state.username}，請進行喊價")
            min_bid = state["highest_bid"] + 1
            
            col1, col2 = st.columns([3, 1])
            with col1:
                new_bid = st.number_input("輸入您的出價金額", min_value=min_bid, step=10, label_visibility="collapsed")
            with col2:
                if st.button("確認出價", use_container_width=True, type="primary"):
                    if state["last_bid_time"] is not None and (time.time() - state["last_bid_time"]) >= 10:
                        st.error("很抱歉，拍賣剛剛已經結束！出價無效。")
                        state["auction_ended"] = True
                        st.rerun()
                    elif new_bid > state["highest_bid"]:
                        state["highest_bid"] = new_bid
                        state["highest_bidder"] = st.session_state.username
                        state["last_bid_time"] = time.time()
                        st.rerun()
                    else:
                        st.error("出價必須高於目前最高金額！")
                    
    else:
        st.success("🎉 本場拍賣已結束！")
        
        # 僅得標者可以看到下載按鈕
        if st.session_state.username and st.session_state.username == state["highest_bidder"]:
            st.balloons()
            st.markdown("### 👑 恭喜您得標！請下載您的專屬證明圖片：")
            
            img_bytes = generate_winner_image()
            st.download_button(
                label="📥 下載得標圖片",
                data=img_bytes,
                file_name=f"auction_round_{state['round']}_winner.png",
                mime="image/png",
                type="primary"
            )
        else:
            if state['highest_bidder']:
                st.info(f"本次拍賣由 **{state['highest_bidder']}** 得標！")
            else:
                st.info("本次拍賣無人出價，流標！")
            
        st.divider()
        if st.button("開啟下一輪拍賣"):
            # 【修正關鍵】不再使用 state.clear()，而是單獨重置需要的數值，並將回合數 +1
            state["image"] = None
            state["highest_bid"] = 0
            state["highest_bidder"] = None
            state["last_bid_time"] = None
            state["auction_ended"] = False
            state["round"] += 1  # 進入下一回合
            st.rerun()
