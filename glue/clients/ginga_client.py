import logging
from time import time

import numpy as np

from ..core.exceptions import IncompatibleAttribute
from ..core.util import Pointer, view_shape, stack_view, split_component_view, color2rgb

from .image_client import ImageClient
from .ds9norm import DS9Normalize
from .layer_artist import (ChangedTrigger, LayerArtistBase, RGBImageLayerBase,
                           ImageLayerBase, SubsetImageLayerBase)

from ginga.util import wcsmod
from ginga.misc import Bunch

wcsmod.use('astropy')
from ginga.ImageViewCanvas import Image
from ginga import AstroImage, BaseImage


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


class GingaLayerArtist(LayerArtistBase):
    zorder = Pointer('_zorder')
    visible = Pointer('_visible')

    def __init__(self, layer, canvas):
        super(GingaLayerArtist, self).__init__(layer)
        self._canvas = canvas
        self._visible = True

    def redraw(self, whence=0):
        self._canvas.redraw(whence=whence)

    def _sync_style(self):
        pass


class GingaImageLayer(GingaLayerArtist, ImageLayerBase):

    # unused by Ginga
    cmap = None
    norm = None

    def __init__(self, layer, canvas):
        super(GingaImageLayer, self).__init__(layer, canvas)
        self._override_image = None
        self._tag = "layer%s_%s" % (layer.label, time())
        self._img = None  # DataImage instance
        self._enabled = True

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        if self._visible == value:
            return

        self._visible = value
        if not value:
            self.clear()
        elif self._img:
            self._canvas.set_image(self._img)

    def set_norm(self, **kwargs):
        # NOP for ginga
        pass

    def clear_norm(self):
        # NOP for ginga
        pass

    def override_image(self, image):
        """Temporarily show a different image"""
        print 'set override image'
        self._override_image = image

    def clear_override(self):
        self._override_image = None

    def clear(self):
        # remove previously added image
        try:
            self._canvas.deleteObjectsByTag(['_image'], redraw=False)
        except:
            pass

    @property
    def enabled(self):
        return self._enabled

    def update(self, view, transpose=False):
        if not self.visible:
            return

        # update ginga model
        comp, view = split_component_view(view)

        if self._img is None:
            self._img = DataImage(self.layer, comp, view, transpose)
            self._canvas.set_image(self._img)

        self._img.data = self.layer
        self._img.component = comp
        self._img.view = view
        self._img.transpose = transpose
        self._img.override_image = self._override_image

        self.redraw()


class GingaSubsetImageLayer(GingaLayerArtist, SubsetImageLayerBase):

    def __init__(self, layer, canvas):
        super(GingaSubsetImageLayer, self).__init__(layer, canvas)
        self._img = None
        self._cimg = None
        self._tag = "layer%s_%s" % (layer.label, time())
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
        if value is self._visible:
            return

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

    def _update_ginga_models(self, view, transpose=False):
        subset = self.layer
        logging.getLogger(__name__).debug("View into subset %s is %s", self.layer, view)

        _, view = split_component_view(view)  # discard ComponentID
        r, g, b = color2rgb(self.layer.style.color)

        if self._img is None:
            self._img = SubsetImage(subset, view)
        if self._cimg is None:
            # XXX for some reason we need to wrap inside Image, or ginga
            #     complains about missing methods. Check to se
            #     if there's a better way
            self._cimg = Image(0, 0, self._img, alpha=0.5, flipy=False)

        self._img.view = view
        self._img.color = (r, g, b)
        self._img.transpose = transpose

    def _check_enabled(self):
        """
        Sync the enabled/disabled status, based on whether
        mask is computable
        """
        self._enabled = True
        try:
            # the first pixel
            view = tuple(0 for _ in self.layer.data.shape)
            self.layer.to_mask(view)
        except IncompatibleAttribute as exc:
            self._enabled = False
            self.disable_invalid_attributes(*exc.args)

    def update(self, view, transpose=False):
        self.clear()

        self._check_enabled()
        self._update_ginga_models(view, transpose)

        # XXX can skip remove/re-add
        # use getObjectByTag(self, tag) to check if layer is present
        if self._enabled and self._visible:
            self._canvas.add(self._cimg, tag=self._tag, redraw=False)

        self.redraw(whence=2)


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


def forbidden(*args):
    raise ValueError("Forbidden")


