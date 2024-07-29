import numpy as np
import matplotlib.pyplot as plt

from matplotlib.colors import Colormap, Normalize, LogNorm, CenteredNorm, SymLogNorm
from matplotlib.cm import ScalarMappable
from matplotlib.collections import QuadMesh
from matplotlib import patches
from abc import ABC, abstractmethod
from nap_plot_tools.cmap import cat10_mod_cmap, cat10_mod_cmap_first_transparent
from psygnal import Signal
from typing import Tuple, List, Union
from collections import defaultdict
import warnings

from biaplotter.colormap import BiaColormap


class Artist(ABC):
    """Abstract base class for artists in the BiAPlotter.

    Parameters
    ----------
    ax : plt.Axes, optional
        axes to plot on, by default None
    data : (N, 2) np.ndarray
        data to be plotted
    overlay_colormap : Colormap, optional
        a colormap to use for the artist, by default cat10_mod_cmap from nap-plot-tools
    color_indices : (N,) np.ndarray, optional
        array of indices to map to the colormap, by default None
    """

    def __init__(self, ax: plt.Axes = None, data: np.ndarray = None, overlay_colormap: Colormap = cat10_mod_cmap, color_indices: np.ndarray = None):
        """Initializes the abstract artist.
        """
        #: Stores data to be plotted
        self._data: np.ndarray = data
        #: Stores axes to plot on
        self.ax: plt.Axes = ax if ax is not None else plt.gca()
        #: Stores visibility of the artist
        self._visible: bool = True
        #: Stores the colormap to use for the artist
        self._overlay_colormap: Colormap = BiaColormap(overlay_colormap)
        #: Stores the array of indices to map to the colormap
        self._color_indices: np.array = color_indices

    @property
    @abstractmethod
    def data(self) -> np.ndarray:
        """Abstract property for the artist's data."""
        pass

    @data.setter
    @abstractmethod
    def data(self, value: np.ndarray):
        """Abstract setter for the artist's data."""
        pass

    @property
    @abstractmethod
    def visible(self) -> bool:
        """Abstract property for the artist's visibility."""
        pass

    @visible.setter
    @abstractmethod
    def visible(self, value: bool):
        """Abstract setter for the artist's visibility."""
        pass

    @property
    @abstractmethod
    def color_indices(self) -> np.ndarray:
        """Abstract property for the indices into the colormap."""
        pass

    @color_indices.setter
    @abstractmethod
    def color_indices(self, indices: np.ndarray):
        """Abstract setter for the indices into the colormap."""
        pass

    @abstractmethod
    def draw(self):
        """Abstract method to draw or redraw the artist."""
        pass


