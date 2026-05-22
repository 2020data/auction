import streamlit as st
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. 初始化全局狀態 (跨使用者共享)
# ==========================================
@st.cache_resource
def get_auction_state():
    # 利用 cache_resource 保持一個全域字典，所有連線的使用者都能讀寫同一個狀態
    return {
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
    
    # 在圖片下方增加 100px 的留白空間
    new_height = height + 100
    new_img = Image.new("RGB", (width, new_height), "white")
    new_img.paste(original, (0, 0))
    
    draw = ImageDraw.Draw(new_img)
    
    # 嘗試載入支援中文的字體 (依據你的作業系統可能需要調整)
    try:
        # Windows 常見微軟正黑體
        font = ImageFont.truetype("msjh.ttc", max(24, int(width/25))) 
    except:
        try:
            # Mac 常見字體
            font = ImageFont.truetype("PingFang.ttc", max(24, int(width/25)))
        except:
            # 找不到字體時的預設退路 (可能不支援中文顯示)
            font = ImageFont.load_default()
            
    # 準備寫入的文字
    winner_text = f"得標者: {state['highest_bidder']}  |  得標金額: ${state['highest_bid']}"
    
    # 簡單的文字置中邏輯
    text_bbox = draw.textbbox((0, 0), winner_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) / 2
    y = height + (100 - text_height) / 2 - 10
    
    # 畫上文字 (黑色)
    draw.text((x, y), winner_text, fill="black", font=font)
    
    # 轉為 BytesIO 以供下載
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

# --- 側邊欄：登入區塊 ---
with st.sidebar:
    st.header("👤 參與者登入")
    name_input = st.text_input("請輸入您的名稱以參與喊價", value=st.session_state.username)
    if st.button("設定名稱"):
        if name_input.strip():
            st.session_state.username = name_input.strip()
            st.success(f"登入成功！身分：{st.session_state.username}")
        else:
            st.error("名稱不能為空！")

st.title("🔨 即時圖片拍賣系統")

# 強制要求登入
if not st.session_state.username:
    st.warning("👈 請先在左側欄位設定您的名稱，才能檢視或參與拍賣！")
    st.stop()

# --- 階段 A：上傳圖片 (無圖片時顯示) ---
if state["image"] is None:
    st.info("目前尚未有拍賣進行中，您可以發起一場新的拍賣。")
    uploaded_file = st.file_uploader("上傳一張欲拍賣的圖片", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        if st.button("開始拍賣！"):
            # 初始化拍賣狀態
            state["image"] = Image.open(uploaded_file)
            state["highest_bid"] = 0
            state["highest_bidder"] = None
            state["last_bid_time"] = None
            state["auction_ended"] = False
            st.rerun()

# --- 階段 B：拍賣進行中 ---
else:
    # 顯示拍賣圖片
    st.image(state["image"], use_container_width=True, caption="競標拍賣品")
    st.divider()

    # 定義一個每秒自動更新的 Fragment 來處理倒數計時與狀態顯示
    @st.fragment(run_every=1)
    def auction_timer_board():
        # 如果已經有人出價且尚未結標，檢查是否超時
        if state["last_bid_time"] is not None and not state["auction_ended"]:
            elapsed = time.time() - state["last_bid_time"]
            time_left = 10.0 - elapsed
            
            if time_left <= 0:
                # 倒數結束，判定結標
                state["auction_ended"] = True
                st.rerun() # 觸發全局重整以顯示下載按鈕
            else:
                # 倒數中
                st.metric("🏆 當前最高出價", f"${state['highest_bid']}", f"出價者: {state['highest_bidder']}")
                st.error(f"⏳ 結標倒數： **{time_left:.1f} 秒** (若無人加價即結標)")
                
        elif not state["auction_ended"]:
            # 還沒有人出價
            st.success("✨ 拍賣已開始！目前尚未有人出價，快來搶下第一標！")
            
        elif state["auction_ended"]:
            # 結標狀態顯示
            st.metric("🏆 最終得標金額", f"${state['highest_bid']}", f"得標者: {state['highest_bidder']}")

    # 渲染計時面板
    auction_timer_board()

    # --- 互動區塊 ---
    if not state["auction_ended"]:
        st.subheader("💰 進行喊價")
        # 設定最低出價限制
        min_bid = state["highest_bid"] + 1
        
        # 將輸入框與按鈕放在同行
        col1, col2 = st.columns([3, 1])
        with col1:
            new_bid = st.number_input("輸入您的出價金額", min_value=min_bid, step=10, label_visibility="collapsed")
        with col2:
            if st.button("確認出價", use_container_width=True, type="primary"):
                # 再次確認是否已經逾時 (避免在最後0.1秒同時按下的競速問題)
                if state["last_bid_time"] is not None and (time.time() - state["last_bid_time"]) >= 10:
                    st.error("很抱歉，拍賣剛剛已經結束！出價無效。")
                    state["auction_ended"] = True
                    st.rerun()
                elif new_bid > state["highest_bid"]:
                    state["highest_bid"] = new_bid
                    state["highest_bidder"] = st.session_state.username
                    state["last_bid_time"] = time.time() # 重置計時器
                    st.rerun()
                else:
                    st.error("出價必須高於目前最高金額！")
                    
    else:
        st.success("🎉 拍賣已結束！")
        
        # 僅得標者可以看到下載按鈕
        if st.session_state.username == state["highest_bidder"]:
            st.balloons()
            st.markdown("### 👑 恭喜您得標！請下載您的專屬證明圖片：")
            
            # 產生圖片
            img_bytes = generate_winner_image()
            st.download_button(
                label="📥 下載得標圖片",
                data=img_bytes,
                file_name="auction_winner.png",
                mime="image/png",
                type="primary"
            )
        else:
            st.info(f"本次拍賣由 **{state['highest_bidder']}** 得標！")
            
        if st.button("開始全新的拍賣"):
            state.clear() # 清空共享狀態
            st.rerun()
