from __future__ import annotations

from pathlib import Path
from enum import Enum, auto
from nap_plot_tools import CustomToolbarWidget, QtColorSpinBox, cat10_mod_cmap_first_transparent
from napari.layers import Labels, Points, Tracks
from napari_matplotlib.base import BaseNapariMPLWidget
from napari_matplotlib.util import Interval
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget
from psygnal import Signal
from typing import Union, TYPE_CHECKING, Optional

from biaplotter.artists import Scatter, Histogram2D
from biaplotter.selectors import InteractiveRectangleSelector, InteractiveEllipseSelector, InteractiveLassoSelector

if TYPE_CHECKING:
    import napari

icon_folder_path = (
    Path(__file__).parent / "icons"
)


class ArtistType(Enum):
    HISTOGRAM2D = auto()
    SCATTER = auto()


class SelectorType(Enum):
    LASSO = auto()
    ELLIPSE = auto()
    RECTANGLE = auto()


class CanvasWidget(BaseNapariMPLWidget):
    """A widget that contains a canvas with matplotlib axes and a selection toolbar.

    The widget includes a selection toolbar with buttons to enable/disable selection tools.
    The selection toolbar includes a color class spinbox to select the class to assign to selections.
    The widget includes artists and selectors to plot data and select points.

    Parameters
    ----------
    napari_viewer : napari.viewer.Viewer
        The napari viewer.
    parent : QWidget, optional
        The parent widget, by default None.
    label_text : str, optional
        The text to display next to the class spinbox, by default "Class:".

    Attributes
    ----------
    n_layers_input : Interval
        Amount of available input layers.
    input_layer_types : tuple
        All layers that have a .features attributes.
    selection_tools_layout : QHBoxLayout
        The selection tools layout.
    selection_toolbar : CustomToolbarWidget
        The selection toolbar.
    class_spinbox : QtColorSpinBox
        The color class spinbox.
    colormap : matplotlib.colors.ListedColormap
        The colormap to use for the color class spinbox.
    artists : dict
        Dictionary of artists.
    selectors : dict
        Dictionary of selectors.
    _active_artist : Union[Scatter, Histogram2D]
        Stores the active artist.

    Notes
    -----

    Signals and Slots:

    This class emits the **`artist_changed_signal`** signal when the current artist changes.

    This class automatically connects the **`data_changed_signal`** signal from each artist to the **`update_data`** slot in each selector.
    This allows artists to notify selectors when the data changes. Selectors can then synchronize their data with the artist's data.

    """

    # Amount of available input layers
    n_layers_input = Interval(1, None)
    # All layers that have a .features attributes
    input_layer_types = (Labels, Points, Tracks)
    # # Signal emitted when the current artist changes
    artist_changed_signal = Signal(ArtistType)

    def __init__(self, napari_viewer: "napari.viewer.Viewer", parent: Optional[QWidget] = None, label_text: str = "Class:"):
        super().__init__(napari_viewer, parent=parent)
        self.add_single_axes()
        # Add selection tools layout below canvas
        self.selection_tools_layout = self._build_selection_toolbar_layout(
            label_text=label_text)

        # Add button to selection_toolbar
        self.selection_toolbar.add_custom_button(
            name=SelectorType.LASSO.name,
            tooltip="Click to enable/disable Lasso selection",
            default_icon_path=icon_folder_path / "lasso.png",
            checkable=True,
            checked_icon_path=icon_folder_path / "lasso_checked.png",
            callback=self.on_enable_selector,
        )
        # Add button to selection_toolbar
        self.selection_toolbar.add_custom_button(
            name=SelectorType.ELLIPSE.name,
            tooltip="Click to enable/disable Ellipse selection",
            default_icon_path=icon_folder_path / "ellipse.png",
            checkable=True,
            checked_icon_path=icon_folder_path / "ellipse_checked.png",
            callback=self.on_enable_selector,
        )
        # Add button to selection_toolbar
        self.selection_toolbar.add_custom_button(
            name=SelectorType.RECTANGLE.name,
            tooltip="Click to enable/disable Rectangle selection",
            default_icon_path=icon_folder_path / "rectangle.png",
            checkable=True,
            checked_icon_path=icon_folder_path / "rectangle_checked.png",
            callback=self.on_enable_selector,
        )

        # Set selection class colormap
        self.colormap = cat10_mod_cmap_first_transparent

        # Add selection tools layout to main layout below matplotlib toolbar and above canvas
        self.layout().insertLayout(1, self.selection_tools_layout)

        # Create artists
        self._active_artist = None
        self.artists = {}
        self.add_artist(ArtistType.SCATTER, Scatter(
            ax=self.axes, colormap=self.colormap))
        self.add_artist(ArtistType.HISTOGRAM2D, Histogram2D(ax=self.axes))
        # Set histogram2d as the default artist
        self.active_artist = self.artists[ArtistType.HISTOGRAM2D]

        # Create selectors
        self.selectors = {}
        self.add_selector(SelectorType.LASSO, InteractiveLassoSelector(
            ax=self.axes, canvas_widget=self))
        self.add_selector(SelectorType.ELLIPSE, InteractiveEllipseSelector(
            ax=self.axes, canvas_widget=self))
        self.add_selector(SelectorType.RECTANGLE,
                          InteractiveRectangleSelector(self.axes, self))
        # Connect data_changed signals from each artist to set data in each selector
        for artist in self.artists.values():
            for selector in self.selectors.values():
                artist.data_changed_signal.connect(selector.update_data)

    def _build_selection_toolbar_layout(self, label_text: str = "Class:"):
        """Builds the selection toolbar layout.

        The toolbar starts without any buttons. Add buttons using the add_custom_button method.
        The toolbar includes a color class spinbox to select the class to assign to selections.

        Parameters
        ----------
        label_text : str, optional
            The text to display next to the class spinbox, by default "Class:"

        Returns
        -------
        QHBoxLayout
            The selection toolbar layout.
        """
        # Add selection tools layout below canvas
        selection_tools_layout = QHBoxLayout()
        # Add selection toolbar
        self.selection_toolbar = CustomToolbarWidget(self)
        selection_tools_layout.addWidget(self.selection_toolbar)
        # Add class spinbox
        selection_tools_layout.addWidget(QLabel(label_text))
        self.class_spinbox = QtColorSpinBox(first_color_transparent=False)
        selection_tools_layout.addWidget(self.class_spinbox)
        # Add stretch to the right to push buttons to the left
        selection_tools_layout.addStretch(1)
        return selection_tools_layout

    def on_enable_selector(self, checked: bool):
        """Enables or disables the selected selector.

        Enabling a selector disables all other selectors.

        Parameters
        ----------
        checked : bool
            Whether the button is checked or not.
        """
        sender_name = self.sender().text()
        if checked:
            # If the button is checked, disable all other buttons
            for button_name, button in self.selection_toolbar.buttons.items():
                if button.isChecked() and button_name != sender_name:
                    button.setChecked(False)
            # Remove all selectors
            for selector in self.selectors.values():
                selector.selected_indices = None
                selector.remove()
            # Create the chosen selector
            for selector_type, selector in self.selectors.items():
                if selector_type.name == sender_name:
                    selector.create_selector()
        else:
            # If the button is unchecked, remove the selector
            for selector_type, selector in self.selectors.items():
                if selector_type.name == sender_name:
                    selector.selected_indices = None
                    selector.remove()

    @property
    def active_artist(self):
        """Sets or returns the active artist.
        
        If set, makes the selected artist visible and all other artists invisible.

        Returns
        -------
        Union[Scatter, Histogram2D]
            The active artist.

        Notes
        -----
        artist_changed_signal : Signal
            Signal emitted when the current artist changes.
        """
        return self._active_artist

    @active_artist.setter
    def active_artist(self, value: Union[Scatter, Histogram2D]):
        """Sets the active artist.
        """
        self._active_artist = value
        for artist in self.artists.values():
            if artist == self._active_artist:
                artist.visible = True
            else:
                artist.visible = False
        # Gets artist type
        for artist_type, artist in self.artists.items():
            if artist == value:
                active_artist_type = artist_type
        # Emit signal to notify that the current artist has changed
        self.artist_changed_signal.emit(active_artist_type)

    def add_artist(self, artist_type: ArtistType, artist_instance: Union[Scatter, Histogram2D], visible: bool = False):
        """
        Adds a new artist instance to the artists dictionary.

        Parameters
        ----------
        artist_type : ArtistType
            The type of the artist, defined by the ArtistType enum.
        artist_instance : Union[Scatter, Histogram2D]
            An instance of the artist class.
        """
        if artist_type in self.artists:
            raise ValueError(f"Artist '{artist_type.name}' already exists.")
        self.artists[artist_type] = artist_instance
        artist_instance.visible = visible

    def add_selector(self, selector_type: SelectorType, selector_instance: Union[InteractiveRectangleSelector, InteractiveEllipseSelector, InteractiveLassoSelector]):
        """
        Adds a new selector instance to the selectors dictionary.

        Parameters
        ----------
        selector_type : SelectorType
            The type of the selector, defined by the SelectorType enum.
        selector_instance : Union[InteractiveRectangleSelector, InteractiveEllipseSelector, InteractiveLassoSelector]
            An instance of the selector class.
        """
        if selector_type in self.selectors:
            raise ValueError(
                f"Selector '{selector_type.name}' already exists.")
        self.selectors[selector_type] = selector_instance
