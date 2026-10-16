import os
import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "sakura_dist"))
os.makedirs(_COMPONENT_DIR, exist_ok=True)

# Declare component once at module import
_sakura_component = components.declare_component("sakura_game", path=_COMPONENT_DIR)

def render_sakura_game(key: str = "sakura_game_instance"):
    """Renders the 3D game component and returns user actions (e.g. 'dashboard', 'signout')."""
    return _sakura_component(key=key, default=None)
