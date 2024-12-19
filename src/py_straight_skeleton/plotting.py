"""
Utilities and tracers to plot the state of the straight skeleton algorithm to Matplotlib figures.
"""

import logging
import os
from typing import Any, Sequence

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch
from matplotlib.typing import ColorType
from py_straight_skeleton.algorithm import EventInfo, EventQueue, NoopAlgorithmTracer, StraightSkeletonAlgorithm
from py_straight_skeleton.polygon_math import (
    LAV,
    Edge,
    NoopPolygonMathTracer,
    VertexInfo,
    VertexNotComputedError,
    is_point_inside_polygon_edges,
)
from py_straight_skeleton.skeleton import Skeleton

logger = logging.getLogger(__name__)


class Utils:
    """Utilities for plotting elements of the straight skeleton algorithm."""

    @staticmethod
    def plot_vertex_info(
        vi: VertexInfo,
        ax: plt.Axes,
        *,
        bisector_color: ColorType | None = None,
        bisector_length: float = 1,
        arrow_color: ColorType | None = None,
        hide_original_vertex_arrows: bool = True,
    ) -> None:
        """Plot the given vertex information.

        Args:
            vi: Vertex information.
            ax: Matplotlib axes.
            bisector_color: Color of the bisector. Bisector will not be shown if None.
            bisector_length: Length of the bisector.
            arrow_color: Color of the arrows that point towards the vertex's connected edges. Arrows will not be shown
                if None.
            hide_original_vertex_arrows: Whether to hide the arrows that point towards the vertex's connected edges if
                the vertex is defined by both its edges, as is the case of the original vertices.
        """
        # Vertex bisector.
        if bisector_color is not None:
            try:
                bis_direction = vi.bisector_direction
                ax.plot(
                    [vi.position.x, vi.position.x + bis_direction.x * bisector_length],
                    [vi.position.y, vi.position.y + bis_direction.y * bisector_length],
                    color=bisector_color,
                )
            except VertexNotComputedError:
                pass

        # Vertex arrows to its connected edges.
        if arrow_color is not None:
            skip_arrow = (
                hide_original_vertex_arrows
                and vi.prev_orig_edge.has_endpoint(vi)
                and vi.next_orig_edge.has_endpoint(vi)
            )
            if not skip_arrow:
                ax.add_patch(
                    FancyArrowPatch(
                        vi.position.coords,
                        vi.prev_orig_edge.center_p.coords,
                        connectionstyle="arc3,rad=.5",
                        color=arrow_color,
                        arrowstyle="->",
                        mutation_scale=20,
                    )
                )
                ax.add_patch(
                    FancyArrowPatch(
                        vi.position.coords,
                        vi.next_orig_edge.center_p.coords,
                        connectionstyle="arc3,rad=-.5",
                        color=arrow_color,
                        arrowstyle="->",
                        mutation_scale=20,
                    )
                )

    @staticmethod
    def plot_lav(
        lav: LAV, ax: plt.Axes, *, show_bisectors=True, bisector_length: float = 1, show_edge_arrows: bool = True
    ):
        """Plots a LAV.

        Args:
            lav: Lav to plot.
            ax: Matplotlib axes.
            show_bisectors: Whether to show the bisectors of the vertices in the LAV.
            bisector_length: Length of the vertex bisectors. Ignored if `show_bisectors` is False.
            show_edge_arrows: Whether to show the arrows that point towards the vertex's connected edges.
        """
        xs, ys, colors = [], [], []
        for i, vi in enumerate(lav):
            xs.append(vi.position.x)
            ys.append(vi.position.y)
            try:
                colors.append("red" if vi.processed else "magenta" if vi.is_reflex else "goldenrod")
            except VertexNotComputedError:
                colors.append("black")

            if not vi.processed:
                bisector_color = colors[-1] if show_bisectors else None
                arrow_color = (0.8, 0.8, 0.8) if show_edge_arrows else None
                Utils.plot_vertex_info(
                    vi=vi,
                    ax=ax,
                    bisector_color=bisector_color,
                    bisector_length=bisector_length,
                    arrow_color=arrow_color,
                )

        # Plot the vertices.
        ax.scatter(xs, ys, c=colors, s=6)
        # Plot the segments.
        ax.plot(xs + [xs[0]], ys + [ys[0]], color=(0.1, 0.1, 0.1), linestyle="-", lw=1)

        # Annotate the vertices.
        for i, vi in enumerate(lav):
            # Draw odd to the left, even to the right.
            if i % 2 == 0:
                ax.text(vi.position.x, vi.position.y, f"{i}", fontsize=7, ha="left", va="bottom")
            else:
                ax.text(vi.position.x, vi.position.y, f"{i}", fontsize=7, ha="right", va="top")

    @staticmethod
    def plot_edges(edges: list[Edge], ax: plt.Axes, show_edge_ids: bool = False, **kwargs) -> None:
        """Plots the given edges to the given Matplotlib axes, passing through the kwargs."""
        for edge in edges:
            ax.plot([edge.start_p.x, edge.end_p.x], [edge.start_p.y, edge.end_p.y], **kwargs)
            if show_edge_ids:
                ax.text(edge.center_p.x, edge.center_p.y, f"e{edge._auto_id}.", fontsize=7)

    @staticmethod
    def plot_queue(queue: EventQueue, ax: plt.Axes, original_edges: list[Edge] | None):
        """Plots each event in the given queue.

        Args:
            queue: Queue to plot.
            ax: Matplotlib axes.
            original_edges: Original edges of the polygon. If provided, events outside the polygon will not be plotted.
        """
        # Iterate the queue without removing elements
        for idx, (_, event_info) in enumerate(queue):
            cc = event_info.position
            if original_edges and not is_point_inside_polygon_edges(edges=original_edges, point2d=cc):
                logger.debug(f"Not plotting event {idx} @ {cc} as it is outside the polygon.")
                continue
            if idx == 0:
                color = "red"
                marker = "o" if event_info.is_edge_event else "p"
                dests = (
                    [event_info.v_a.position, event_info.v_b.position]
                    if event_info.is_edge_event
                    else [event_info.v.position, event_info.opposite_edge.center_p]
                )
                for dest in dests:
                    debug_arrow = FancyArrowPatch(
                        cc.coords,
                        dest.coords,
                        color=color,
                        arrowstyle="->",
                        mutation_scale=20,
                        connectionstyle="arc3,rad=-.5",
                    )
                    ax.add_patch(debug_arrow)
                s = 64
            elif idx == 1:
                color = "orange"
                marker = "." if event_info.is_edge_event else "*"
                s = 16
            else:
                color = "blue" if event_info.is_edge_event else "magenta"
                marker = "d" if event_info.is_edge_event else "x"
                s = 12
            ax.scatter(cc.x, cc.y, color=color, marker=marker, s=s)

    @staticmethod
    def plot_skeleton(
        skeleton: Skeleton,
        ax: plt.Axes,
        *,
        arc_color: ColorType = "darkgreen",
        circle_color: ColorType | None = None,
        show_vertex_info: bool = False,
        vertex_info_fontsize: int = 6,
        face_colors: Sequence[ColorType] | Sequence[str] | ColorType | None = None,
        **kwargs,
    ):
        """Plots the given skeleton to the given Matplotlib axes

        Args:
            skeleton: Skeleton to plot.
            ax: Matplotlib axes to plot to.
            color: Color of the skeleton arcs.
            circle_color: Color of the circles to render at each vertex. Circles no rendered if set to None.
            show_vertex_info: If set to true, the information (id and time) of each vertex will be displayed.
            vertex_info_fontsize: Font size of the vertex information. Ignored if `show_vertex_info` is False.
            face_colors: Color or colors to render the faces of the skeleton. If a single color is provided, all faces
                will be rendered with that color. If a list of colors is provided, the faces will be rendered with the
                colors in the list, repeating if necessary. If None, faces will not be rendered. Note that this will
                cause face computation if the skeleton does not have faces computed yet.
        """
        # Render the faces first (so that arcs and info overwrite them).
        if face_colors is not None:
            face_color_l = [face_colors] if not hasattr(face_colors, "__getitem__") else face_colors  # type: ignore
            for face_idx, face in enumerate(skeleton.get_faces()):
                face_color = face_color_l[face_idx % len(face_color_l)]
                face_coords = [(skeleton.nodes[v_idx].position.x, skeleton.nodes[v_idx].position.y) for v_idx in face]
                ax.fill(*zip(*face_coords), color=face_color, alpha=0.5)
        # Render the arcs next.
        for skv1, skv2 in skeleton.arc_iterator():
            ax.plot([skv1.position.x, skv2.position.x], [skv1.position.y, skv2.position.y], color=arc_color, **kwargs)
            # Render a circle at p2 with the time as its radius
            if circle_color is not None:
                ax.add_patch(
                    plt.Circle((skv2.position.x, skv2.position.y), radius=skv2.time, color=circle_color, fill=False)
                )
        # Show vertex information at each vertex last (if desired).
        if show_vertex_info:
            for sk_v in skeleton.nodes:
                x, y = sk_v.position.x, sk_v.position.y
                ax.text(x, y, f"{sk_v._skn_id} | t={sk_v.time:.2f}", fontsize=vertex_info_fontsize)


