import sys
import napari
import numpy as np
from src.grabber import Grabber
import cv2
from magicgui import magicgui
from qtpy.QtWidgets import QDoubleSpinBox


# TODO
#  - roll back path when not found
#  - click addition
#  -

def main(args):

    image = cv2.cvtColor(cv2.imread(args[1]), cv2.COLOR_BGR2RGB)
    mask = cv2.imread(args[2])
    mask = (mask[:, :, 0] > 127).astype(np.uint8)

    default_sigma = 5.0

    with napari.gui_qt():
        viewer = napari.view_image(image)

        grabber = Grabber(image=cv2.cvtColor(image, cv2.COLOR_RGB2LAB),
                          mask=mask, sigma=default_sigma)

        label = viewer.add_labels(grabber.contour,
                                  color={1: 'cyan'},
                                  name='contour', opacity=1.0)

        points = viewer.add_points(np.array([p.coords for p in grabber.paths]),
                                   size=5, face_color='yellow', edge_color='black')
        points.mode = 'select'

        def valid(coords):
            return 0 <= coords[0] < image.shape[0] and 0 <= coords[1] < image.shape[1]

        @points.mouse_drag_callbacks.append
        def mouse_click(layer, event):
            coords = round(layer.position[0]), round(layer.position[1])
            if not valid(coords) or not grabber.contour[coords]:
                print('miss click')
                return

            # mouse press
            if not grabber.select(coords):
                return
            yield

            # mouse move
            while event.type == 'mouse_move':
                coords = round(layer.position[0]), round(layer.position[1])
                grabber.drag(coords)
                label.data = grabber.contour
                yield

            # mouse release
            grabber.confirm()

        # FIXME points.mouse_drag_callbacks.insert(0, mouse_click)

        @magicgui(auto_call=True,
                  sigma={'widget_type': QDoubleSpinBox, 'maximum': 255, 'minimum': 0.01, 'singleStep': 5.0})
        def update_sigma(sigma: float = default_sigma):
            grabber.sigma = sigma

        sigma_box = update_sigma.Gui()
        viewer.window.add_dock_widget(sigma_box, area='left')
        viewer.layers.events.changed.connect(lambda x: sigma_box.refresh_choices())

        @viewer.bind_key('d')
        def remove_points(viewer):
            for i in points.selected_data:
                pt = grabber.paths[i].coords
                grabber.remove(pt)
            label.data = grabber.contour
            points.remove_selected()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("app.py <input image path> <input mask path>")
        sys.exit(-1)
    main(sys.argv)