class Scatter(Artist):
    """Scatter plot artist for the BiAPlotter.

    Inherits all parameters and attributes from abstract Artist.
    For parameter and attribute details, see the abstract Artist class documentation.

    Parameters
    ----------
    ax : plt.Axes, optional
        axes to plot on, by default None
    data : (N, 2) np.ndarray
        data to be plotted
    overlay_colormap : Colormap, optional
        a colormap to use for the artist, by default cat10_mod_cmap from nap-plot-tools
    color_indices : (N,) np.ndarray[int] or int, optional
        array of indices to map to the colormap, by default None

    Notes
    -----
    **Signals:**

        * **data_changed_signal** emitted when the data is changed.
        * **color_indices_changed_signal** emitted when the color indices are changed.

    Examples
    --------
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> from biaplotter.artists import Scatter
    >>> data = np.random.rand(100, 2)
    >>> fig, ax = plt.subplots()
    >>> scatter = Scatter(ax)
    >>> scatter.data = data
    >>> scatter.visible = True
    >>> scatter.color_indices = np.linspace(start=0, stop=5, num=100, endpoint=False, dtype=int)
    >>> plt.show()
    """
    #: Signal emitted when the `data` is changed.
    data_changed_signal: Signal = Signal(np.ndarray)
    #: Signal emitted when the `color_indices` are changed.
    color_indices_changed_signal: Signal = Signal(np.ndarray)

    def __init__(self, ax: plt.Axes = None, data: np.ndarray = None, overlay_colormap: Colormap = cat10_mod_cmap, color_indices: np.ndarray = None):
        """Initializes the scatter plot artist.
        """
        super().__init__(ax, data, overlay_colormap, color_indices)
        #: Stores the scatter plot matplotlib object
        self._scatter = None
        self._normalization_methods = {
            'linear': Normalize, 'log': LogNorm, 'symlog': SymLogNorm, 'centered': CenteredNorm}
        self._color_normalization_method = 'linear'
        self.data = data
        self._size = 50  # Default size
        self.draw()  # Initial draw of the scatter plot

    @property
    def data(self) -> np.ndarray:
        """Gets or sets the data associated with the scatter plot.

        Updates colors if color_indices are set. Triggers a draw idle command.

        Returns
        -------
        data : (N, 2) np.ndarray
           data for the artist. Does not respond if set to None or empty array.

        Notes
        -----
        data_changed_signal : Signal
            Signal emitted when the data is changed.
        """
        return self._data

    @data.setter
    def data(self, value: np.ndarray):
        """Sets the data for the scatter plot, updating the display as needed."""
        if value is None:
            return
        if len(value) == 0:
            return
        self._data = value
        # emit signal
        self.data_changed_signal.emit(self._data)
        if self._scatter is None:
            self._scatter = self.ax.scatter(value[:, 0], value[:, 1], s=self._size)
            self.color_indices = 0  # Set default color index
        else:
            # If the scatter plot already exists, just update its data
            self._scatter.set_offsets(value)

        if self._color_indices is None:
            self.color_indices = 0  # Set default color index
        else:
            # Update colors if color indices are set, resize if data shape has changed
            color_indices_size = len(self._color_indices)
            color_indices = np.resize(self._color_indices, self._data.shape[0])
            if len(color_indices) > color_indices_size:
                # fill with zeros where new data is larger
                color_indices[color_indices_size:] = 0
            self.color_indices = color_indices
        self.size = 50
        self.draw()

    @property
    def visible(self) -> bool:
        """Gets or sets the visibility of the scatter plot.

        Triggers a draw idle command.

        Returns
        -------
        visible : bool
            visibility of the scatter plot.
        """
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        """Sets the visibility of the scatter plot."""
        self._visible = value
        if self._scatter is not None:
            self._scatter.set_visible(value)
        self.draw()

    @property
    def color_indices(self) -> np.ndarray:
        """Gets or sets the current color indices used for the scatter plot.

        Triggers a draw idle command.

        Returns
        -------
        color_indices : (N,) np.ndarray[int] or int
            indices to map to the overlay_colormap. Accepts a scalar or an array of integers.

        Notes
        -----
        color_indices_changed_signal : Signal
            Signal emitted when the color indices are changed.

        """
        return self._color_indices

    

    @color_indices.setter
    def color_indices(self, indices: np.ndarray):
        """Sets color indices for the scatter plot and updates colors accordingly."""
        # Check if indices are a scalar
        if np.isscalar(indices):
            indices = np.full(len(self._data), indices)
        self._color_indices = indices
        if indices is not None and self._scatter is not None:
            norm_class = self._normalization_methods[self._color_normalization_method]
            # If overlay_colormap is categorical, normalize to colormap range
            if self.overlay_colormap.categorical:
                if self._color_indices.dtype != int:
                    warnings.warn(
                        'Color indices must be integers for categorical colormap. Change `overlay_colormap` to a continuous colormap or set `color_indices` to integers.')
                if self._color_normalization_method != 'linear':
                    warnings.warn(
                        'Categorical colormap detected. Setting color normalization method to linear.')
                    self._color_normalization_method = 'linear'
                norm = Normalize(vmin=0, vmax=self.overlay_colormap.N)
            else:
                with warnings.catch_warnings():
                    # If array is all NaN, ignore warning since it will be displayed transparent
                    warnings.filterwarnings(
                        'ignore', r'All-NaN slice encountered')
                    if self._color_normalization_method == 'log':
                        min_value = np.nanmin(self._color_indices)
                        if min_value <= 0:
                            min_value = 0.01
                        norm = norm_class(vmin=min_value, vmax=np.nanmax(self._color_indices))
                        warnings.warn(
                            f'Log normalization applied to color indices with min value {min_value}. Values below 0.01 were set to 0.01.')
                        indices[indices <= 0] = min_value
                    elif self._color_normalization_method == 'centered':
                        norm = norm_class(vcenter=np.nanmean(self._color_indices))
                    elif self._color_normalization_method == 'symlog':
                        norm = norm_class(vmin=np.nanmin(self._color_indices), vmax=np.nanmax(self._color_indices), linthresh=0.03)
                    else:
                        norm = norm_class(vmin=np.nanmin(self._color_indices), vmax=np.nanmax(self._color_indices))

            # Create a ScalarMappable instance using chosen colormap and normalization
            sm = ScalarMappable(norm=norm, cmap=self.overlay_colormap.cmap)
            # Convert normalized data to RGBA
            rgba_colors = sm.to_rgba(indices)
            self._scatter.set_facecolor(rgba_colors)
            self._scatter.set_edgecolor(None)
        # emit signal
        self.color_indices_changed_signal.emit(self._color_indices)
        self.draw()

    @property
    def overlay_colormap(self) -> BiaColormap:
        """Gets or sets the overlay colormap for the scatter plot.

        Returns
        -------
        overlay_colormap : BiaColormap
            colormap for the scatter plot with a `categorical` attribute.
        """
        return self._overlay_colormap
    
    @overlay_colormap.setter
    def overlay_colormap(self, value: Colormap):
        """Sets the overlay colormap for the scatter plot."""
        self._overlay_colormap = BiaColormap(value)
        self.color_indices = self._color_indices

    @property
    def color_normalization_method(self) -> str:
        """Gets or sets the normalization method for the color indices.

        Returns
        -------
        color_normalization_method : str
            the normalization method for the color indices.
        """
        return self._color_normalization_method

    @color_normalization_method.setter
    def color_normalization_method(self, value: str):
        """Sets the normalization method for the color indices."""
        self._color_normalization_method = value
        self.color_indices = self._color_indices

    @property
    def size(self) -> Union[float, np.ndarray]:
        """Gets or sets the size of the points in the scatter plot.

        Triggers a draw idle command.

        Returns
        -------
        size : float or (N,) np.ndarray[float]
            size of the points in the scatter plot. Accepts a scalar or an array of floats.
        """
        return self._size

    @size.setter
    def size(self, value: Union[float, np.ndarray]):
        """Sets the size of the points in the scatter plot."""
        self._size = value
        if self._scatter is not None:
            self._scatter.set_sizes(np.full(len(self._data), value) if np.isscalar(value) else value)
        self.draw()

    def draw(self):
        """Draws or redraws the scatter plot."""
        self.ax.figure.canvas.draw_idle()


