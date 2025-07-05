# app.py - Main Application File

import streamlit as st
from config import PAGE_CONFIG, APP_TITLE
from utils import setup_page_config

# Setup page configuration
setup_page_config(st, PAGE_CONFIG)

# Main app content
st.title(APP_TITLE)

from views.main import run_app

run_app()
