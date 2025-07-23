
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

class ClaveUnica:
    """Represents the credentials for Clave Unica login."""

    def __init__(self, rut, password):
        self.rut = rut
        self._password = password
