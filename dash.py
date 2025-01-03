import requests
import streamlit as st

st.set_page_config(
    page_title="MIND",
    page_icon="🍋",
    layout="wide",
    initial_sidebar_state="expanded",
)

reduce_header_height_style = """
    <style>
        div.block-container {padding-top:1rem;}
    </style>
"""
st.markdown(reduce_header_height_style, unsafe_allow_html=True)


st.markdown("""
    <style>
        .title-text {
            color: #ABE7E1;
        }
        .white-text {
            color: white;
        }
    </style>
    <h1 class="white-text">
            <span class="title-text"">M</span>ultimodal
            <span class="title-text">IN</span>teractive 
            <span class="title-text">D</span>ashboard
    </h1>
""", unsafe_allow_html=True)

card_css = """
<style>
.card {
    border-radius: 15px;
    padding: 20px;
    background-color: #1C1C2A;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px; /* 카드 사이 간격 추가 */
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.card-title {
    display: flex;
    flex-direction: row;
    align-items: center;
    margin-bottom: 5px;
}

.card-title > * + * {
    margin-left: 5px;
}

.card-content {
    display: flex;
    flex-direction: column;
    color: white;
    font-size: 28px;
    font-weight: bold;
}

.tooltip-trigger {
    position: relative;
    cursor: pointer;
    font-size: 11px;
    border-radius: 50%; /* 100% 대신 50%로 변경 */
    width: 19px; /* 원의 크기를 조정 */
    height: 19px; /* 원의 크기를 조정 */
    color: white; /* 텍스트 색상 설정 */
    border-color: white;
    border-style:solid;
    border-width: 1.5px;
    text-align: center; /* 텍스트 중앙 정렬 */
    line-height: 19px; /* 텍스트 수직 중앙 정렬 */
}

.tooltip-trigger::before {
    content: attr(data-tooltip);
    position: absolute;
    top: -30px;
    left: 50%;
    transform: translateX(-50%);
    padding: 5px;
    background-color: rgba(0, 0, 0, 0.8);
    color: white;
    border-radius: 5px;
    font-size: 14px;
    white-space: nowrap;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.2s, visibility 0.2s;
}


.tooltip-trigger:hover::before {
    opacity: 1;
    visibility: visible;
}

#seledtBox {
            color: white;
            border: 1px solid white;
            background-color: transparent;
            padding: 5px;
            border-radius: 5px;
        }

#seledtBox option {
    color: black;
    border: 1px solid white;
}
</style>
"""


cols = st.columns([1, 1])

st.markdown(card_css, unsafe_allow_html=True)

with cols[0].container():
    # sub_cols_1 = st.columns([1, 1])

    # with sub_cols_1[0].container():
    #     st.markdown('''
    #             <div class="card">
    #                 <div class="card-content">\t</div>
    #                 <iframe src="http://localhost:5000/face_feed" width="100%" height="485" frameborder="0" scrolling="no">
    #                 </iframe>
    #             </div>''', unsafe_allow_html=True)
        
    st.markdown('''
            <div class="card">
                <div class = "card-title" >
                <div class="card-content">Emotion</div>
                </div>
                    <iframe src="http://localhost:5000/emotion_feed" width="100%" height="450" frameborder="0" scrolling="no">
                    </iframe>
            </div>''', unsafe_allow_html=True)
    
    # st.markdown('''
    #     <div class="card">
    #         <div class="card-title">
    #             <div class="card-content">Transform into Character</div>
    #             </select>
    #         </div>
    #         <iframe src="http://localhost:5000/streamdiffusion_feed" width="100%" height="450" frameborder="0" scrolling="no">
    #         </iframe>
    #     </div>
    #     ''', unsafe_allow_html=True)

    #### Two cols ####
    sub_cols_1 = st.columns([1, 1])

    with sub_cols_1[0].container():
        st.markdown('''
            <div class="card">
                <div class="card-title">
                    <div class="card-content">Original Video</div>
                    </select>
                </div>
                <iframe src="http://localhost:5000/video_feed" width="100%" height="450" frameborder="0" scrolling="no">
                </iframe>
            </div>
            ''', unsafe_allow_html=True)

    with sub_cols_1[1].container():
        st.markdown('''
            <div class="card">
                <div class="card-title">
                    <div class="card-content">Transform into Character</div>
                    </select>
                </div>
                <iframe src="http://localhost:5000/streamdiffusion_feed" width="100%" height="450" frameborder="0" scrolling="no">
                </iframe>
            </div>
            ''', unsafe_allow_html=True)
    #####################

    # st.markdown('''
    #     <div class="card" style="height: 540px; width: 100%;>
    #         <div class="card-title" style="position: absolute; top: 20px; left: 20px; font-size: 20px;">
    #             <div class="card-content">Transform into Character</div>
    #         </div>
    #         <div style="display: flex; justify-content: center; align-items: center; width: 100%; height: 100vh;">
    #             <iframe src="http://localhost:5000/video_feed" style="flex: 1; height: 150vh; margin-right: 10px;" frameborder="0" scrolling="no"></iframe>
    #             <iframe src="http://localhost:5000/streamdiffusion_feed" style="flex: 1; height: 90vh; margin-left: 10px; position: relative; top: -1025px;" frameborder="0" scrolling="no"></iframe>
    #         </div>
    #     </div>
    # ''', unsafe_allow_html=True)

with cols[1].container():
    st.markdown('''
            <div class="card">
                    <div class = "card-title">
                    <div class="card-content">EEG Stream</div>
                    </div>
                    <iframe src="http://localhost:5000/eeg_feed" width="100%" height="550" frameborder="0" scrolling="no">
                    </iframe>
            </div>''', unsafe_allow_html=True)
    
    sub_cols_2 = st.columns([1.2, 1])

    with sub_cols_2[0].container():
        st.markdown('''
                <div class="card">
                    <div class = "card-title">
                    <div class="card-content">EEG Scalp Maps</div>
                    </div>
                        <iframe src="http://localhost:5000/mne_feed" width="100%" height="350" frameborder="0" scrolling="no">
                        </iframe>
                </div>''', unsafe_allow_html=True)
    

    with sub_cols_2[1].container():
        st.markdown('''
                <div class="card">
                    <div class = "card-title">
                    <div class="card-content">Attention</div>
                    </div>
                    <iframe src="http://localhost:5000/attention_feed" width="100%" height="350" frameborder="0" scrolling="no">
                        </iframe>
                </div>''', unsafe_allow_html=True)
        
