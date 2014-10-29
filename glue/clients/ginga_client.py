import logging

import numpy as np

from ..core.exceptions import IncompatibleAttribute
from ..core.util import color2rgb
from ..core.util import Pointer

from .image_client import ImageClient
from .ds9norm import DS9Normalize
from .layer_artist import (ChangedTrigger, LayerArtist, RGBImageLayerBase,
                           ImageLayerBase, SubsetImageLayerBase)

from ginga.util import wcsmod
wcsmod.use('astropy')
from ginga.ImageViewCanvas import Image
from ginga import AstroImage, RGBImage


class GingaClient(ImageClient):

    def __init__(self, data, canvas=None, artist_container=None):
        super(GingaClient, self).__init__(data, artist_container)
        self._setup_ginga(canvas)

    def _setup_ginga(self, canvas):

        if canvas is None:
            raise ValueError("GingaClient needs a canvas")

        self._canvas = canvas
        self._wcs = None

    def _new_rgb_layer(self, layer):
        return RGBGingaImageLayer(layer, self._canvas)

    def _new_subset_image_layer(self, layer):
        return GingaSubsetImageLayer(layer, self._canvas)

    def _new_image_layer(self, layer):
        return GingaImageLayer(layer, self._canvas)

    def _new_scatter_layer(self, layer):
        pass

    def _update_axis_labels(self):
        pass

    def set_cmap(self, cmap):
        self._canvas.set_cmap(cmap)


class GingaLayerArtist(LayerArtist):
    zorder = Pointer('_zorder')
    visible = Pointer('_visible')

    def __init__(self, layer, canvas):
        # Note: a bit ugly here, canvas gets assigned to self._axes
        #       by superclass. This doesn't actually do anything harmful
        #       right now, but it's a hack.
        super(GingaLayerArtist, self).__init__(layer, canvas)
        self._canvas = canvas
        self._visible = True

    def redraw(self):
        self._canvas.redraw()

    def _sync_style(self):
        pass


class GingaImageLayer(GingaLayerArtist, ImageLayerBase):

    # unused by Ginga
    cmap = None
    norm = None

    def __init__(self, layer, canvas):
        super(GingaImageLayer, self).__init__(layer, canvas)
        self._override_image = None
        self._tag = "layer%s" % (str(layer.label))
        self._img = None
        self._aimg = None

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value
        if not value:
            self.clear()
        elif self._aimg:
            #self._canvas.add(self._nimg, tag=self._tag, redraw=True)
            self._canvas.set_image(self._aimg)

    def set_norm(self, **kwargs):
        # NOP for ginga
        pass

    def clear_norm(self):
        # NOP for ginga
        pass

    def override_image(self, image):
        """Temporarily show a different image"""
        self._override_image = image

    def clear_override(self):
        self._override_image = None

    def clear(self):
        # remove previously added image
        try:
            #self._canvas.deleteObjectsByTag([self._tag], redraw=False)
            self._canvas.deleteObjectsByTag(['_image'], redraw=False)
        except:
            pass

    @property
    def enabled(self):
        return self._aimg is not None

    def update(self, view, transpose=False):
        """
        to fix:
        view is downsampled/cropped. Let ginga do this
        check if we can skip this depending on attribute, data
        """

        self.clear()

        # TODO: check visibility

        if self._override_image is not None:
            data = self.override_image
        else:
            data = self._layer[view]
            if transpose:
                data = data.T

        self._aimg = AstroImage.AstroImage(data_np=data)

        hdr = self._layer.coords._header
        self._aimg.update_keywords(hdr)

        x_pos = y_pos = 0
        if self._visible:
            self._canvas.set_image(self._aimg)