class DataImage(AstroImage.AstroImage):

    """
    A Ginga image subclass to interface with Glue Data objects
    """
    get_data = _get_data = copy_data = set_data = get_array = transfer = forbidden

    def __init__(self, data, component, view, transpose=False,
                 override_image=None, **kwargs):
        """
        Parameters
        ----------
        data : glue.core.data.Data
            The data to image
        component : glue.core.data.ComponentID
            The ComponentID in the data to image
        view : numpy-style view
            The view into the data to image. Must produce a 2D array
        transpose : bool
            Whether to transpose the view
        override_image : numpy array (optional)
            Whether to show override_image instead of the view into the data.
            The override image must have the same shape as the 2D view into
            the data.
        kwargs : dict
            Extra kwargs are passed to the superclass
        """
        self.transpose = transpose
        self.view = view
        self.data = data
        self.component = component
        self.override_image = None
        super(DataImage, self).__init__(**kwargs)

    @property
    def shape(self):
        """
        The shape of the 2D view into the data
        """
        result = view_shape(self.data.shape, self.view)
        if self.transpose:
            result = result[::-1]
        return result

    def _get_fast_data(self):
        return self._slice((slice(None, None, 10), slice(None, None, 10)))

    def _slice(self, view):
        """
        Extract a view from the 2D image.
        """
        if self.override_image is not None:
            return self.override_image[view]

        # Combining multiple views: First a 2D slice into an ND array, then
        # the requested view from this slice
        if self.transpose:
            views = [self.view, 'transpose', view]
        else:
            views = [self.view, view]
        view = stack_view(self.data.shape, *views)
        return self.data[self.component, view]


class SubsetImage(BaseImage.BaseImage):

    """
    A Ginga image subclass to interface with Glue subset objects
    """
    get_data = _get_data = copy_data = set_data = get_array = transfer = forbidden

    def __init__(self, subset, view, color=(0, 1, 0), transpose=False, **kwargs):
        """
        Parameters
        ----------
        subset : glue.core.subset.Subset
            The subset to image
        view : numpy-style view
            The view into the subset to image. Must produce a 2D array
        color : tuple of 3 floats in range [0, 1]
            The color to image the subset as
        transpose : bool
            Whether to transpose the view
        kwargs : dict
            Extra kwargs are passed to the ginga superclass
        """
        super(SubsetImage, self).__init__(**kwargs)
        self.subset = subset
        self.view = view
        self.transpose = transpose
        self.color = color
        self.order = 'RGBA'

    @property
    def shape(self):
        """
        Shape of the 2D view into the subset mask
        """
        result = view_shape(self.subset.data.shape, self.view)
        if self.transpose:
            result = result[::-1]
        return tuple(list(result) + [4])  # 4th dim is RGBA channels

    def _rgb_from_mask(self, mask):
        """
        Turn a boolean mask into a 4-channel RGBA image
        """
        r, g, b = self.color
        ones = mask * 0 + 255
        alpha = mask * 127
        result = np.dstack((ones * r, ones * g, ones * b, alpha)).astype(np.uint8)
        return result

    def _get_fast_data(self):
        return self._slice((slice(None, None, 10), slice(None, None, 10)))

    def _slice(self, view):
        """
        Extract a view from the 2D subset mask.
        """
        # Combining multiple views: First a 2D slice into an ND array, then
        # the requested view from this slice

        if self.transpose:
            views = [self.view, 'transpose', view]
        else:
            views = [self.view, view]
        view = stack_view(self.subset.data.shape, *views)

        mask = self.subset.to_mask(view)
        return self._rgb_from_mask(mask)

    def _set_minmax(self):
        # we already know the data bounds
        self.minval = 0
        self.maxval = 256
        self.minval_noinf = self.minval
        self.maxval_noinf = self.maxval

    def get_scaled_cutout_wdht(self, x1, y1, x2, y2, new_wd, new_ht):

        # default implementation if downsampling
        if new_wd <= (x2 - x1 + 1) or new_ht <= (y2 - y1 + 1):
            return super(SubsetImage, self).get_scaled_cutout_wdht(x1, y1, x2, y2, new_wd, new_ht)

        # if upsampling, prevent extra to_mask() computation
        x1, x2 = np.clip([x1, x2], 0, self.width - 2).astype(np.int)
        y1, y2 = np.clip([y1, y2], 0, self.height - 2).astype(np.int)

        result = self._slice(np.s_[y1:y2 + 1, x1:x2 + 1])

        yi = np.linspace(0, result.shape[0], new_ht).astype(np.int).reshape(-1, 1).clip(0, result.shape[0] - 1)
        xi = np.linspace(0, result.shape[1], new_wd).astype(np.int).reshape(1, -1).clip(0, result.shape[1] - 1)
        yi, xi = [np.array(a) for a in np.broadcast_arrays(yi, xi)]
        result = result[yi, xi]

        scale_x = 1.0 * result.shape[1] / (x2 - x1 + 1)
        scale_y = 1.0 * result.shape[0] / (y2 - y1 + 1)

        return Bunch.Bunch(data=result, scale_x=scale_x, scale_y=scale_y)
