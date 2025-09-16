import streamlit as st

# Set page configuration
st.set_page_config(page_title="Blackboard Log Tool", layout="wide")

# Inject custom CSS to hide sidebar navigation
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# Display Anthology logo above the sidebar header
logo_url = "https://logos-world.net/wp-content/uploads/2024/09/Anthology-Symbol.png"
st.sidebar.image(logo_url, use_container_width=True)


# Sidebar navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Download Logs", "Convert Logs", "Search Logs"])

# Page routing
if page == "Download Logs":
    import pages.download as download_page
    download_page.run()
elif page == "Convert Logs":
    import pages.convert as convert_page
    convert_page.run()
elif page == "Search Logs":
    import pages.search as search_page
    search_page.run()