class Histogram2D(Artist):
    """2D histogram artist for the BiAPlotter.

    Inherits all parameters and attributes from abstract Artist.
    For parameter and attribute details, see the abstract Artist class documentation.

    Parameters
    ----------
    ax : plt.Axes, optional
        axes to plot on, by default None
    data : (N, 2) np.ndarray
        data to be plotted
    overlay_colormap : Colormap, optional
        a colormap to use for the artist overlay, by default cat10_mod_cmap_first_transparent from nap-plot-tools (first color is transparent)
    color_indices : (N,) np.ndarray[int] or int, optional
        array of indices to map to the overlay_colormap, by default None
    bins : int, optional
        number of bins for the histogram, by default 20
    histogram_colormap : Colormap, optional
        colormap for the histogram, by default plt.cm.magma

    Notes
    -----
    **Signals:**

        * **data_changed_signal** emitted when the data is changed.
        * **color_indices_changed_signal** emitted when the color indices are changed.

    """
    #: Signal emitted when the `data` is changed.
    data_changed_signal: Signal = Signal(np.ndarray)
    #: Signal emitted when the `color_indices` are changed.
    color_indices_changed_signal: Signal = Signal(np.ndarray)

    def __init__(self, ax: plt.Axes = None, data: np.ndarray = None, overlay_colormap: Colormap = cat10_mod_cmap_first_transparent, color_indices: np.ndarray = None, bins=20, histogram_colormap: Colormap = plt.cm.magma):
        super().__init__(ax, data, overlay_colormap, color_indices)
        """Initializes the 2D histogram artist.
        """
        #: Stores the matplotlib histogram2D object
        self._histogram_image = None
        self._bins = bins
        self._histogram_colormap = BiaColormap(histogram_colormap)
        self._overlay_colormap = BiaColormap(overlay_colormap)
        self._histogram_interpolation = 'nearest'
        self._overlay_interpolation = 'nearest'
        self._overlay_opacity = 1
        self._overlay_visible = True
        self._overlay_histogram_image = None
        self._normalization_methods = {
            'linear': Normalize, 'log': LogNorm, 'symlog': SymLogNorm, 'centered': CenteredNorm}
        self._histogram_color_normalization_method = 'linear'
        self._overlay_color_normalization_method = 'linear'
        self.data = data
        self.draw()  # Initial draw of the histogram

    @property
    def data(self) -> np.ndarray:
        """Gets or sets the data associated with the 2D histogram.

        Updates colors if color_indices are set. Triggers a draw idle command.

        Returns
        -------
        data : (N, 2) np.ndarray
            data for the artist. Does not respond if set to None or empty array.

        Notes
        -----
        data_changed_signal : Signal
            Signal emitted when the data is changed.
        """
        return self._data

    @data.setter
    def data(self, value: np.ndarray):
        """Sets the data for the 2D histogram, updating the display as needed."""
        if value is None:
            return
        if len(value) == 0:
            return
        self._data = value
        # emit signal
        self.data_changed_signal.emit(self._data)
        # Remove the existing histogram to redraw
        if self._histogram_image is not None:
            self._histogram_image.remove()
        # Calculate and draw the new histogram
        self._histogram = np.histogram2d(
            value[:, 0], value[:, 1], bins=self._bins)
        counts, x_edges, y_edges = self._histogram
        self._histogram_rgba = self._histogram2D_array_to_rgba(
            self.ax, counts, x_edges, y_edges, is_overlay=False)
        self._histogram_image = self.ax.imshow(self._histogram_rgba, extent=[
                                               x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]], origin='lower', zorder=1, interpolation=self._histogram_interpolation, alpha=1)

        if self._color_indices is None:
            self.color_indices = 0  # Set default color index
        else:
            # Update colors if color indices are set, resize if data shape has changed
            color_indices_size = len(self._color_indices)
            color_indices = np.resize(self._color_indices, self._data.shape[0])
            if len(color_indices) > color_indices_size:
                # Fill with zeros where new data is larger
                color_indices[color_indices_size:] = 0
            self.color_indices = color_indices            
        self.draw()

    @property
    def visible(self) -> bool:
        """Gets or sets the visibility of the 2D histogram.

        Triggers a draw idle command.

        Returns
        -------
        visible : bool
            visibility of the 2D histogram.
        """
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        """Sets the visibility of the 2D histogram."""
        self._visible = value
        if self._histogram_image is not None:
            artist = self._histogram_image
            artist.set_visible(value)
            if self._overlay_histogram_image is not None:
                self._overlay_histogram_image.set_visible(value)
        self.draw()

    @property
    def color_indices(self) -> np.ndarray:
        """Gets or sets the current color indices used for the 2D histogram underlying data.

        Triggers a draw idle command.

        Returns
        -------
        color_indices : (N,) np.ndarray[int] or int
            indices to map to the overlay colormap. Accepts a scalar or an array.

        Notes
        -----
        color_indices_changed_signal : Signal
            Signal emitted when the color indices are changed.

        """
        return self._color_indices

    @color_indices.setter
    def color_indices(self, indices: np.ndarray):
        """Sets color indices for the 2D histogram underlying data and updates colors accordingly."""
        # Check if indices are a scalar
        if np.isscalar(indices):
            indices = np.full(len(self._data), indices)
        self._color_indices = indices
        # Remove the existing overlay to redraw
        if self._overlay_histogram_image is not None:
            self._overlay_histogram_image.remove()
            self._overlay_histogram_image = None
        counts, x_edges, y_edges = self._histogram
        # Get the bin index for each x value ( -1 to start from index 0 and clip to handle edge cases)
        x_bin_indices = (np.digitize(
            self._data[:, 0], x_edges, right=False) - 1).clip(0, len(x_edges)-2)
        # Get the bin index for each y value ( -1 to start from index 0 and clip to handle edge cases)
        y_bin_indices = (np.digitize(
            self._data[:, 1], y_edges, right=False) - 1).clip(0, len(y_edges)-2)
        # Assign median values to the bins (fill with NaNs if no data in the bin)
        statistic_histogram = self._calculate_statistic_histogram(
            x_bin_indices, y_bin_indices, indices, statistic='median')
        if not np.all(np.isnan(statistic_histogram)):
            # Draw the overlay
            self.overlay_histogram_rgba = self._histogram2D_array_to_rgba(
                self.ax, statistic_histogram, x_edges, y_edges, is_overlay=True)
            self._overlay_histogram_image = self.ax.imshow(self.overlay_histogram_rgba,  extent=[
                                                        x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]], origin='lower', zorder=2, interpolation=self._overlay_interpolation, alpha=self._overlay_opacity)

        # emit signal
        self.color_indices_changed_signal.emit(self._color_indices)
        self.draw()

    @property
    def overlay_colormap(self) -> BiaColormap:
        """Gets or sets the overlay colormap for the 2D histogram.

        Returns
        -------
        overlay_colormap : BiaColormap
            colormap for the overlay histogram with a `categorical` attribute.
        """
        return self._overlay_colormap
    
    @overlay_colormap.setter
    def overlay_colormap(self, value: Colormap):
        """Sets the overlay colormap for the 2D histogram."""
        self._overlay_colormap = BiaColormap(value)
        self.color_indices = self._color_indices

    @property
    def histogram_color_normalization_method(self) -> str:
        """Gets or sets the normalization method for the histogram.

        Returns
        -------
        color_normalization_method : str
            the normalization method for the histogram.
        """
        return self._histogram_color_normalization_method

    @histogram_color_normalization_method.setter
    def histogram_color_normalization_method(self, value: str):
        """Sets the normalization method for the histogram."""
        self._histogram_color_normalization_method = value
        # Update histogram image if new color normalization method is set
        self.data = self._data

    @property
    def overlay_color_normalization_method(self) -> str:
        """Gets or sets the normalization method for the overlay histogram.

        Returns
        -------
        overlay_color_normalization_method : str
            the normalization method for the overlay color indices.
        """
        return self._overlay_color_normalization_method
    
    @overlay_color_normalization_method.setter
    def overlay_color_normalization_method(self, value: str):
        """Sets the normalization method for the overlay histogram."""
        self._overlay_color_normalization_method = value
        # Update overlay histogram image if new color normalization method is set
        self.color_indices = self._color_indices

    @property
    def bins(self) -> int:
        """Gets or sets the number of bins for the histogram.

        Returns
        -------
        bins : int
            number of bins for the histogram.
        """
        return self._bins

    @bins.setter
    def bins(self, value: int):
        """Sets the number of bins for the histogram."""
        self._bins = value
        self.data = self._data

    @property
    def histogram_colormap(self) -> Colormap:
        """Gets or sets the colormap for the histogram.

        Returns
        -------
        histogram_colormap : Colormap
            colormap for the histogram.
        """
        return self._histogram_colormap

    @histogram_colormap.setter
    def histogram_colormap(self, value: Colormap):
        """Sets the colormap for the histogram."""
        self._histogram_colormap = BiaColormap(value)
        self.data = self._data

    @property
    def histogram_interpolation(self) -> str:
        """Gets or sets the interpolation method for the histogram.

        Returns
        -------
        histogram_interpolation : str
            interpolation method for the histogram.
        """
        return self._histogram_interpolation

    @histogram_interpolation.setter
    def histogram_interpolation(self, value: str):
        """Sets the interpolation method for the histogram."""
        self._histogram_interpolation = value
        self.data = self._data

    @property
    def overlay_interpolation(self) -> str:
        """Gets or sets the interpolation method for the overlay histogram.

        Returns
        -------
        overlay_interpolation : str
            interpolation method for the overlay histogram.
        """
        return self._overlay_interpolation

    @overlay_interpolation.setter
    def overlay_interpolation(self, value: str):
        """Sets the interpolation method for the overlay histogram."""
        self._overlay_interpolation = value
        self.data = self._data

    @property
    def overlay_opacity(self):
        """Gets or sets the opacity of the overlay histogram.

        Triggers a draw idle command.

        Returns
        -------
        overlay_opacity : float
            opacity of the overlay histogram.
        """
        return self._overlay_opacity

    @overlay_opacity.setter
    def overlay_opacity(self, value):
        """Sets the opacity of the overlay histogram."""
        self._overlay_opacity = value
        self.data = self._data

    @property
    def overlay_visible(self):
        """Gets or sets the visibility of the overlay histogram.

        Triggers a draw idle command.

        Returns
        -------
        overlay_visible : bool
            visibility of the overlay histogram.
        """
        return self._overlay_visible

    @overlay_visible.setter
    def overlay_visible(self, value):
        """Sets the visibility of the overlay histogram."""
        self._overlay_visible = value
        if self._overlay_histogram_image is not None:
            self._overlay_histogram_image.set_visible(value)
        self.draw()

    @property
    def histogram(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, QuadMesh]:
        """Returns the 2D histogram array and edges.

        Returns
        -------
        histogram : Tuple[np.ndarray, np.ndarray, np.ndarray]
            2D histogram, x edges, and y edges.
        """
        return self._histogram

    def indices_in_patches_above_threshold(self, threshold: int) -> List[int]:
        """
        Returns the indices of the points in that fall into the bins
        of the 2D histogram exceeding a specified threshold.

        Parameters
        ----------
        threshold : int
            The count threshold to exceed.

        Returns
        -------
        indices : List[int]
            list of indices of points falling into the exceeding bins.
        """
        histogram, x_edges, y_edges = self._histogram

        # Identify bins that exceed the threshold
        exceeding_bins = np.argwhere(histogram > threshold)

        # Prepare to collect indices
        indices = []

        # For each bin exceeding the threshold...
        for bin_x, bin_y in exceeding_bins:
            # Identify the edges of the current bin
            x_min, x_max = x_edges[bin_x], x_edges[bin_x + 1]
            y_min, y_max = y_edges[bin_y], y_edges[bin_y + 1]

            # Find indices of points within these edges
            bin_indices = np.where((self._data[:, 0] >= x_min) & (self._data[:, 0] < x_max) & (
                self._data[:, 1] >= y_min) & (self._data[:, 1] < y_max))[0]
            indices.extend(bin_indices)

        return indices

    def _calculate_statistic_histogram(self, x_indices, y_indices, features, statistic='median'):
        """
        Calculate either a mean, median or sum "histogram" for provided indices and features.

        This means that in each patch, instead of portraying the count of points, we portray the mean, median or sum of those values.

        Parameters
        ----------
        x_indices : np.ndarray
            indices of the x bins
        y_indices : np.ndarray
            indices of the y bins
        features : np.ndarray
            features to calculate the statistic
        statistic : str
            the statistic to calculate, 'sum', 'mean', or 'median'

        Returns
        -------
        statistic_histogram : np.ndarray
            the calculated statistic histogram
        """
        height = max(x_indices) + 1
        width = max(y_indices) + 1
        statistic_histogram = np.full(
            (height, width), np.nan)  # Initialize with NaNs

        if statistic == 'mean':
            sums = np.zeros((height, width))
            counts = np.zeros((height, width))
            for x, y, feature in zip(x_indices, y_indices, features):
                sums[x, y] += feature
                counts[x, y] += 1
            np.divide(sums, counts, out=statistic_histogram, where=counts != 0)
        elif statistic == 'median':
            feature_lists = defaultdict(list)
            for x, y, feature in zip(x_indices, y_indices, features):
                feature_lists[(x, y)].append(feature)
            for (x, y), feats in feature_lists.items():
                if feats:
                    statistic_histogram[x, y] = np.median(feats)
        elif statistic == 'sum':
            sums = np.zeros((height, width))
            sums_flags = np.zeros((height, width)).astype(bool)
            for x, y, feature in zip(x_indices, y_indices, features):
                if np.isnan(sums[x, y]):
                    # Initialize sum as 0 when first feature is added
                    sums[x, y] = 0
                sums[x, y] += feature
                sums_flags[x, y] = True
            statistic_histogram[sums_flags] = sums[sums_flags]

        return statistic_histogram
    
    def _is_categorical_colormap(self, colormap):
        """
        Check if the colormap is categorical.

        Parameters
        ----------
        colormap : BiaColormap or ColormapLike
            colormap to check.

        Returns
        -------
        bool
            True if the colormap is categorical, False otherwise.
        """
        if hasattr(colormap, 'categorical'):
            return colormap.categorical
        try:
            bia_colormap = BiaColormap(colormap)
            return bia_colormap.categorical
        except ValueError:
            return False

    def _handle_norm_method_for_categorical_colormap(self, is_overlay, colormap, dtype):
        """
        Set the normalization method for the histogram data when the colormap is categorical.

        Parameters
        ----------
        is_overlay : bool
            whether the histogram is an overlay or not.
        colormap : BiaColormap
            colormap to use for the image with `categorical` attribute
        dtype : type
            data type of the histogram data, can be int or float. A categorical colormap expects positive integer color indices.

        Returns
        -------
        norm_class : Normalize
            the normalization class to use for the histogram data (linear normalization for categorical colormap).
        """
        if is_overlay:
            color_normalization_method = self._overlay_color_normalization_method
        else:
            color_normalization_method = self._histogram_color_normalization_method

        if dtype != int:
            # Warn user that categorical colormap expects integer color indices
            warnings.warn(
                f'Color indices must be integers for categorical colormap. Change `{"overlay_" if is_overlay else "histogram_"}colormap` to a continuous colormap or set `color_indices` to integers.')
        if color_normalization_method != 'linear':
            # Warn user that categorical colormap employs linear normalization
            warnings.warn(
                f'Categorical colormap detected in `{"overlay_" if is_overlay else "histogram_"}colormap`. Setting color normalization method to linear.')
            if is_overlay:
                self._overlay_color_normalization_method = 'linear'
            else:
                self._histogram_color_normalization_method = 'linear'
        return Normalize(vmin=0, vmax=colormap.N)


    def _handle_norm_method_for_continuous_colormap(self, is_overlay, norm_class, histogram_data, lintresh_for_symlog=0.03, min_value_for_log=0.01):
        """
        Set the normalization method for the histogram data when the colormap is continuous.

        Parameters
        ----------
        is_overlay : bool
            whether the histogram is an overlay or not.
        norm_class : Normalize
            normalization class to use for the histogram data.
        histogram_data : np.ndarray
            2D histogram data array to be converted to RGBA image.
        lintresh_for_symlog : float, optional
            linear threshold for SymLogNorm, by default 0.03
        min_value_for_log : float, optional
            minimum value for log normalization, by default 0.01

        Returns
        -------
        norm_class : Normalize
            the normalization class to use for the histogram data.
        """
        if is_overlay:
            color_normalization_method = self._overlay_color_normalization_method
        else:
            color_normalization_method = self._histogram_color_normalization_method

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore', r'All-NaN slice encountered')
            if color_normalization_method == 'log':
                min_value = np.nanmin(histogram_data)
                if min_value <= 0:
                    min_value = min_value_for_log
                norm = norm_class(vmin=min_value, vmax=np.nanmax(histogram_data))
                warnings.warn(
                    f'Log normalization applied to color indices with min value {min_value}. Values below 0.01 were set to 0.01.')
                histogram_data[histogram_data <= 0] = min_value
            elif color_normalization_method == 'centered':
                norm = norm_class(vcenter=np.nanmean(histogram_data))
            elif color_normalization_method == 'symlog':
                norm = norm_class(vmin=np.nanmin(histogram_data), vmax=np.nanmax(histogram_data), linthresh=lintresh_for_symlog)
            else:
                norm = norm_class(vmin=np.nanmin(histogram_data), vmax=np.nanmax(histogram_data))
        return norm

    def _get_normalization_class(self, is_overlay):
        """
        Get the normalization class

        Parameters
        ----------
        is_overlay : bool
            whether the histogram is an overlay or not.

        Returns
        -------
        norm_class : Normalize
            the normalization class to use for the histogram data or overlay data.
        """
        if is_overlay:
            return self._normalization_methods[self._overlay_color_normalization_method]
        else:
            return self._normalization_methods[self._histogram_color_normalization_method]

    def _select_norm_class(self, is_overlay, histogram_data):
        """
        Select the normalization class for the histogram or overlay histogram data.

        Parameters
        ----------
        colormap : BiaColormap
            colormap to use for the image with `categorical` attribute.
        dtype : type
            data type of the histogram data, can be int or float. A categorical colormap expects positive integer color indices.
        histogram_data : np.ndarray
            2D histogram data array to be converted to RGBA image.
        
        Returns
        -------
        norm_class : Normalize
            the normalization class to use for the histogram or overlay histogram data.
        """
        if is_overlay:
            colormap = self.overlay_colormap
            dtype = self._color_indices.dtype
        else:
            colormap = self.histogram_colormap
            dtype = float
        norm_class = self._get_normalization_class(is_overlay)
        if self._is_categorical_colormap(colormap):
            return self._handle_norm_method_for_categorical_colormap(is_overlay, colormap, dtype)
        else:
            return self._handle_norm_method_for_continuous_colormap(is_overlay, norm_class, histogram_data)


    def _histogram2D_array_to_rgba(self, ax, histogram_data, x_edges, y_edges, is_overlay=False):
        """
        Convert a 2D data array to a RGBA image object via pcolormesh using a matplotlib colormap.

        Parameters
        ----------
        ax : plt.Axes
            axes to plot on
        histogram_data : np.ndarray
            2D data array to be converted to RGBA image
        x_edges : np.ndarray
            x bin edges
        y_edges : np.ndarray
            y bin edges
        colormap : BiaColormap
            colormap to use for the image with `categorical` attribute
        dtype : type, optional
            data type of the histogram data, by default float. Can be int or float. It is used to determine the normalization method.
        """
        norm = self._select_norm_class(is_overlay, histogram_data)
        histogram_data = histogram_data.T
        xcenters = (x_edges[:-1] + x_edges[1:]) / 2
        ycenters = (y_edges[:-1] + y_edges[1:]) / 2
        qm = ax.pcolormesh(xcenters, ycenters, histogram_data, shading='nearest',
                           alpha=1, visible=True, norm=norm, cmap=[self.histogram_colormap.cmap, self.overlay_colormap.cmap][is_overlay])
        rgba_array = qm.to_rgba(qm.get_array().reshape(
                histogram_data.shape), norm=True)
        qm.remove()
        # Set NaN values to transparent
        rgba_array[np.isnan(histogram_data)] = [0, 0, 0, 0]
        return rgba_array

    def draw(self):
        """Draws or redraws the 2D histogram."""
        self.ax.figure.canvas.draw_idle()
