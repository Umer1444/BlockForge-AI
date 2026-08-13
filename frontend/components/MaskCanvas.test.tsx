import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MaskCanvas from "./MaskCanvas";

describe("MaskCanvas Component", () => {
    const defaultProps = {
        imageUrl: "http://example.com/test.png",
        onSave: vi.fn(),
        width: 800,
        height: 600,
    };

    it("renders toolbar with role='toolbar' and ARIA labels", () => {
        render(<MaskCanvas {...defaultProps} />);

        const toolbar = screen.getByRole("toolbar", { name: "Canvas toolbar" });
        expect(toolbar).toBeInTheDocument();

        const brushBtn = screen.getByRole("button", { name: "Brush tool" });
        const eraserBtn = screen.getByRole("button", { name: "Eraser tool" });
        const undoBtn = screen.getByRole("button", { name: "Undo last stroke" });
        const clearBtn = screen.getByRole("button", { name: "Clear mask" });
        const saveBtn = screen.getByRole("button", { name: "Save mask" });

        expect(brushBtn).toBeInTheDocument();
        expect(brushBtn).toHaveAttribute("aria-pressed", "true");
        expect(eraserBtn).toBeInTheDocument();
        expect(eraserBtn).toHaveAttribute("aria-pressed", "false");
        expect(undoBtn).toBeInTheDocument();
        expect(undoBtn).toBeDisabled();
        expect(clearBtn).toBeInTheDocument();
        expect(saveBtn).toBeInTheDocument();

        const slider = screen.getByRole("slider", { name: "Brush size" });
        expect(slider).toBeInTheDocument();
        expect(slider).toHaveAttribute("aria-valuenow", "30");
        expect(slider).toHaveAttribute("aria-valuemin", "5");
        expect(slider).toHaveAttribute("aria-valuemax", "100");

        const canvas = screen.getByRole("img", { name: "Inpainting mask drawing canvas" });
        expect(canvas).toBeInTheDocument();
    });

    it("displays keyboard shortcut hints subtext under canvas", () => {
        render(<MaskCanvas {...defaultProps} />);

        expect(
            screen.getByText(/Paint over the area to remove, then click Save Mask/i)
        ).toBeInTheDocument();
        expect(screen.getByText(/Shortcuts:/i)).toBeInTheDocument();
        expect(screen.getAllByText(/Brush/i).length).toBeGreaterThanOrEqual(2);
        expect(screen.getAllByText(/Eraser/i).length).toBeGreaterThanOrEqual(2);
    });

    it("switches tools using B and E keys", () => {
        render(<MaskCanvas {...defaultProps} />);

        const brushBtn = screen.getByRole("button", { name: "Brush tool" });
        const eraserBtn = screen.getByRole("button", { name: "Eraser tool" });

        expect(brushBtn).toHaveAttribute("aria-pressed", "true");

        // Press E to switch to eraser
        fireEvent.keyDown(window, { key: "e" });
        expect(eraserBtn).toHaveAttribute("aria-pressed", "true");
        expect(brushBtn).toHaveAttribute("aria-pressed", "false");

        // Press B to switch back to brush
        fireEvent.keyDown(window, { key: "b" });
        expect(brushBtn).toHaveAttribute("aria-pressed", "true");
        expect(eraserBtn).toHaveAttribute("aria-pressed", "false");
    });

    it("adjusts brush size using [ and ] keys within bounds [5, 100]", () => {
        render(<MaskCanvas {...defaultProps} />);

        const slider = screen.getByRole("slider", { name: "Brush size" });
        expect(slider).toHaveAttribute("aria-valuenow", "30");

        // Press ] to increase by 5px
        fireEvent.keyDown(window, { key: "]" });
        expect(slider).toHaveAttribute("aria-valuenow", "35");

        // Press [ twice to decrease by 10px
        fireEvent.keyDown(window, { key: "[" });
        fireEvent.keyDown(window, { key: "[" });
        expect(slider).toHaveAttribute("aria-valuenow", "25");
    });

    it("handles Escape key to clear mask", () => {
        render(<MaskCanvas {...defaultProps} />);

        // Should trigger clearMask without crashing
        fireEvent.keyDown(window, { key: "Escape" });
    });

    it("ignores keybindings when typing inside a text input", () => {
        render(
            <div>
                <input data-testid="text-input" type="text" />
                <MaskCanvas {...defaultProps} />
            </div>
        );

        const textInput = screen.getByTestId("text-input");
        const brushBtn = screen.getByRole("button", { name: "Brush tool" });
        const eraserBtn = screen.getByRole("button", { name: "Eraser tool" });

        textInput.focus();
        fireEvent.keyDown(textInput, { key: "e" });

        // Tool should remain brush because user was typing in text input
        expect(brushBtn).toHaveAttribute("aria-pressed", "true");
        expect(eraserBtn).toHaveAttribute("aria-pressed", "false");
    });

    it("handles touch events (onTouchStart, onTouchMove, onTouchEnd) for touch screens", () => {
        render(<MaskCanvas {...defaultProps} />);
        const canvas = screen.getByRole("img", { name: "Inpainting mask drawing canvas" });

        expect(canvas).toHaveStyle({ touchAction: "none" });

        // Simulate touch start
        fireEvent.touchStart(canvas, {
            touches: [{ clientX: 100, clientY: 100 }],
        });

        // Simulate touch move
        fireEvent.touchMove(canvas, {
            touches: [{ clientX: 120, clientY: 120 }],
        });

        // Simulate touch end
        fireEvent.touchEnd(canvas);
    });

    it("updates maxW dynamically on window resize event", () => {
        render(<MaskCanvas {...defaultProps} />);

        // Dispatch window resize event
        fireEvent(window, new Event("resize"));
    });
});

