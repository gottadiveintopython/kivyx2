def _init():
    from kivy.factory import Factory
    from kivy.core.window import Window
    from ._install import install_on_window, install_on_factory
    install_on_window(Window)
    install_on_factory(Factory)


_init()