class PlotTracer(NoopAlgorithmTracer, NoopPolygonMathTracer):
    """Tracer that plots the state of the algorithm and other events to Matplotlib figures."""

    def __init__(
        self,
        *,
        fig_cs: float = 5.0,
        step_fig_nrows: int = 3,
        step_fig_ncols: int = 3,
        step_max_figs: int = 3,
        output_dir: str | None = None,
        log_level: int | str = logging.DEBUG,
    ):
        """Initialize the tracer with custom Matplotlib figure settings. The settings for figures are applied to
        step plotting, but some may not affect other plots, such as final plots on algorithm end.

        Args:
            fig_cs: Width=Height of the cells in inches. See figsize in plt.subplots.
            step_fig_nrows: Number of rows per figure before creating another for step plots.
            step_fig_ncols: Number of columns per figure before creating another for step plots.
            step_max_figs: Maximum number of figures to create for step plots. If 0 (or negative), no figures will be
                created.
            output_dir: If set, figures will also be saved to files automatically.
            log_level: Logging level to use for the tracer. It is applied to the module's logger.
        """
        super().__init__()

        # General.
        self.fig_cs = fig_cs

        # Step auto-figures.
        self.step_fig_nrows = step_fig_nrows
        self.step_fig_ncols = step_fig_ncols
        self.step_max_figs = step_max_figs
        self.step_cur_fig: tuple[str, Figure] | None = None
        self.step_next_ax_index = 0
        self.step_cur_flat_axes: Any | None = None

        # Output folder.
        self.output_dir = output_dir
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Logging.
        logger.setLevel(log_level)

    def _create_new_step_figure_lazy(self, fig_name: str) -> bool:
        """Create a new Matplotlib figure if the next axis index is out of bounds, and we have not reached the limit.

        Args:
            fig_name: Name of the figure to create (if one is created), to identify it when we save to disk.

        Returns:
            True if we can use the next axis, False if we have reached the limit of figures and we did not create
            a new one.
        """
        # If our next ax is still within the current figure, we don't need to do anything.
        if self.step_cur_flat_axes is not None and self.step_next_ax_index < len(self.step_cur_flat_axes):
            return True

        # Otherwise, save the current one. It will be closed if it is saved.
        self._save_current_figure_if_needed(close_it=True)

        # If we have reached the limit, we can't create a new one.
        if self.step_max_figs <= 0:
            return False

        # Create a new one.
        fig, axes = plt.subplots(
            ncols=self.step_fig_ncols,
            nrows=self.step_fig_nrows,
            figsize=(self.fig_cs * self.step_fig_ncols, self.fig_cs * self.step_fig_nrows),
        )
        fig.tight_layout()

        # Configure it.
        self.step_cur_fig = (fig_name, fig)
        self.step_next_ax_index = 0
        self.step_cur_flat_axes = axes.flatten() if self.step_fig_nrows > 1 else [axes]
        for ax in self.step_cur_flat_axes:
            ax.set_aspect("equal")

        # And discount from figures left.
        self.step_max_figs -= 1
        return True

    def _get_next_ax(self, fig_name: str) -> plt.Axes | None:
        """Return a new axis to use, increasing the index for the next one and creating a new figure if necessary.

        Args:
            fig_name: Name of the created figure (if one is created), to identify it when we save to disk.

        Returns:
            The axis to plot to, or None if we have reached the maximum number of figures allowed.
        """
        can_draw = self._create_new_step_figure_lazy(fig_name=fig_name)
        if not can_draw:
            return None

        assert self.step_cur_flat_axes is not None  # for mypy
        ax = self.step_cur_flat_axes[self.step_next_ax_index]
        self.step_next_ax_index += 1
        return ax

    def _save_current_figure_if_needed(self, *, close_it: bool) -> None:
        """Save to disk the current figure if we have a folder set up, and a figure to save.

        Args:
            close_it: Whether to close the figure after saving it. In general this should be True, but sometimes
                we may want to save a figure due to a debug event, while keeping it open for more plots.
        """
        if self.step_cur_fig is not None and self.output_dir is not None:
            fig_name, fig = self.step_cur_fig
            target_dir = os.path.join(self.output_dir, f"skel_plot_{fig_name}.png")
            fig.savefig(target_dir)
            if close_it:
                plt.close(fig)
            logger.debug(f"Saved plot to {target_dir}")

        # Regardless of whether we saved the image, remove the pointers as if we had closed it. We do not close it
        # so that it stays open for interactive notebooks, but we pretend we did so that we create new ones later on.
        if close_it:
            self.step_cur_fig = None
            self.step_cur_flat_axes = None
            self.step_next_ax_index = 0

    def _plot_common_to_ax(
        self,
        ax: plt.Axes,
        algorithm: StraightSkeletonAlgorithm,
        *,
        bisector_length: float | None = None,
        show_edge_ids: bool = False,
    ) -> None:
        """Plot most common elements of the algorithm to the given axis.

        Args:
            ax: Axis to plot to.
            algorithm: Instance with the current state of the algorithm.
            bisector_length: Length of the vertex bisectors. If None, a default length is computed, based on a factor
                with respect to the axis size.
            show_edge_ids: Whether to show the edge ids.
        """

        def compute_bisector_length(bisector_factor: float = 0.5) -> float:
            """Helper to compute bisector length as a factor of the axis size."""
            x_range = ax.get_xlim()
            y_range = ax.get_ylim()
            x_width = abs(x_range[1] - x_range[0])
            y_height = abs(y_range[1] - y_range[0])
            return min(x_width, y_height) * bisector_factor

        bisector_length = compute_bisector_length() if bisector_length is None else bisector_length

        # Original edges
        Utils.plot_edges(
            edges=algorithm.original_edges, ax=ax, color="gray", linestyle="--", show_edge_ids=show_edge_ids
        )
        # LAVs.
        for lav in algorithm.slav:
            Utils.plot_lav(lav=lav, ax=ax, bisector_length=bisector_length, show_edge_arrows=False)
        # Skeleton
        Utils.plot_skeleton(skeleton=algorithm.skeleton, ax=ax, arc_color="lightsteelblue", circle_color=None)
        # Queue
        Utils.plot_queue(queue=algorithm.queue, ax=ax, original_edges=algorithm.original_edges)

    def on_step_begin(self, step: int, time: float, algorithm: StraightSkeletonAlgorithm) -> None:
        """Logs the current queue and plots the state of the algorithm if we have axes/plots left to plot to."""

        # Log current queue.
        logger.debug("= " * 80)
        logger.debug("Queue:")
        for idx, (priority, event_info) in enumerate(algorithm.queue):
            logger.debug(f"{idx} ({event_info._auto_id}): {priority} {event_info.event_type:15s} {event_info.position}")
        logger.debug("= " * 80)

        # Grab the next axis to plot to.
        fig_name = f"step_{step}"
        cur_step_ax = self._get_next_ax(fig_name=fig_name)
        if cur_step_ax is None:
            return

        # Set ax's title.
        queue_count = len(algorithm.queue)
        lav_count = len(algorithm.slav)
        cur_step_ax.set_title(f"Step={step}, t={time:.6f}, {queue_count} events, {lav_count} LAVs", fontsize=8)

        # Plot everything.
        self._plot_common_to_ax(ax=cur_step_ax, algorithm=algorithm, show_edge_ids=step == 1)

    def on_event_popped(
        self, step: int, time: float, event_info: EventInfo, algorithm: StraightSkeletonAlgorithm
    ) -> None:
        """Logs the event information."""

        # Print event information.
        logger.debug(
            f"s={step}, t={time: .6f}. Processing event at {event_info.position} (type: {event_info.event_type})"
        )

    def on_algorithm_end(self, algorithm: StraightSkeletonAlgorithm) -> None:
        """Closes the current figure, and plots the final result of the algorithm, polygonizing the skeleton."""

        # Add to the limit of figs, since we will need at least two more axes.
        self.step_max_figs += 2

        # Skeleton
        final_ax_skel = self._get_next_ax(fig_name="end_skeleton")
        assert final_ax_skel is not None  # for mypy
        final_ax_skel.set_aspect("equal")
        final_ax_skel.set_title("Final Skeleton", fontsize=8)
        Utils.plot_edges(edges=algorithm.original_edges, ax=final_ax_skel, color="gray", linestyle="--")
        Utils.plot_skeleton(skeleton=algorithm.skeleton, ax=final_ax_skel, circle_color="whitesmoke")

        # Polygonized skeleton.
        final_ax_faces = self._get_next_ax(fig_name="end_faces")
        assert final_ax_faces is not None  # for mypy
        final_ax_faces.set_aspect("equal")
        final_ax_faces.set_title("Final Faces", fontsize=8)

        # Plot end result.
        Utils.plot_edges(edges=algorithm.original_edges, ax=final_ax_faces, color="gray", linestyle="--")
        face_colors = ["red", "green", "blue", "yellow", "purple", "orange", "cyan", "magenta"]
        try:
            # Polygonization can be tricky, log any issuies, but do not crash while plotting.
            Utils.plot_skeleton(
                skeleton=algorithm.skeleton, ax=final_ax_faces, arc_color="black", face_colors=face_colors, lw=0.5
            )
        except Exception as e:
            logger.error(f"Failed to plot skeleton faces: {e}")

        # Immediately save/close the figure if needed.
        self._save_current_figure_if_needed(close_it=True)

    def on_lav_infinite_loop_detected(self, lav: LAV) -> None:
        """Save the last plot we were able to get, since we are crashing."""

        logger.error("Infinite loop detected in LAV computation.")

        # Save the last image since we are crashing.
        self._save_current_figure_if_needed(close_it=True)

    def on_debug_hit(self, algorithm: StraightSkeletonAlgorithm) -> None:
        """General function to plot the current state of the algorithm when a debug hit is triggered."""

        # Create a debug figure and plot all to it.
        debug_fig, debug_ax = plt.subplots(figsize=(10, 10))
        debug_ax.set_title("Debug hit")
        debug_ax.set_aspect("equal")

        # Plot common state of the algorithm.
        self._plot_common_to_ax(ax=debug_ax, algorithm=algorithm)

        # - PLACEHOLDER BEGIN
        # Here we can add custom information during debugging.
        # - PLACEHOLDER END

        # Save it to the output folder.
        if self.output_dir:
            target_dir = os.path.join(self.output_dir, "on_debug_hit.png")
            debug_fig.savefig(target_dir)
            plt.close(debug_fig)
            logger.info(f"Saved debug hit plot to {target_dir}")

        # Save the current figure if needed, but do not close it, in case the algorithm continues.
        self._save_current_figure_if_needed(close_it=False)

    def on_algorith_raised_exception(self, algorithm: StraightSkeletonAlgorithm, exception: Exception) -> None:
        """Save the last plot we were able to get, since we are crashing."""

        # Save the last image since we are crashing.
        self._save_current_figure_if_needed(close_it=True)

        # Also attempt to draw a last image.
        self.on_debug_hit(algorithm=algorithm)
