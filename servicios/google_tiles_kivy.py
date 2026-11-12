"""Adaptador Google Map Tiles para el widget MapView de Kivy.

No usa el método Downloader.download_tile, porque este escribe las
imágenes en disco. En su lugar, Downloader.submit aporta su executor
y despacha texturas en el hilo principal. Las teselas están únicamente
en memoria mientras se renderizan (política de Google Map Tiles).
"""
from io import BytesIO

from kivy.core.image import Image as CoreImage
from kivy_garden.mapview import MapSource
from kivy_garden.mapview.downloader import Downloader

from servicios.google_tiles_api import ErrorMapTiles


class GoogleTilesSource(MapSource):
    """MapSource intercambiable: la navegación y los marcadores se conservan."""

    def __init__(self, cliente, al_fallar=None, creditos="Google Maps"):
        super().__init__(
            url="https://tile.googleapis.com/v1/2dtiles/{z}/{x}/{y}",
            cache_key="google-tiles-no-persistent-cache",
            min_zoom=2,
            max_zoom=20,
            tile_size=256,
            image_ext=cliente.formato,
            attribution="Google Maps",
        )
        self.cliente = cliente
        self.al_fallar = al_fallar
        self.creditos = creditos
        self._fallo_reportado = False

    def fill_tile(self, tile):
        if tile.state == "done":
            return
        # Downloader.submit() ejecuta el trabajo fuera del hilo UI y
        # devuelve el resultado al Kivy Clock sin guardar archivo.
        Downloader.instance().submit(self._descargar, tile)

    def _descargar(self, tile):
        if tile.state == "done":
            return
        try:
            # MapView usa Y desde abajo; Google usa Y desde arriba.
            y_google = self.get_row_count(tile.zoom) - tile.tile_y - 1
            datos = self.cliente.mosaico(tile.zoom, tile.tile_x, y_google)
            return self._aplicar, (tile, datos)
        except ErrorMapTiles as exc:
            return self._fallo, (str(exc),)
        except Exception:
            return self._fallo, ("No se pudo mostrar Google Maps.",)

    def _aplicar(self, tile, datos):
        if tile.state == "done" or tile.map_source is not self:
            return
        try:
            # La textura se crea en el hilo principal; jamás se guarda
            # la imagen de Google en la caché por defecto de MapView.
            imagen = CoreImage(BytesIO(datos), ext=self.cliente.formato)
            tile.texture = imagen.texture
            tile.state = "need-animation"
        except Exception:
            self._fallo("No se pudo decodificar una imagen de Google Maps.")

    def _fallo(self, mensaje):
        if self._fallo_reportado:
            return
        self._fallo_reportado = True
        if self.al_fallar is not None:
            self.al_fallar(mensaje)