class GingaSubsetImageLayer(GingaLayerArtist, SubsetImageLayerBase):

    def __init__(self, layer, canvas):
        super(GingaSubsetImageLayer, self).__init__(layer, canvas)
        self._img = None
        self._cimg = None
        self._tag = "layer%s" % (str(layer.label))
        self._visible = True
        self._enabled = True

    @property
    def visible(self):
        return self._visible

    @property
    def enabled(self):
        return self._enabled

    @visible.setter
    def visible(self, value):
        self._visible = value
        if not value:
            self.clear()
        elif self._cimg:
            self._canvas.add(self._cimg, tag=self._tag, redraw=True)

    def clear(self):
        try:
            self._canvas.deleteObjectsByTag([self._tag], redraw=True)
        except:
            pass

    def _compute_img(self, view, transpose=False):
        subset = self.layer
        logging.getLogger(__name__).debug("View into subset %s is %s", self.layer, view)

        try:
            mask = subset.to_mask(view[1:])
        except IncompatibleAttribute as exc:
            self.disable_invalid_attributes(*exc.args)
            return False
        logging.getLogger(__name__).debug("View mask has shape %s", mask.shape)

        # shortcut for empty subsets
        if not mask.any():
            return None

        if transpose:
            mask = mask.T

        r, g, b = color2rgb(self.layer.style.color)

        if self._img and self._img.get_data().shape[:2] == mask.shape[:2]:
            # optimization to simply update the color overlay if it already
            # exists and is the correct size
            data = self._img.get_data()
            data[..., 3] = 127 * mask
            data[..., 0] = 255 * r
            data[..., 1] = 255 * g
            data[..., 2] = 255 * b

            return self._img

        # create new color image overlay
        ones = np.ones(mask.shape)
        clr_img = np.dstack((r * ones, g * ones, b * ones, mask * .5))
        clr_img = (255 * clr_img).astype(np.uint8)

        rgbimg = RGBImage.RGBImage(data_np=clr_img)

        self._img = rgbimg

        return self._img

    def update(self, view, transpose=False):
        # remove previously added image
        self.clear()
        self._enabled = True

        im = self._compute_img(view, transpose)
        if not im:
            self._enabled = False
            self.redraw()
            return
        # lower z-order in the back
        # TODO: check for z-order

        x_pos = y_pos = 0
        # TODO: how should we decide the alpha?
        self._cimg = Image(x_pos, y_pos, im, alpha=0.5,
                           flipy=False)
        if self._visible:
            self._canvas.add(self._cimg, tag=self._tag, redraw=True)


class RGBGingaImageLayer(GingaLayerArtist, RGBImageLayerBase):
    r = ChangedTrigger(None)
    g = ChangedTrigger(None)
    b = ChangedTrigger(None)

    rnorm = gnorm = bnorm = None

    contrast_layer = Pointer('_contrast_layer')
    layer_visible = Pointer('_layer_visible')

    def __init__(self, layer, canvas, last_view=None):
        super(RGBGingaImageLayer, self).__init__(layer, canvas)
        self.contrast_layer = 'green'
        self.layer_visible = dict(red=True, green=True, blue=True)
        self._aimg = None

    @property
    def norm(self):
        return getattr(self, self.contrast_layer[0] + 'norm')

    @norm.setter
    def norm(self, value):
        setattr(self, self.contrast_layer[0] + 'norm', value)

    def set_norm(self, **kwargs):
        norm = self.norm or DS9Normalize()

        for k, v in kwargs:
            setattr(norm, k, v)

        self.norm = norm

    def update(self, view=None, transpose=None):
        self.clear()

        rgb = []
        shp = self.layer.shape
        for att, norm, ch in zip([self.r, self.g, self.b],
                                 [self.rnorm, self.gnorm, self.bnorm],
                                 ['red', 'green', 'blue']):
            if att is None or not self.layer_visible[ch]:
                rgb.append(np.zeros(shp))
                continue

            data = self.layer[att]
            norm = norm or DS9Normalize()
            data = norm(data)

            rgb.append(data)

        self._aimg = AstroImage.AstroImage(data_np=np.dstack(rgb))
        hdr = self._layer.coords._header
        self._aimg.update_keywords(hdr)

        if self._visible:
            self._canvas.set_image(self._aimg)
