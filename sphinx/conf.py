# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib.metadata

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = 'kivyx'
copyright = '2025, Mitō Nattōsai'
author = 'Mitō Nattōsai'
release = importlib.metadata.version(project)

rst_epilog = """
.. |ja| replace:: 🇯🇵
"""

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    # 'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
language = 'en'
add_module_names = False
gettext_auto_build = False
gettext_location = False


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "alabaster"
html_static_path = ['_static']


# -- Options for todo extension ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/todo.html#configuration
todo_include_todos = True


# -- Options for intersphinx extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'kivy': ('https://kivy.org/doc/master', None),
}


# -- Options for autodoc extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#configuration
autodoc_mock_imports = ['kivy', ]
autodoc_default_options = {
   'members': True,
   'undoc-members': True,
   'no-show-inheritance': True,
   'exclude-members': "on_touch_down, on_touch_move, on_touch_up, on_motion, to_local, to_parent, to_window, to_widget, collide_point, __init__",
}
autodoc_class_signature = 'separated'
# autodoc_preserve_defaults = True
