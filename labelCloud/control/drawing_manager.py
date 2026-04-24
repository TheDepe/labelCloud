import logging
from typing import TYPE_CHECKING, List, Union

from ..labeling_strategies import BaseLabelingStrategy
from .bbox_controller import BoundingBoxController
from .pick_point_controller import PickPointController
from .pick_flow_controller import PickFlowController

if TYPE_CHECKING:
    from ..view.gui import GUI


class DrawingManager(object):
    def __init__(self, bbox_controller: BoundingBoxController, pick_point_controller: PickPointController, pick_flow_controller: PickFlowController) -> None:
        self.view: "GUI"
        self.bbox_controller = bbox_controller
        self.drawing_strategy: Union[BaseLabelingStrategy, None] = None
        self.pick_point_controller = pick_point_controller
        self.pick_flow_controller = pick_flow_controller

        # Pick flow queue — classes not yet assigned for the current PCD.
        # Persists across toggle off/on within the same PCD so the flow resumes.
        self.pending_classes: List[str] = []
        self.pick_flow_active: bool = False

    def set_view(self, view: "GUI") -> None:
        self.view = view
        self.view.gl_widget.drawing_mode = self

    def is_active(self) -> bool:
        return self.drawing_strategy is not None and isinstance(
            self.drawing_strategy, BaseLabelingStrategy
        )

    def has_preview(self) -> bool:
        if self.is_active():
            return self.drawing_strategy.__class__.PREVIEW  # type: ignore
        return False

    def set_drawing_strategy(self, strategy: BaseLabelingStrategy) -> None:
        if self.is_active() and self.drawing_strategy == strategy:
            self.reset()
            logging.info("Deactivated drawing!")
        else:
            if self.is_active():
                self.reset()
                logging.info("Resetted previous active drawing mode!")
            self.drawing_strategy = strategy

    def register_point(
        self, x: float, y: float, correction: bool = False, is_temporary: bool = False
    ) -> None:
        assert self.drawing_strategy is not None
        world_point = self.view.gl_widget.get_world_coords(x, y, correction=correction)

        if is_temporary:
            self.drawing_strategy.register_tmp_point(world_point)
        else:
            self.drawing_strategy.register_point(world_point)

            if self.drawing_strategy.__class__.__name__ == "PickingPointStrategy" and self.drawing_strategy.pick_flow:
                point = self.drawing_strategy.get_point()
                # Assign classname from the front of the pending queue BEFORE adding
                if self.pending_classes:
                    point.classname = self.pending_classes[0]
                self.pick_point_controller.add_point(point)
                self.move_to_next_class()

            elif self.drawing_strategy.__class__.__name__ == "PickingPointStrategy":
                self.pick_point_controller.add_point(self.drawing_strategy.get_point())
                self.drawing_strategy.reset()
                self.drawing_strategy = None

            elif self.drawing_strategy.is_bbox_finished():
                self.bbox_controller.add_bbox(self.drawing_strategy.get_bbox())
                self.drawing_strategy.reset()
                self.drawing_strategy = None

    def draw_preview(self) -> None:
        if self.drawing_strategy is not None:
            self.drawing_strategy.draw_preview()

    def reset(self, points_only: bool = False) -> None:
        if self.is_active():
            self.drawing_strategy.reset()  # type: ignore
            if not points_only:
                self.drawing_strategy = None
        self.pick_flow_active = False

    def reset_pick_flow_state(self) -> None:
        """Fully clear pick flow state. Call when loading a new PCD."""
        self.pending_classes = []
        self.pick_flow_active = False

    def activate_pick_flow(self) -> None:
        """Initialise or resume the pending-class queue.

        The dropdown is intentionally NOT managed here — it continues to work
        normally, reflecting whatever point is currently selected.  Only the
        'Next class' status label is owned by the pick flow.
        """
        self.pick_flow_active = True
        if not self.pending_classes:
            # Build the queue: all session classes that have not yet been assigned.
            all_classes = [
                self.view.current_class_dropdown.itemText(i)
                for i in range(self.view.current_class_dropdown.count())
            ]
            assigned = {
                item.get_classname()
                for item in self.view.controller.unified_annotation_controller.items
            }
            self.pending_classes = [c for c in all_classes if c not in assigned]
        self._update_flow_display()

    def _update_flow_display(self) -> None:
        """Update the 'Next class' status label from pending_classes[0]."""
        if self.pending_classes:
            self.view.set_label_flow_status(self.pending_classes[0])
            self.view.gl_widget.set_current_label(self.pending_classes[0])
        else:
            self.view.set_label_flow_status("")
            self.view.gl_widget.set_current_label(None)

    def restore_class_to_front(self, classname: str) -> None:
        """Put a class back at the front of the queue (Ctrl+Z undo)."""
        if classname and classname not in self.pending_classes:
            self.pending_classes.insert(0, classname)
            self._update_flow_display()

    def restore_class_to_back(self, classname: str) -> None:
        """Put a class back at the end of the queue (explicit delete)."""
        if classname and classname not in self.pending_classes:
            self.pending_classes.append(classname)
            self._update_flow_display()

    def move_to_next_class(self, skip: bool = False) -> None:
        """Advance the pick flow. Removes assigned classes; rotates skipped ones to the end."""
        if not self.pending_classes:
            self.reset()
            return

        current_class = self.pending_classes.pop(0)

        if skip:
            # Not assigned yet — move to end so it cycles around
            self.pending_classes.append(current_class)
        # else: assigned — do not re-add

        if self.pending_classes:
            self._update_flow_display()
        else:
            self.view.set_label_flow_status("")
            self.view.gl_widget.set_current_label(None)
            self.reset()
